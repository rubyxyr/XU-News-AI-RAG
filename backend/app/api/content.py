"""
Content management API endpoints for document CRUD operations.
"""
from flask import Blueprint, request, jsonify, current_app, Response, stream_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.utils import secure_filename
import os
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app import db
from app.models import Document, Tag
from sqlalchemy import func
from app.utils.decorators import validate_json, validate_pagination, require_user_ownership
from app.utils.validators import validate_file_upload, sanitize_html_content, validate_tag_name

logging.basicConfig(level=logging.INFO)
bp = Blueprint('content', __name__)

# Global thread pool executor for background tasks
_background_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='vector-cleanup')


def cleanup_background_executor():
    """
    Cleanup function to properly shutdown the background executor.
    Should be called when the application shuts down.
    """
    try:
        logging.info("Shutting down background vector cleanup executor...")
        _background_executor.shutdown(wait=True)
        logging.info("Background vector cleanup executor shutdown completed")
    except Exception as e:
        logging.error(f"Error shutting down background executor: {e}")


# Register cleanup function to be called on application shutdown
import atexit
atexit.register(cleanup_background_executor)


def _extract_csv_content(file_path: str) -> tuple[str, str]:
    """
    Extract content from CSV file - returns overview for main document.
    Individual rows will be processed separately.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple of (overview_content, summary)
    """
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Generate overview content (not the actual data)
        content_parts = []
        
        # Add file overview
        content_parts.append(f"CSV File Overview:")
        content_parts.append(f"- Total records: {len(df)}")
        content_parts.append(f"- Total columns: {len(df.columns)}")
        content_parts.append(f"- Columns: {', '.join(df.columns.tolist())}")
        content_parts.append("")
        
        # Add column information
        content_parts.append("Column Information:")
        for col in df.columns:
            col_type = str(df[col].dtype)
            non_null_count = df[col].count()
            content_parts.append(f"- {col}: {col_type} ({non_null_count} non-null values)")
        content_parts.append("")
        
        # Add data preview (first 5 rows for overview only)
        content_parts.append("Data Preview (First 5 rows):")
        sample_data = df.head(5).to_string(index=False)
        content_parts.append(sample_data)
        content_parts.append("")
        
        # Add note about individual records
        content_parts.append("Note: Each row in this CSV has been imported as a separate document.")
        content_parts.append(f"Total {len(df)} individual documents created from this file.")
        
        content = "\n".join(content_parts)
        
        # Generate summary
        summary = f"CSV file imported with {len(df)} individual records. "
        summary += f"Columns: {', '.join(df.columns.tolist()[:5])}"
        if len(df.columns) > 5:
            summary += f" and {len(df.columns) - 5} more"
        
        return content, summary
        
    except Exception as e:
        error_content = f"Error extracting CSV content: {str(e)}\n\nFile appears to be a CSV but could not be processed."
        return error_content, "CSV file processing error"


def _process_csv_rows_as_documents_streaming(file_path: str, user_id: int, file_tags: list = None, source_name: str = None, progress_callback=None):
    """
    Process each row in CSV file as individual documents with streaming progress updates.
    
    Args:
        file_path: Path to the CSV file
        user_id: User ID for document ownership
        file_tags: Tags to apply to all documents
        source_name: Name of the source file
        progress_callback: Callback function that formats progress data into messages
        
    Yields:
        Progress messages formatted for streaming
    """
    try:
        import pandas as pd
        from app.models import Document
        
        # Read CSV file
        df = pd.read_csv(file_path)
        created_docs = []
        total_rows = len(df)
        
        logging.info(f"Processing {total_rows} rows from CSV as individual documents (streaming)")
        
        # Initial progress
        initial_msg = progress_callback({
            'type': 'progress',
            'message': f'Starting to process {total_rows} CSV rows',
            'current': 0,
            'total': total_rows,
            'percentage': 0
        })
        if initial_msg:
            yield initial_msg
        
        # Column identification (same as original function)
        title_cols = [col for col in df.columns if any(keyword in col.lower() 
                     for keyword in ['title', 'headline', 'subject', 'name'])]
        content_cols = [col for col in df.columns if any(keyword in col.lower() 
                       for keyword in ['content', 'text', 'body', 'description', 'summary', 'article'])]
        author_cols = [col for col in df.columns if any(keyword in col.lower() 
                      for keyword in ['author', 'writer', 'reporter', 'by'])]
        date_cols = [col for col in df.columns if any(keyword in col.lower() 
                    for keyword in ['date', 'time', 'published', 'created'])]
        url_cols = [col for col in df.columns if any(keyword in col.lower() 
                   for keyword in ['url', 'link', 'source', 'href'])]
        tag_cols = [col for col in df.columns if any(keyword in col.lower() 
                   for keyword in ['tags', 'tag', 'categories', 'labels', 'keywords'])]
        
        for index, row in df.iterrows():
            try:
                # Extract data (same logic as original function)
                title = None
                if title_cols:
                    title = str(row[title_cols[0]]) if pd.notna(row[title_cols[0]]) else None
                
                if not title:
                    for col in df.columns:
                        if pd.notna(row[col]) and isinstance(row[col], (str, int, float)):
                            title = str(row[col])[:100]
                            break
                
                if not title:
                    title = f"Record {index + 1} from {source_name or 'CSV file'}"
                
                content = None
                if content_cols:
                    content = str(row[content_cols[0]]) if pd.notna(row[content_cols[0]]) else None
                
                if not content:
                    content_parts = []
                    for col in df.columns:
                        if pd.notna(row[col]):
                            content_parts.append(f"{col}: {row[col]}")
                    content = "\n".join(content_parts)
                
                author = None
                if author_cols:
                    author = str(row[author_cols[0]]) if pd.notna(row[author_cols[0]]) else None
                
                published_date = None
                if date_cols:
                    try:
                        date_val = row[date_cols[0]]
                        if pd.notna(date_val):
                            from dateutil import parser
                            published_date = parser.parse(str(date_val))
                    except Exception:
                        pass
                
                source_url = None
                if url_cols:
                    source_url = str(row[url_cols[0]]) if pd.notna(row[url_cols[0]]) else None
                
                summary = content[:200] + "..." if len(content) > 200 else content
                
                # Extract and combine tags
                tags = list(file_tags) if file_tags else []
                
                if tag_cols:
                    csv_tags_str = str(row[tag_cols[0]]) if pd.notna(row[tag_cols[0]]) else ""
                    if csv_tags_str:
                        csv_tags = [tag.strip().lower() for tag in csv_tags_str.replace(';', ',').replace('|', ',').split(',')]
                        csv_tags = [tag for tag in csv_tags if tag and len(tag) > 0]
                        tags.extend(csv_tags)
                
                tags.extend(['csv-import'])
                
                # Create document
                document = Document.create_document(
                    user_id=user_id,
                    title=title,
                    content=content,
                    summary=summary,
                    source_url=source_url,
                    source_type='csv',
                    source_name=source_name or f"CSV Import (Row {index + 1})",
                    author=author,
                    published_date=published_date,
                    tags=tags,
                    vector_id=f"csv_row_{user_id}_{index}_{hash(file_path)}"
                )
                
                # Process through AI pipeline
                _process_document_through_ai_pipeline(document)
                
                created_docs.append(document.id)
                
                # Yield progress update immediately after each document
                progress_msg = progress_callback({
                    'type': 'progress',
                    'message': f'Created document for row {index + 1}: "{title[:50]}{"..." if len(title) > 50 else ""}"',
                    'current': index + 1,
                    'total': total_rows,
                    'percentage': int((index + 1) / total_rows * 100),
                    'created_count': len(created_docs)
                })
                if progress_msg:
                    yield progress_msg
                
            except Exception as row_error:
                logging.error(f"Error processing CSV row {index}: {row_error}")
                error_msg = progress_callback({
                    'type': 'error',
                    'message': f'Error processing row {index + 1}: {str(row_error)}',
                    'current': index + 1,
                    'total': total_rows
                })
                if error_msg:
                    yield error_msg
                continue
        
        # Final success message
        final_msg = progress_callback({
            'type': 'success',
            'message': f'Successfully created {len(created_docs)} documents from CSV',
            'current': total_rows,
            'total': total_rows,
            'percentage': 100,
            'created_count': len(created_docs)
        })
        if final_msg:
            yield final_msg
        
        logging.info(f"Successfully created {len(created_docs)} documents from CSV (streaming)")
        
    except Exception as e:
        logging.error(f"Error processing CSV rows (streaming): {e}")
        error_msg = progress_callback({
            'type': 'error',
            'message': f'Error processing CSV: {str(e)}',
            'fatal': True
        })
        if error_msg:
            yield error_msg


def _process_csv_rows_as_documents(file_path: str, user_id: int, file_tags: list = None, source_name: str = None, progress_callback=None):
    """
    Process each row in CSV file as individual documents.
    
    Args:
        file_path: Path to the CSV file
        user_id: User ID for document ownership
        file_tags: Tags to apply to all documents
        source_name: Name of the source file
        progress_callback: Optional callback function for progress updates
        
    Returns:
        List of created document IDs
    """
    try:
        import pandas as pd
        from app.models import Document
        
        # Read CSV file
        df = pd.read_csv(file_path)
        created_docs = []
        total_rows = len(df)
        
        logging.info(f"Processing {total_rows} rows from CSV as individual documents")
        
        if progress_callback:
            progress_callback({
                'type': 'progress',
                'message': f'Starting to process {total_rows} CSV rows',
                'current': 0,
                'total': total_rows,
                'percentage': 0
            })
        
        # Try to identify common column patterns for news/content
        title_cols = [col for col in df.columns if any(keyword in col.lower() 
                     for keyword in ['title', 'headline', 'subject', 'name'])]
        content_cols = [col for col in df.columns if any(keyword in col.lower() 
                       for keyword in ['content', 'text', 'body', 'description', 'summary', 'article'])]
        author_cols = [col for col in df.columns if any(keyword in col.lower() 
                      for keyword in ['author', 'writer', 'reporter', 'by'])]
        date_cols = [col for col in df.columns if any(keyword in col.lower() 
                    for keyword in ['date', 'time', 'published', 'created'])]
        url_cols = [col for col in df.columns if any(keyword in col.lower() 
                   for keyword in ['url', 'link', 'source', 'href'])]
        tag_cols = [col for col in df.columns if any(keyword in col.lower() 
                   for keyword in ['tags', 'tag', 'categories', 'labels', 'keywords'])]
        
        for index, row in df.iterrows():
            try:
                # Update progress every 10 rows or for small files every row
                if progress_callback and (index % max(1, total_rows // 100) == 0 or total_rows < 100):
                    progress_callback({
                        'type': 'progress',
                        'message': f'Processing row {index + 1} of {total_rows}',
                        'current': index + 1,
                        'total': total_rows,
                        'percentage': int((index + 1) / total_rows * 100)
                    })
                
                # Extract title (prefer title columns, fallback to first non-null string column)
                title = None
                if title_cols:
                    title = str(row[title_cols[0]]) if pd.notna(row[title_cols[0]]) else None
                
                if not title:
                    # Fallback: use first non-null string column
                    for col in df.columns:
                        if pd.notna(row[col]) and isinstance(row[col], (str, int, float)):
                            title = str(row[col])[:100]  # Limit title length
                            break
                
                if not title:
                    title = f"Record {index + 1} from {source_name or 'CSV file'}"
                
                # Extract content (prefer content columns, fallback to all row data)
                content = None
                if content_cols:
                    content = str(row[content_cols[0]]) if pd.notna(row[content_cols[0]]) else None
                
                if not content:
                    # Fallback: create structured content from all columns
                    content_parts = []
                    for col in df.columns:
                        if pd.notna(row[col]):
                            content_parts.append(f"{col}: {row[col]}")
                    content = "\n".join(content_parts)
                
                # Extract author
                author = None
                if author_cols:
                    author = str(row[author_cols[0]]) if pd.notna(row[author_cols[0]]) else None
                
                # Extract date
                published_date = None
                if date_cols:
                    try:
                        date_val = row[date_cols[0]]
                        if pd.notna(date_val):
                            from dateutil import parser
                            published_date = parser.parse(str(date_val))
                    except Exception as date_error:
                        logging.debug(f"Could not parse date {date_val}: {date_error}")
                
                # Extract source URL
                source_url = None
                if url_cols:
                    source_url = str(row[url_cols[0]]) if pd.notna(row[url_cols[0]]) else None
                
                # Generate summary (first 200 chars of content)
                summary = content[:200] + "..." if len(content) > 200 else content
                
                # Extract tags from CSV data and combine with file tags
                tags = list(file_tags) if file_tags else []
                
                # Extract tags from CSV columns if available
                if tag_cols:
                    csv_tags_str = str(row[tag_cols[0]]) if pd.notna(row[tag_cols[0]]) else ""
                    if csv_tags_str:
                        # Split by common separators (comma, semicolon, pipe)
                        csv_tags = [tag.strip().lower() for tag in csv_tags_str.replace(';', ',').replace('|', ',').split(',')]
                        csv_tags = [tag for tag in csv_tags if tag and len(tag) > 0]  # Filter empty tags
                        tags.extend(csv_tags)
                
                # Add auto-detected tags
                tags.extend(['csv-import'])
                
                # Create document
                document = Document.create_document(
                    user_id=user_id,
                    title=title,
                    content=content,
                    summary=summary,
                    source_url=source_url,
                    source_type='csv',
                    source_name=source_name or f"CSV Import (Row {index + 1})",
                    author=author,
                    published_date=published_date,
                    tags=tags,
                    vector_id=f"csv_row_{user_id}_{index}_{hash(file_path)}"
                )
                
                # Process through AI pipeline
                _process_document_through_ai_pipeline(document)
                
                created_docs.append(document.id)
                
                # Yield progress update after successfully creating each document
                if progress_callback:
                    progress_callback({
                        'type': 'progress',
                        'message': f'Created document for row {index + 1}: "{title[:50]}{"..." if len(title) > 50 else ""}"',
                        'current': index + 1,
                        'total': total_rows,
                        'percentage': int((index + 1) / total_rows * 100),
                        'created_count': len(created_docs)
                    })
                
            except Exception as row_error:
                logging.error(f"Error processing CSV row {index}: {row_error}")
                if progress_callback:
                    progress_callback({
                        'type': 'error',
                        'message': f'Error processing row {index + 1}: {str(row_error)}',
                        'current': index + 1,
                        'total': total_rows
                    })
                continue
        
        if progress_callback:
            progress_callback({
                'type': 'success',
                'message': f'Successfully created {len(created_docs)} documents from CSV',
                'current': total_rows,
                'total': total_rows,
                'percentage': 100,
                'created_count': len(created_docs)
            })
        
        logging.info(f"Successfully created {len(created_docs)} documents from CSV")
        return created_docs
        
    except Exception as e:
        logging.error(f"Error processing CSV rows: {e}")
        if progress_callback:
            progress_callback({
                'type': 'error',
                'message': f'Error processing CSV: {str(e)}',
                'fatal': True
            })
        return []


def _extract_xlsx_content(file_path: str) -> tuple[str, str]:
    """
    Extract overview content from XLSX file.
    Individual rows will be processed separately.
    
    Args:
        file_path: Path to the XLSX file
        
    Returns:
        Tuple of (overview_content, summary)
    """
    try:
        import pandas as pd
        
        # Read Excel file and get all sheet names
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        content_parts = []
        
        # Add file overview
        content_parts.append(f"Excel File Overview:")
        content_parts.append(f"- Total sheets: {len(sheet_names)}")
        content_parts.append(f"- Sheet names: {', '.join(sheet_names)}")
        content_parts.append("")
        
        total_rows = 0
        
        # Process each sheet
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                total_rows += len(df)
                
                content_parts.append(f"Sheet: {sheet_name}")
                content_parts.append(f"- Rows: {len(df)}")
                content_parts.append(f"- Columns: {len(df.columns)}")
                content_parts.append(f"- Column names: {', '.join(df.columns.tolist())}")
                content_parts.append("")
                
                # Add data preview (first 3 rows per sheet for overview)
                if not df.empty:
                    content_parts.append(f"Data Preview for '{sheet_name}' (First 3 rows):")
                    sample_data = df.head(3).to_string(index=False)
                    content_parts.append(sample_data)
                    content_parts.append("")
                
            except Exception as sheet_error:
                content_parts.append(f"Error processing sheet '{sheet_name}': {str(sheet_error)}")
                content_parts.append("")
        
        # Add note about individual records
        content_parts.append("Note: Each row from all sheets has been imported as a separate document.")
        content_parts.append(f"Total {total_rows} individual documents created from this Excel file.")
        
        content = "\n".join(content_parts)
        
        # Generate summary
        summary = f"Excel file imported with {total_rows} individual records across {len(sheet_names)} sheets. "
        summary += f"Sheets: {', '.join(sheet_names[:3])}"
        if len(sheet_names) > 3:
            summary += f" and {len(sheet_names) - 3} more"
        
        return content, summary
        
    except Exception as e:
        error_content = f"Error extracting Excel content: {str(e)}\n\nFile appears to be an Excel file but could not be processed."
        return error_content, "Excel file processing error"


def _process_xlsx_rows_as_documents_streaming(file_path: str, user_id: int, file_tags: list = None, source_name: str = None, progress_callback=None):
    """
    Process each row in XLSX file (all sheets) as individual documents with streaming progress updates.
    
    Args:
        file_path: Path to the XLSX file
        user_id: User ID for document ownership
        file_tags: Tags to apply to all documents
        source_name: Name of the source file
        progress_callback: Callback function that formats progress data into messages
        
    Yields:
        Progress messages formatted for streaming
    """
    try:
        import pandas as pd
        from app.models import Document
        
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        created_docs = []
        
        # Calculate total rows across all sheets for progress tracking
        total_rows = 0
        sheet_row_counts = {}
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_row_counts[sheet_name] = len(df)
                total_rows += len(df)
            except Exception:
                sheet_row_counts[sheet_name] = 0
        
        logging.info(f"Processing XLSX with {len(sheet_names)} sheets and {total_rows} total rows as individual documents (streaming)")
        
        # Initial progress
        initial_msg = progress_callback({
            'type': 'progress',
            'message': f'Starting to process {total_rows} Excel rows across {len(sheet_names)} sheets',
            'current': 0,
            'total': total_rows,
            'percentage': 0
        })
        if initial_msg:
            yield initial_msg
        
        processed_rows = 0
        
        # Process each sheet
        for sheet_idx, sheet_name in enumerate(sheet_names):
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                if df.empty:
                    logging.info(f"Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                logging.info(f"Processing {len(df)} rows from sheet '{sheet_name}' (streaming)")
                
                # Column identification
                title_cols = [col for col in df.columns if any(keyword in col.lower() 
                             for keyword in ['title', 'headline', 'subject', 'name'])]
                content_cols = [col for col in df.columns if any(keyword in col.lower() 
                               for keyword in ['content', 'text', 'body', 'description', 'summary', 'article'])]
                author_cols = [col for col in df.columns if any(keyword in col.lower() 
                              for keyword in ['author', 'writer', 'reporter', 'by'])]
                date_cols = [col for col in df.columns if any(keyword in col.lower() 
                            for keyword in ['date', 'time', 'published', 'created'])]
                url_cols = [col for col in df.columns if any(keyword in col.lower() 
                           for keyword in ['url', 'link', 'source', 'href'])]
                tag_cols = [col for col in df.columns if any(keyword in col.lower() 
                           for keyword in ['tags', 'tag', 'categories', 'labels', 'keywords'])]
                
                for index, row in df.iterrows():
                    try:
                        processed_rows += 1
                        
                        # Extract data (same logic as original function)
                        title = None
                        if title_cols:
                            title = str(row[title_cols[0]]) if pd.notna(row[title_cols[0]]) else None
                        
                        if not title:
                            for col in df.columns:
                                if pd.notna(row[col]) and isinstance(row[col], (str, int, float)):
                                    title = str(row[col])[:100]
                                    break
                        
                        if not title:
                            title = f"Record {index + 1} from {sheet_name} ({source_name or 'Excel file'})"
                        
                        content = None
                        if content_cols:
                            content = str(row[content_cols[0]]) if pd.notna(row[content_cols[0]]) else None
                        
                        if not content:
                            content_parts = []
                            content_parts.append(f"Sheet: {sheet_name}")
                            content_parts.append("")
                            for col in df.columns:
                                if pd.notna(row[col]):
                                    content_parts.append(f"{col}: {row[col]}")
                            content = "\n".join(content_parts)
                        
                        author = None
                        if author_cols:
                            author = str(row[author_cols[0]]) if pd.notna(row[author_cols[0]]) else None
                        
                        published_date = None
                        if date_cols:
                            try:
                                date_val = row[date_cols[0]]
                                if pd.notna(date_val):
                                    from dateutil import parser
                                    published_date = parser.parse(str(date_val))
                            except Exception:
                                pass
                        
                        source_url = None
                        if url_cols:
                            source_url = str(row[url_cols[0]]) if pd.notna(row[url_cols[0]]) else None
                        
                        summary = content[:200] + "..." if len(content) > 200 else content
                        
                        # Extract and combine tags
                        tags = list(file_tags) if file_tags else []
                        
                        if tag_cols:
                            xlsx_tags_str = str(row[tag_cols[0]]) if pd.notna(row[tag_cols[0]]) else ""
                            if xlsx_tags_str:
                                xlsx_tags = [tag.strip().lower() for tag in xlsx_tags_str.replace(';', ',').replace('|', ',').split(',')]
                                xlsx_tags = [tag for tag in xlsx_tags if tag and len(tag) > 0]
                                tags.extend(xlsx_tags)
                        
                        tags.extend(['xlsx-import'])
                        
                        # Create document
                        document = Document.create_document(
                            user_id=user_id,
                            title=title,
                            content=content,
                            summary=summary,
                            source_url=source_url,
                            source_type='xlsx',
                            source_name=source_name or f"Excel Import - {sheet_name} (Row {index + 1})",
                            author=author,
                            published_date=published_date,
                            tags=tags,
                            vector_id=f"xlsx_row_{user_id}_{sheet_name}_{index}_{hash(file_path)}"
                        )
                        
                        # Process through AI pipeline
                        _process_document_through_ai_pipeline(document)
                        
                        created_docs.append(document.id)
                        
                        # Yield progress update immediately after each document
                        progress_msg = progress_callback({
                            'type': 'progress',
                            'message': f'Created document for {sheet_name} row {index + 1}: "{title[:50]}{"..." if len(title) > 50 else ""}"',
                            'current': processed_rows,
                            'total': total_rows,
                            'percentage': int(processed_rows / total_rows * 100),
                            'created_count': len(created_docs),
                            'sheet_name': sheet_name
                        })
                        if progress_msg:
                            yield progress_msg
                        
                    except Exception as row_error:
                        logging.error(f"Error processing row {index} in sheet '{sheet_name}': {row_error}")
                        error_msg = progress_callback({
                            'type': 'error',
                            'message': f'Error processing row {index + 1} in sheet "{sheet_name}": {str(row_error)}',
                            'current': processed_rows,
                            'total': total_rows,
                            'sheet_name': sheet_name
                        })
                        if error_msg:
                            yield error_msg
                        continue
                
            except Exception as sheet_error:
                logging.error(f"Error processing sheet '{sheet_name}': {sheet_error}")
                error_msg = progress_callback({
                    'type': 'error',
                    'message': f'Error processing sheet "{sheet_name}": {str(sheet_error)}',
                    'current': processed_rows,
                    'total': total_rows,
                    'sheet_name': sheet_name
                })
                if error_msg:
                    yield error_msg
                continue
        
        # Final success message
        final_msg = progress_callback({
            'type': 'success',
            'message': f'Successfully created {len(created_docs)} documents from Excel file',
            'current': total_rows,
            'total': total_rows,
            'percentage': 100,
            'created_count': len(created_docs)
        })
        if final_msg:
            yield final_msg
        
        logging.info(f"Successfully created {len(created_docs)} documents from XLSX (streaming)")
        
    except Exception as e:
        logging.error(f"Error processing XLSX rows (streaming): {e}")
        error_msg = progress_callback({
            'type': 'error',
            'message': f'Error processing Excel file: {str(e)}',
            'fatal': True
        })
        if error_msg:
            yield error_msg


def _process_xlsx_rows_as_documents(file_path: str, user_id: int, file_tags: list = None, source_name: str = None, progress_callback=None):
    """
    Process each row in XLSX file (all sheets) as individual documents.
    
    Args:
        file_path: Path to the XLSX file
        user_id: User ID for document ownership
        file_tags: Tags to apply to all documents
        source_name: Name of the source file
        progress_callback: Optional callback function for progress updates
        
    Returns:
        List of created document IDs
    """
    try:
        import pandas as pd
        from app.models import Document
        
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        created_docs = []
        
        # Calculate total rows across all sheets for progress tracking
        total_rows = 0
        sheet_row_counts = {}
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_row_counts[sheet_name] = len(df)
                total_rows += len(df)
            except Exception:
                sheet_row_counts[sheet_name] = 0
        
        logging.info(f"Processing XLSX with {len(sheet_names)} sheets and {total_rows} total rows as individual documents")
        
        if progress_callback:
            progress_callback({
                'type': 'progress',
                'message': f'Starting to process {total_rows} Excel rows across {len(sheet_names)} sheets',
                'current': 0,
                'total': total_rows,
                'percentage': 0
            })
        
        processed_rows = 0
        
        # Process each sheet
        for sheet_idx, sheet_name in enumerate(sheet_names):
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                if df.empty:
                    logging.info(f"Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                logging.info(f"Processing {len(df)} rows from sheet '{sheet_name}'")
                
                # Try to identify common column patterns for news/content
                title_cols = [col for col in df.columns if any(keyword in col.lower() 
                             for keyword in ['title', 'headline', 'subject', 'name'])]
                content_cols = [col for col in df.columns if any(keyword in col.lower() 
                               for keyword in ['content', 'text', 'body', 'description', 'summary', 'article'])]
                author_cols = [col for col in df.columns if any(keyword in col.lower() 
                              for keyword in ['author', 'writer', 'reporter', 'by'])]
                date_cols = [col for col in df.columns if any(keyword in col.lower() 
                            for keyword in ['date', 'time', 'published', 'created'])]
                url_cols = [col for col in df.columns if any(keyword in col.lower() 
                           for keyword in ['url', 'link', 'source', 'href'])]
                tag_cols = [col for col in df.columns if any(keyword in col.lower() 
                           for keyword in ['tags', 'tag', 'categories', 'labels', 'keywords'])]
                
                for index, row in df.iterrows():
                    try:
                        processed_rows += 1
                        
                        # Update progress every few rows or for small files every row
                        if progress_callback and (processed_rows % max(1, total_rows // 100) == 0 or total_rows < 100):
                            progress_callback({
                                'type': 'progress',
                                'message': f'Processing sheet "{sheet_name}" - row {index + 1} of {len(df)} (overall: {processed_rows}/{total_rows})',
                                'current': processed_rows,
                                'total': total_rows,
                                'percentage': int(processed_rows / total_rows * 100)
                            })
                        # Extract title (prefer title columns, fallback to first non-null string column)
                        title = None
                        if title_cols:
                            title = str(row[title_cols[0]]) if pd.notna(row[title_cols[0]]) else None
                        
                        if not title:
                            # Fallback: use first non-null string column
                            for col in df.columns:
                                if pd.notna(row[col]) and isinstance(row[col], (str, int, float)):
                                    title = str(row[col])[:100]  # Limit title length
                                    break
                        
                        if not title:
                            title = f"Record {index + 1} from {sheet_name} ({source_name or 'Excel file'})"
                        
                        # Extract content (prefer content columns, fallback to all row data)
                        content = None
                        if content_cols:
                            content = str(row[content_cols[0]]) if pd.notna(row[content_cols[0]]) else None
                        
                        if not content:
                            # Fallback: create structured content from all columns
                            content_parts = []
                            content_parts.append(f"Sheet: {sheet_name}")
                            content_parts.append("")
                            for col in df.columns:
                                if pd.notna(row[col]):
                                    content_parts.append(f"{col}: {row[col]}")
                            content = "\n".join(content_parts)
                        
                        # Extract author
                        author = None
                        if author_cols:
                            author = str(row[author_cols[0]]) if pd.notna(row[author_cols[0]]) else None
                        
                        # Extract date
                        published_date = None
                        if date_cols:
                            try:
                                date_val = row[date_cols[0]]
                                if pd.notna(date_val):
                                    from dateutil import parser
                                    published_date = parser.parse(str(date_val))
                            except Exception as date_error:
                                logging.debug(f"Could not parse date {date_val}: {date_error}")
                        
                        # Extract source URL
                        source_url = None
                        if url_cols:
                            source_url = str(row[url_cols[0]]) if pd.notna(row[url_cols[0]]) else None
                        
                        # Generate summary (first 200 chars of content)
                        summary = content[:200] + "..." if len(content) > 200 else content
                        
                        # Extract tags from XLSX data and combine with file tags
                        tags = list(file_tags) if file_tags else []
                        
                        # Extract tags from XLSX columns if available
                        if tag_cols:
                            xlsx_tags_str = str(row[tag_cols[0]]) if pd.notna(row[tag_cols[0]]) else ""
                            if xlsx_tags_str:
                                # Split by common separators (comma, semicolon, pipe)
                                xlsx_tags = [tag.strip().lower() for tag in xlsx_tags_str.replace(';', ',').replace('|', ',').split(',')]
                                xlsx_tags = [tag for tag in xlsx_tags if tag and len(tag) > 0]  # Filter empty tags
                                tags.extend(xlsx_tags)
                        
                        # Add auto-detected tags
                        tags.extend(['xlsx-import',])
                        
                        # Create document
                        document = Document.create_document(
                            user_id=user_id,
                            title=title,
                            content=content,
                            summary=summary,
                            source_url=source_url,
                            source_type='xlsx',
                            source_name=source_name or f"Excel Import - {sheet_name} (Row {index + 1})",
                            author=author,
                            published_date=published_date,
                            tags=tags,
                            vector_id=f"xlsx_row_{user_id}_{sheet_name}_{index}_{hash(file_path)}"
                        )
                        
                        # Process through AI pipeline
                        _process_document_through_ai_pipeline(document)
                        
                        created_docs.append(document.id)
                        
                        # Yield progress update after successfully creating each document
                        if progress_callback:
                            progress_callback({
                                'type': 'progress',
                                'message': f'Created document for {sheet_name} row {index + 1}: "{title[:50]}{"..." if len(title) > 50 else ""}"',
                                'current': processed_rows,
                                'total': total_rows,
                                'percentage': int(processed_rows / total_rows * 100),
                                'created_count': len(created_docs),
                                'sheet_name': sheet_name
                            })
                        
                    except Exception as row_error:
                        logging.error(f"Error processing row {index} in sheet '{sheet_name}': {row_error}")
                        if progress_callback:
                            progress_callback({
                                'type': 'error',
                                'message': f'Error processing row {index + 1} in sheet "{sheet_name}": {str(row_error)}',
                                'current': processed_rows,
                                'total': total_rows
                            })
                        continue
                
            except Exception as sheet_error:
                logging.error(f"Error processing sheet '{sheet_name}': {sheet_error}")
                if progress_callback:
                    progress_callback({
                        'type': 'error',
                        'message': f'Error processing sheet "{sheet_name}": {str(sheet_error)}',
                        'current': processed_rows,
                        'total': total_rows
                    })
                continue
        
        if progress_callback:
            progress_callback({
                'type': 'success',
                'message': f'Successfully created {len(created_docs)} documents from Excel file',
                'current': total_rows,
                'total': total_rows,
                'percentage': 100,
                'created_count': len(created_docs)
            })
        
        logging.info(f"Successfully created {len(created_docs)} documents from XLSX")
        return created_docs
        
    except Exception as e:
        logging.error(f"Error processing XLSX rows: {e}")
        if progress_callback:
            progress_callback({
                'type': 'error',
                'message': f'Error processing Excel file: {str(e)}',
                'fatal': True
            })
        return []


def _process_document_through_ai_pipeline(document, config=None):
    """
    Process document through AI pipeline for semantic search.
    Similar to RSS crawler implementation.
    
    Args:
        document: Document instance to process
        config: Optional configuration dictionary
    """
    try:
        from app.ai.langchain_service import LangChainService
        
        # Use provided config or default values
        ai_config = config or {
            'EMBEDDINGS_MODEL': current_app.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            'VECTOR_STORE_PATH': current_app.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
            'LLM_MODEL': current_app.config.get('LLM_MODEL', 'qwen3:4b'),
            'OLLAMA_BASE_URL': current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'RERANKER_MODEL': current_app.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        }
        
        ai_pipeline = LangChainService(config=ai_config)
        success = ai_pipeline.process_document(document)
        
        if success:
            logging.info(f"Document {document.id} processed through AI pipeline successfully")
        else:
            logging.warning(f"Failed to process document {document.id} through AI pipeline")
        
        return success
        
    except Exception as e:
        logging.error(f"Error processing document {document.id} through AI pipeline: {e}")
        # Don't fail the entire upload process if AI processing fails
        return False


def _remove_document_from_ai_pipeline_sync(document_data, app_config, flask_app):
    """
    Synchronous function to remove document from AI pipeline vector store.
    This function runs in a background thread with proper Flask application context.
    
    Args:
        document_data: Dict containing document information (id, user_id, etc.)
        app_config: Application configuration dictionary
        flask_app: Flask application instance for context
    """
    try:
        # Create Flask application context for background thread
        with flask_app.app_context():
            from app.ai.langchain_service import LangChainService
            
            # Create a simple document-like object for the AI pipeline
            class DocumentInfo:
                def __init__(self, doc_data):
                    self.id = doc_data['id']
                    self.user_id = doc_data['user_id']
                    self.title = doc_data.get('title', '')
            
            document = DocumentInfo(document_data)
            
            ai_pipeline = LangChainService(config=app_config)
            success = ai_pipeline.remove_document(document)
            
            if success:
                logging.info(f"[BACKGROUND] Document {document.id} removed from AI pipeline successfully")
            else:
                logging.warning(f"[BACKGROUND] Failed to remove document {document.id} from AI pipeline")
            
            return success
        
    except Exception as e:
        logging.error(f"[BACKGROUND] Error removing document {document_data.get('id', 'unknown')} from AI pipeline: {e}")
        return False


def _remove_document_from_ai_pipeline_background(document):
    """
    Remove document from AI pipeline vector store as a background task.
    Returns immediately while cleanup happens in the background.
    
    Args:
        document: Document instance to remove
    """
    try:
        # Extract necessary data from document before background task
        document_data = {
            'id': document.id,
            'user_id': document.user_id,
            'title': getattr(document, 'title', '')
        }
        
        # Get current app config and app instance (outside of background thread)
        app_config = {
            'EMBEDDINGS_MODEL': current_app.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            'VECTOR_STORE_PATH': current_app.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
            'LLM_MODEL': current_app.config.get('LLM_MODEL', 'qwen3:4b'),
            'OLLAMA_BASE_URL': current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'RERANKER_MODEL': current_app.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        }
        
        # Get Flask app instance for background context
        flask_app = current_app._get_current_object()
        
        # Submit background task with Flask app context
        future = _background_executor.submit(
            _remove_document_from_ai_pipeline_sync, 
            document_data, 
            app_config,
            flask_app
        )
        
        logging.info(f"Document {document.id} vector cleanup scheduled as background task")
        
        # Add callback for completion logging (optional)
        def log_completion(future):
            try:
                success = future.result()
                if success:
                    logging.info(f"[BACKGROUND] Vector cleanup completed for document {document_data['id']}")
                else:
                    logging.warning(f"[BACKGROUND] Vector cleanup failed for document {document_data['id']}")
            except Exception as e:
                logging.error(f"[BACKGROUND] Vector cleanup task error for document {document_data['id']}: {e}")
        
        future.add_done_callback(log_completion)
        
    except Exception as e:
        logging.error(f"Error scheduling background vector cleanup for document {document.id}: {e}")


def _remove_documents_from_ai_pipeline_background(documents):
    """
    Remove multiple documents from AI pipeline vector store as a background task.
    Returns immediately while cleanup happens in the background.
    
    Args:
        documents: List of Document instances to remove
    """
    try:
        logging.info(f"[VECTOR_CLEANUP] Starting background vector cleanup for {len(documents)} documents")
        
        # Extract necessary data from documents before background task
        documents_data = []
        for doc in documents:
            doc_data = {
                'id': doc.id,
                'user_id': doc.user_id,
                'title': getattr(doc, 'title', '')
            }
            documents_data.append(doc_data)
            logging.debug(f"[VECTOR_CLEANUP] Extracted data for document {doc.id}: user_id={doc.user_id}")
        
        logging.info(f"[VECTOR_CLEANUP] Extracted data for {len(documents_data)} documents")
        
        # Get current app config and app instance (outside of background thread)
        app_config = {
            'EMBEDDINGS_MODEL': current_app.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            'VECTOR_STORE_PATH': current_app.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
            'LLM_MODEL': current_app.config.get('LLM_MODEL', 'qwen3:4b'),
            'OLLAMA_BASE_URL': current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'RERANKER_MODEL': current_app.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        }
        
        logging.debug(f"[VECTOR_CLEANUP] App config prepared: {list(app_config.keys())}")
        
        # Get Flask app instance for background context
        flask_app = current_app._get_current_object()
        logging.debug(f"[VECTOR_CLEANUP] Flask app instance obtained: {flask_app}")
        
        # Submit background task for batch processing
        def batch_remove_task():
            logging.info(f"[BACKGROUND] Starting batch vector cleanup task for {len(documents_data)} documents")
            success_count = 0
            for doc_data in documents_data:
                try:
                    logging.debug(f"[BACKGROUND] Processing document {doc_data['id']}")
                    success = _remove_document_from_ai_pipeline_sync(doc_data, app_config, flask_app)
                    if success:
                        success_count += 1
                        logging.info(f"[BACKGROUND] Successfully removed document {doc_data['id']} from vector store")
                    else:
                        logging.warning(f"[BACKGROUND] Failed to remove document {doc_data['id']} from vector store")
                except Exception as e:
                    logging.error(f"[BACKGROUND] Error removing document {doc_data['id']} from vector store: {e}")
            
            logging.info(f"[BACKGROUND] Batch vector cleanup completed: {success_count}/{len(documents_data)} documents processed")
            return success_count
        
        # Test if background executor is working
        def test_executor():
            logging.info(f"[BACKGROUND_TEST] Background executor is working!")
            return "test_success"
        
        logging.info(f"[VECTOR_CLEANUP] Testing background executor first")
        test_future = _background_executor.submit(test_executor)
        try:
            test_result = test_future.result(timeout=5)  # Wait max 5 seconds for test
            logging.info(f"[VECTOR_CLEANUP] Background executor test result: {test_result}")
        except Exception as test_error:
            logging.error(f"[VECTOR_CLEANUP] Background executor test failed: {test_error}")
        
        logging.info(f"[VECTOR_CLEANUP] Submitting background task to executor")
        future = _background_executor.submit(batch_remove_task)
        logging.info(f"[VECTOR_CLEANUP] Background task submitted successfully")
        
        doc_ids = [str(doc.id) for doc in documents]
        logging.info(f"Batch vector cleanup scheduled as background task for documents: {', '.join(doc_ids)}")
        
        # Add completion callback for debugging
        def log_task_completion(fut):
            try:
                result = fut.result()
                logging.info(f"[VECTOR_CLEANUP] Background task completed with result: {result}")
            except Exception as e:
                logging.error(f"[VECTOR_CLEANUP] Background task failed with error: {e}")
        
        future.add_done_callback(log_task_completion)
        
    except Exception as e:
        logging.error(f"Error scheduling background batch vector cleanup: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")

# Validation Schemas
class DocumentCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    summary = fields.Str(validate=validate.Length(max=1000))
    source_url = fields.Url(allow_none=True)
    source_name = fields.Str(validate=validate.Length(max=200))
    author = fields.Str(validate=validate.Length(max=200))
    published_date = fields.DateTime(allow_none=True)
    tags = fields.List(fields.Str(validate=validate.Length(max=50)), missing=[])
    language = fields.Str(validate=validate.Length(max=10), missing='en')


class DocumentUpdateSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=500))
    content = fields.Str(validate=validate.Length(min=1))
    summary = fields.Str(validate=validate.Length(max=1000))
    source_url = fields.Url(allow_none=True)
    source_name = fields.Str(validate=validate.Length(max=200))
    author = fields.Str(validate=validate.Length(max=200))
    published_date = fields.DateTime(allow_none=True)
    tags = fields.List(fields.Str(validate=validate.Length(max=50)))
    language = fields.Str(validate=validate.Length(max=10))


class BatchOperationSchema(Schema):
    document_ids = fields.List(fields.Int(), required=True, validate=validate.Length(min=1))
    operation = fields.Str(required=True, validate=validate.OneOf(['delete', 'tag', 'untag']))
    tags = fields.List(fields.Str(validate=validate.Length(max=50)), missing=[])


@bp.route('/documents', methods=['GET'])
@jwt_required()
@validate_pagination()
def get_documents(page, per_page):
    """Get paginated list of user's documents with filtering."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get filter parameters
        filters = {}
        
        if request.args.get('source_type'):
            filters['source_type'] = request.args.get('source_type')
        
        if request.args.get('date_from'):
            try:
                filters['date_from'] = datetime.fromisoformat(request.args.get('date_from'))
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use ISO format.'}), 400
        
        if request.args.get('date_to'):
            try:
                filters['date_to'] = datetime.fromisoformat(request.args.get('date_to'))
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use ISO format.'}), 400
        
        if request.args.get('tags'):
            filters['tags'] = request.args.get('tags').split(',')
        
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        
        if request.args.get('processing_status'):
            filters['processing_status'] = request.args.get('processing_status')
        
        # Get documents
        pagination = Document.get_user_documents(current_user_id, page, per_page, filters)
        
        return jsonify({
            'documents': [doc.to_dict(include_content=False) for doc in pagination.items],
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Get documents error: {e}")
        return jsonify({'error': 'Failed to retrieve documents'}), 500


@bp.route('/documents', methods=['POST'])
@jwt_required()
@validate_json(DocumentCreateSchema)
def create_document(validated_data):
    """Create a new document."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Sanitize content
        validated_data['content'] = sanitize_html_content(validated_data['content'])
        if validated_data.get('summary'):
            validated_data['summary'] = sanitize_html_content(validated_data['summary'])
        
        # Validate tags
        if validated_data.get('tags'):
            valid_tags = []
            for tag in validated_data['tags']:
                is_valid, message = validate_tag_name(tag)
                if is_valid:
                    valid_tags.append(tag.lower().strip())
                else:
                    return jsonify({'error': f'Invalid tag "{tag}": {message}'}), 400
            validated_data['tags'] = valid_tags
        
        # Create document
        document = Document.create_document(
            user_id=current_user_id,
            source_type='manual',
            **validated_data
        )
        
        # Process document through AI pipeline for semantic search
        _process_document_through_ai_pipeline(document)
        
        return jsonify({
            'message': 'Document created successfully',
            'document': document.to_dict()
        }), 201
        
    except Exception as e:
        logging.error(f"Create document error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create document'}), 500


@bp.route('/documents/<int:document_id>', methods=['GET'])
@jwt_required()
@require_user_ownership(Document, 'document_id')
def get_document(document_id, resource):
    """Get a specific document by ID."""
    try:
        document = resource  # From decorator
        
        # Increment view count
        document.increment_view_count()
        
        return jsonify({
            'document': document.to_dict(include_content=True)
        }), 200
        
    except Exception as e:
        logging.error(f"Get document error: {e}")
        return jsonify({'error': 'Failed to retrieve document'}), 500


@bp.route('/documents/<int:document_id>', methods=['PUT'])
@jwt_required()
@require_user_ownership(Document, 'document_id')
@validate_json(DocumentUpdateSchema)
def update_document(validated_data, document_id, resource):
    """Update a document."""
    try:
        document = resource  # From decorator
        
        # Sanitize content if provided
        if 'content' in validated_data:
            validated_data['content'] = sanitize_html_content(validated_data['content'])
        
        if 'summary' in validated_data:
            validated_data['summary'] = sanitize_html_content(validated_data['summary'])
        
        # Validate tags if provided
        if 'tags' in validated_data:
            valid_tags = []
            for tag in validated_data['tags']:
                is_valid, message = validate_tag_name(tag)
                if is_valid:
                    valid_tags.append(tag.lower().strip())
                else:
                    return jsonify({'error': f'Invalid tag "{tag}": {message}'}), 400
            validated_data['tags'] = valid_tags
        
        # Update document
        content_changed = 'content' in validated_data
        document.update_content(**validated_data)
        
        # If content changed, reprocess through AI pipeline
        if content_changed:
            _process_document_through_ai_pipeline(document)
        
        return jsonify({
            'message': 'Document updated successfully',
            'document': document.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Update document error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update document'}), 500


@bp.route('/documents/<int:document_id>', methods=['DELETE'])
@jwt_required()
@require_user_ownership(Document, 'document_id')
def delete_document(document_id, resource):
    """Delete a document."""
    try:
        document = resource  # From decorator
        
        # Delete from database first
        db.session.delete(document)
        db.session.commit()
        
        # Schedule vector database cleanup as background task
        # This happens after database deletion to ensure immediate frontend response
        _remove_document_from_ai_pipeline_background(document)
        
        return jsonify({'message': 'Document deleted successfully'}), 200
        
    except Exception as e:
        logging.error(f"Delete document error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete document'}), 500


@bp.route('/documents/batch', methods=['POST'])
@jwt_required()
@validate_json(BatchOperationSchema)
def batch_operation(validated_data):
    """Perform batch operations on multiple documents."""
    try:
        current_user_id = int(get_jwt_identity())
        document_ids = validated_data['document_ids']
        operation = validated_data['operation']
        
        # Verify all documents belong to current user
        documents = Document.query.filter(
            Document.id.in_(document_ids),
            Document.user_id == current_user_id
        ).all()
        
        if len(documents) != len(document_ids):
            return jsonify({'error': 'Some documents not found or not accessible'}), 404
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        if operation == 'delete':
            # Store documents for background vector cleanup before deletion
            docs_for_vector_cleanup = list(documents)  # Create a copy
            logging.info(f"Batch delete: Starting deletion of {len(documents)} documents: {[doc.id for doc in documents]}")
            
            for doc in documents:
                try:
                    # Delete from main database
                    db.session.delete(doc)
                    results['success'] += 1
                    logging.info(f"Batch delete: Successfully deleted document {doc.id} from database")
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Document {doc.id}: {str(e)}")
                    logging.error(f"Batch delete: Failed to delete document {doc.id}: {e}")
            
            logging.info(f"Batch delete: Database deletion completed. Success: {results['success']}, Failed: {results['failed']}")
            
            # Commit database changes before scheduling background tasks
            try:
                db.session.commit()
                logging.info(f"Batch delete: Database changes committed successfully")
            except Exception as commit_error:
                logging.error(f"Batch delete: Database commit failed: {commit_error}")
                db.session.rollback()
                return jsonify({'error': 'Failed to commit database changes'}), 500
            
            # Schedule vector database cleanup as background task for all successfully deleted documents
            # This happens after database deletion to ensure immediate frontend response
            if results['success'] > 0:
                logging.info(f"Batch delete: Scheduling vector cleanup for {len(docs_for_vector_cleanup)} documents")
                try:
                    _remove_documents_from_ai_pipeline_background(docs_for_vector_cleanup)
                    logging.info(f"Batch delete: Vector cleanup scheduling completed")
                except Exception as vector_error:
                    logging.error(f"Batch delete: Vector cleanup scheduling failed: {vector_error}")
                    # Don't fail the entire operation if vector cleanup fails
            else:
                logging.warning(f"Batch delete: No successful deletions, skipping vector cleanup")
            
        elif operation == 'tag':
            if not validated_data.get('tags'):
                return jsonify({'error': 'Tags required for tag operation'}), 400
            
            # Validate tags
            valid_tags = []
            for tag in validated_data['tags']:
                is_valid, message = validate_tag_name(tag)
                if is_valid:
                    valid_tags.append(tag.lower().strip())
                else:
                    return jsonify({'error': f'Invalid tag "{tag}": {message}'}), 400
            
            for doc in documents:
                try:
                    for tag_name in valid_tags:
                        doc.add_tag(tag_name)
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Document {doc.id}: {str(e)}")
        
        elif operation == 'untag':
            if not validated_data.get('tags'):
                return jsonify({'error': 'Tags required for untag operation'}), 400
            
            for doc in documents:
                try:
                    for tag_name in validated_data['tags']:
                        doc.remove_tag(tag_name.lower().strip())
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Document {doc.id}: {str(e)}")
        
        # Only commit if not already committed (for non-delete operations)
        if operation != 'delete':
            db.session.commit()
        
        return jsonify({
            'message': f'Batch {operation} operation completed',
            'results': results
        }), 200
        
    except Exception as e:
        logging.error(f"Batch operation error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Batch operation failed'}), 500


@bp.route('/documents/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload a document file."""
    try:
        current_user_id = int(get_jwt_identity())
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'csv', 'xlsx'})
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        
        is_valid, message = validate_file_upload(file, allowed_extensions, max_size)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{current_user_id}_{timestamp}_{filename}"
        
        upload_path = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        
        file.save(file_path)
        
        # Get metadata from form FIRST
        title = request.form.get('title', file.filename)
        form_summary = request.form.get('summary', '').strip()
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        
        # Validate and clean tags
        valid_tags = []
        for tag in tags:
            tag = tag.strip()
            if tag:
                is_valid, _ = validate_tag_name(tag)
                if is_valid:
                    valid_tags.append(tag.lower())
        
        # Extract content based on file type
        content = ""
        summary = ""
        file_ext = filename.rsplit('.', 1)[-1].lower()
        
        try:
            if file_ext in ['txt', 'md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_ext == 'html':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = sanitize_html_content(f.read())
            elif file_ext == 'csv':
                content, auto_summary = _extract_csv_content(file_path)
                if not form_summary:  # Use auto-generated summary if none provided
                    summary = auto_summary
                else:
                    summary = form_summary
                # Process CSV rows as individual documents
                _process_csv_rows_as_documents(
                    file_path=file_path,
                    user_id=current_user_id,
                    file_tags=valid_tags,
                    source_name=title
                )
            elif file_ext == 'xlsx':
                content, auto_summary = _extract_xlsx_content(file_path)
                if not form_summary:  # Use auto-generated summary if none provided
                    summary = auto_summary
                else:
                    summary = form_summary
                # Process XLSX rows as individual documents
                _process_xlsx_rows_as_documents(
                    file_path=file_path,
                    user_id=current_user_id,
                    file_tags=valid_tags,
                    source_name=title
                )
            # TODO: Add support for PDF, DOC, DOCX extraction
            else:
                content = f"[File uploaded: {file.filename}]\nContent extraction for {file_ext} files not yet implemented."
        
        except Exception as e:
            logging.error(f"Content extraction error: {e}")
            content = f"[File uploaded: {file.filename}]\nError extracting content: {str(e)}"
        
        # Use form summary if provided and not already set
        if form_summary and not summary:
            summary = form_summary
        
        # Create main document (overview for CSV/XLSX, full content for others)
        document = Document.create_document(
            user_id=current_user_id,
            title=title,
            content=content,
            summary=summary,
            source_type='upload',
            source_url=f"file://{filename}",
            tags=valid_tags
        )
        
        # Process document through AI pipeline for semantic search
        _process_document_through_ai_pipeline(document)
        
        # Prepare response message based on file type
        if file_ext in ['csv', 'xlsx']:
            # For CSV/XLSX, the individual records were already processed above
            # Count total documents created for this file
            try:
                import pandas as pd
                if file_ext == 'csv':
                    df = pd.read_csv(file_path)
                    total_records = len(df)
                    message = f'CSV file uploaded successfully. Created {total_records + 1} documents: 1 overview + {total_records} individual records.'
                else:  # xlsx
                    excel_file = pd.ExcelFile(file_path)
                    total_records = 0
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(file_path, sheet_name=sheet_name)
                        total_records += len(df)
                    message = f'Excel file uploaded successfully. Created {total_records + 1} documents: 1 overview + {total_records} individual records from {len(excel_file.sheet_names)} sheets.'
            except Exception as count_error:
                logging.error(f"Error counting records: {count_error}")
                message = f'{file_ext.upper()} file uploaded successfully. Individual records processed as separate documents.'
        else:
            message = 'File uploaded successfully'
        
        return jsonify({
            'message': message,
            'document': document.to_dict(),
            'filename': filename
        }), 201
        
    except Exception as e:
        logging.error(f"File upload error: {e}")
        return jsonify({'error': 'File upload failed'}), 500


@bp.route('/documents/upload/stream', methods=['POST'])
@jwt_required()
def upload_document_stream():
    """Upload a document file with streaming progress updates."""
    
    # Extract all request-specific data outside the generator
    try:
        current_user_id = int(get_jwt_identity())
        
        # Initial validation
        if 'file' not in request.files:
            return Response(
                f"data: {json.dumps({'type': 'error', 'message': 'No file provided'})}\n\n",
                mimetype='text/event-stream'
            )
        
        file = request.files['file']
        if file.filename == '':
            return Response(
                f"data: {json.dumps({'type': 'error', 'message': 'No file selected'})}\n\n",
                mimetype='text/event-stream'
            )
        
        # Get metadata from form
        title = request.form.get('title', file.filename)
        form_summary = request.form.get('summary', '').strip()
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        
        # Get configuration
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'csv', 'xlsx'})
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        upload_path = current_app.config['UPLOAD_FOLDER']
        
        # Validate and save file immediately (before generator starts)
        is_valid, validation_message = validate_file_upload(file, allowed_extensions, max_size)
        if not is_valid:
            return Response(
                f"data: {json.dumps({'type': 'error', 'message': validation_message})}\n\n",
                mimetype='text/event-stream'
            )
        
        # Save file immediately to avoid "closed file" errors
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{current_user_id}_{timestamp}_{filename}"
        
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
    except Exception as e:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': f'Request validation failed: {str(e)}'})}\n\n",
            mimetype='text/event-stream'
        )
    
    # Get the current Flask app instance to use in the generator
    app = current_app._get_current_object()
    
    def generate_upload_progress():
        """Generator function that yields progress updates during file processing."""
        try:
            # File validation and saving already done outside generator
            yield f"data: {json.dumps({'type': 'progress', 'message': 'File validated and saved successfully', 'percentage': 20})}\n\n"
            
            # Validate and clean tags
            valid_tags = []
            for tag in tags:
                tag = tag.strip()
                if tag:
                    is_valid, _ = validate_tag_name(tag)
                    if is_valid:
                        valid_tags.append(tag.lower())
            
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing metadata', 'percentage': 30})}\n\n"
            
            # Extract content based on file type
            content = ""
            summary = ""
            file_ext = filename.rsplit('.', 1)[-1].lower()
            
            try:
                if file_ext in ['txt', 'md']:
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Reading text file', 'percentage': 40})}\n\n"
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                elif file_ext == 'html':
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing HTML file', 'percentage': 40})}\n\n"
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = sanitize_html_content(f.read())
                elif file_ext == 'csv':
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing CSV file', 'percentage': 40})}\n\n"
                    content, auto_summary = _extract_csv_content(file_path)
                    if not form_summary:
                        summary = auto_summary
                    else:
                        summary = form_summary
                    
                    # Process CSV rows with real-time progress updates
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Creating documents from CSV rows', 'percentage': 60})}\n\n"
                    
                    # Create a generator-based CSV processor that yields progress in real-time
                    def process_csv_with_progress():
                        with app.app_context():
                            # Create a simple callback that yields immediately
                            def progress_callback(progress_data):
                                if progress_data.get('type') == 'progress':
                                    # Adjust percentage to be between 60-80% for CSV processing phase
                                    row_progress = progress_data.get('percentage', 0)
                                    overall_percentage = 60 + (row_progress * 0.2)  # 60% + (progress * 20%)
                                    
                                    return f"data: {json.dumps({'type': 'progress', 'message': progress_data.get('message', 'Processing CSV row'), 'percentage': int(overall_percentage), 'current': progress_data.get('current'), 'total': progress_data.get('total'), 'created_count': progress_data.get('created_count', 0)})}\n\n"
                                elif progress_data.get('type') == 'error':
                                    return f"data: {json.dumps({'type': 'warning', 'message': progress_data.get('message', 'Row processing error')})}\n\n"
                                elif progress_data.get('type') == 'success':
                                    return f"data: {json.dumps({'type': 'progress', 'message': progress_data.get('message', 'CSV processing completed'), 'percentage': 80})}\n\n"
                                return None
                            
                            # Use the existing CSV processing function with a yielding callback
                            for progress_message in _process_csv_rows_as_documents_streaming(
                                file_path=file_path,
                                user_id=current_user_id,
                                file_tags=valid_tags,
                                source_name=title,
                                progress_callback=progress_callback
                            ):
                                yield progress_message
                    
                    # Process CSV and yield progress updates in real-time
                    for progress_message in process_csv_with_progress():
                        yield progress_message
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'CSV processing completed', 'percentage': 80})}\n\n"
                        
                elif file_ext == 'xlsx':
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing Excel file', 'percentage': 40})}\n\n"
                    content, auto_summary = _extract_xlsx_content(file_path)
                    if not form_summary:
                        summary = auto_summary
                    else:
                        summary = form_summary
                    
                    # Process XLSX rows with real-time progress updates
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Creating documents from Excel rows', 'percentage': 60})}\n\n"
                    
                    # Create a generator-based XLSX processor that yields progress in real-time
                    def process_xlsx_with_progress():
                        with app.app_context():
                            # Create a simple callback that yields immediately
                            def progress_callback(progress_data):
                                if progress_data.get('type') == 'progress':
                                    # Adjust percentage to be between 60-80% for XLSX processing phase
                                    row_progress = progress_data.get('percentage', 0)
                                    overall_percentage = 60 + (row_progress * 0.2)  # 60% + (progress * 20%)
                                    
                                    message = progress_data.get('message', 'Processing Excel row')
                                    # Include sheet name if available
                                    if progress_data.get('sheet_name'):
                                        message = f"Sheet '{progress_data['sheet_name']}': {message}"
                                    
                                    return f"data: {json.dumps({'type': 'progress', 'message': message, 'percentage': int(overall_percentage), 'current': progress_data.get('current'), 'total': progress_data.get('total'), 'created_count': progress_data.get('created_count', 0)})}\n\n"
                                elif progress_data.get('type') == 'error':
                                    return f"data: {json.dumps({'type': 'warning', 'message': progress_data.get('message', 'Row processing error')})}\n\n"
                                elif progress_data.get('type') == 'success':
                                    return f"data: {json.dumps({'type': 'progress', 'message': progress_data.get('message', 'Excel processing completed'), 'percentage': 80})}\n\n"
                                return None
                            
                            # Use the existing XLSX processing function with a yielding callback
                            for progress_message in _process_xlsx_rows_as_documents_streaming(
                                file_path=file_path,
                                user_id=current_user_id,
                                file_tags=valid_tags,
                                source_name=title,
                                progress_callback=progress_callback
                            ):
                                yield progress_message
                    
                    # Process XLSX and yield progress updates in real-time
                    for progress_message in process_xlsx_with_progress():
                        yield progress_message
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Excel processing completed', 'percentage': 80})}\n\n"
                        
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'Processing {file_ext} file', 'percentage': 40})}\n\n"
                    content = f"[File uploaded: {file.filename}]\nContent extraction for {file_ext} files not yet implemented."
            
            except Exception as e:
                logging.error(f"Content extraction error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error extracting content: {str(e)}'})}\n\n"
                return
            
            # Use form summary if provided and not already set
            if form_summary and not summary:
                summary = form_summary
            
            
            # Final success message
            if file_ext in ['csv', 'xlsx']:
                # For CSV/XLSX, try to get record count for final message
                try:
                    import pandas as pd
                    if file_ext == 'csv':
                        df = pd.read_csv(file_path)
                        total_records = len(df)
                        message = f'CSV file uploaded successfully. Created {total_records + 1} documents: 1 overview + {total_records} individual records.'
                    else:  # xlsx
                        excel_file = pd.ExcelFile(file_path)
                        total_records = 0
                        for sheet_name in excel_file.sheet_names:
                            df = pd.read_excel(file_path, sheet_name=sheet_name)
                            total_records += len(df)
                        message = f'Excel file uploaded successfully. Created {total_records + 1} documents: 1 overview + {total_records} individual records from {len(excel_file.sheet_names)} sheets.'
                except Exception:
                    message = f'{file_ext.upper()} file uploaded successfully. Individual records processed as separate documents.'
            else:
                message = 'File uploaded successfully'
            
            yield f"data: {json.dumps({'type': 'success', 'message': message, 'filename': filename, 'percentage': 100})}\n\n"
            
        except Exception as e:
            logging.error(f"Streaming upload error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Upload failed: {str(e)}'})}\n\n"
    
    return Response(
        generate_upload_progress(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )


@bp.route('/documents/recent', methods=['GET'])
@jwt_required()
def get_recent_documents():
    """Get user's recently created documents."""
    try:
        current_user_id = int(get_jwt_identity())
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        documents = Document.get_recent_documents(current_user_id, limit)
        
        return jsonify({
            'documents': [doc.to_dict(include_content=False) for doc in documents],
            'count': len(documents)
        }), 200
        
    except Exception as e:
        logging.error(f"Get recent documents error: {e}")
        return jsonify({'error': 'Failed to get recent documents'}), 500


@bp.route('/documents/popular', methods=['GET'])
@jwt_required()
def get_popular_documents():
    """Get user's popular documents (by view count)."""
    try:
        current_user_id = int(get_jwt_identity())
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        documents = Document.get_popular_documents(current_user_id, limit)
        
        return jsonify({
            'documents': [doc.to_dict(include_content=False) for doc in documents],
            'count': len(documents)
        }), 200
        
    except Exception as e:
        logging.error(f"Get popular documents error: {e}")
        return jsonify({'error': 'Failed to get popular documents'}), 500


@bp.route('/tags', methods=['GET'])
@jwt_required()
def get_user_tags():
    """Get all tags used by the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        limit = request.args.get('limit', type=int)
        
        tags = Tag.get_user_tags(current_user_id, limit)
        
        return jsonify({
            'tags': [tag.to_dict() for tag in tags],
            'count': len(tags)
        }), 200
        
    except Exception as e:
        logging.error(f"Get user tags error: {e}")
        return jsonify({'error': 'Failed to get tags'}), 500


@bp.route('/tags/trending', methods=['GET'])
@jwt_required()
def get_trending_keywords():
    """Get trending keywords/tags for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        limit = min(request.args.get('limit', 10, type=int), 20)
        
        # Get user's trending tags ordered by usage count
        trending_tags = Tag.get_user_tags(current_user_id, limit)
        
        # Get tag statistics for the user
        tag_stats = Tag.get_tag_statistics(current_user_id)
        
        # Format trending tags with usage count
        trending_data = []
        for tag in trending_tags:
            # Get the document count for this tag for this user
            from app.models.document import Document, document_tags
            doc_count = db.session.query(func.count(document_tags.c.document_id))\
                                .join(Document)\
                                .filter(Document.user_id == current_user_id)\
                                .filter(document_tags.c.tag_id == tag.id)\
                                .scalar()
            
            # Calculate percentage based on total documents
            total_documents = Document.query.filter_by(user_id=current_user_id).count()
            percentage = round((doc_count / total_documents) * 100, 1) if total_documents > 0 else 0
            
            trending_data.append({
                'name': tag.name,
                'count': doc_count or 0,
                'color': tag.color,
                'percentage': percentage
            })
        
        return jsonify({
            'trending_keywords': trending_data,
            'total_keywords': tag_stats['total_tags'],
            'count': len(trending_data)
        }), 200
        
    except Exception as e:
        logging.error(f"Get trending keywords error: {e}")
        return jsonify({'error': 'Failed to get trending keywords'}), 500


@bp.route('/tags/search', methods=['GET'])
@jwt_required()
def search_tags():
    """Search tags by name."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        tags = Tag.search_tags(query, limit)
        
        return jsonify({
            'tags': [tag.to_dict() for tag in tags],
            'count': len(tags),
            'query': query
        }), 200
        
    except Exception as e:
        logging.error(f"Search tags error: {e}")
        return jsonify({'error': 'Failed to search tags'}), 500


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_content_stats():
    """Get content statistics for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get basic counts
        total_documents = Document.query.filter_by(user_id=current_user_id).count()
        total_tags = len(Tag.get_user_tags(current_user_id))
        
        # Get source type distribution
        source_types = db.session.query(
            Document.source_type,
            db.func.count(Document.id).label('count')
        ).filter_by(user_id=current_user_id)\
         .group_by(Document.source_type)\
         .all()
        
        source_distribution = [
            {'source_type': st.source_type, 'count': st.count}
            for st in source_types
        ]
        
        # Get processing status distribution
        processing_statuses = db.session.query(
            Document.processing_status,
            db.func.count(Document.id).label('count')
        ).filter_by(user_id=current_user_id)\
         .group_by(Document.processing_status)\
         .all()
        
        processing_distribution = [
            {'status': ps.processing_status, 'count': ps.count}
            for ps in processing_statuses
        ]
        
        # Get recent activity counts
        from datetime import datetime, timedelta
        
        # Documents created in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_docs = Document.query.filter(
            Document.user_id == current_user_id,
            Document.created_at >= thirty_days_ago
        ).count()
        
        return jsonify({
            'total_documents': total_documents,
            'total_tags': total_tags,
            'recent_documents': recent_docs,
            'source_distribution': source_distribution,
            'processing_distribution': processing_distribution
        }), 200
        
    except Exception as e:
        logging.error(f"Get content stats error: {e}")
        return jsonify({'error': 'Failed to get content statistics'}), 500
