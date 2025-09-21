"""
LangChain integration service for document processing and semantic search.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import numpy as np
try:
    # Try new LangChain structure first
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_community.llms import Ollama
except ImportError:
    # Fall back to old structure
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
    from langchain.llms import Ollama

try:
    # Try new LangChain structure for remaining imports
    from langchain_community.document_loaders import TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain.docstore.document import Document as LangChainDocument
except ImportError:
    # Fall back to old structure
    from langchain.document_loaders import TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain.docstore.document import Document as LangChainDocument
from sentence_transformers import CrossEncoder

from app.models import Document
from app.ai.embeddings import EmbeddingManager
from app.ai.vector_store import VectorStoreManager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIProcessingPipeline:
    """
    Main AI processing pipeline integrating LangChain components
    for document processing, embedding generation, and semantic search.
    """
    
    def __init__(self, config=None):
        """
        Initialize the AI processing pipeline.
        
        Args:
            config: Configuration dictionary with model settings
        """
        self.config = config or {}
        
        # Initialize components
        self.embedding_manager = EmbeddingManager(
            model_name=self.config.get('EMBEDDINGS_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        )
        
        self.vector_store_manager = VectorStoreManager(
            base_path=self.config.get('VECTOR_STORE_PATH', 'data/vector_stores'),
            embeddings=self.embedding_manager.embeddings
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize LLM
        try:
            self.llm = Ollama(
                model=self.config.get('LLM_MODEL', 'qwen3:4b'),
                base_url=self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                temperature=0.3
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama LLM: {e}")
            self.llm = None
        
        # Initialize reranker
        try:
            self.reranker = CrossEncoder(
                self.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
            )
        except Exception as e:
            logger.warning(f"Failed to initialize reranker: {e}")
            self.reranker = None
        
        logger.info("AI Processing Pipeline initialized successfully")
    
    def process_document(self, document: Document) -> bool:
        """
        Process a document through the AI pipeline.
        
        Args:
            document: Document model instance to process
            
        Returns:
            bool: Success status of processing
        """
        try:
            # Update processing status
            document.update_processing_status('processing')
            
            # Split document into chunks
            chunks = self.text_splitter.split_text(document.content)
            
            # Create LangChain documents
            langchain_docs = []
            for i, chunk in enumerate(chunks):
                metadata = {
                    'document_id': document.id,
                    'chunk_id': i,
                    'title': document.title,
                    'source_type': document.source_type,
                    'source_url': document.source_url,
                    'created_at': document.created_at.isoformat() if document.created_at else None
                }
                
                langchain_doc = LangChainDocument(
                    page_content=chunk,
                    metadata=metadata
                )
                langchain_docs.append(langchain_doc)
            
            # Generate and store embeddings
            success = self.vector_store_manager.add_documents_to_user_store(
                str(document.user_id),
                langchain_docs
            )
            
            if success:
                # Generate summary if LLM is available
                summary = self.generate_summary(document.content) if self.llm else None
                if summary and not document.summary:
                    document.summary = summary
                
                # Update document status
                document.update_processing_status('completed')
                document.vector_id = f"user_{document.user_id}_doc_{document.id}"
                
                logger.info(f"Successfully processed document {document.id}")
                return True
            else:
                document.update_processing_status('failed', 'Failed to generate embeddings')
                return False
                
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            document.update_processing_status('failed', str(e))
            return False
    
    def remove_document(self, document: Document) -> bool:
        """
        Remove a document from the vector store.
        
        Args:
            document: Document model instance to remove from vector store
            
        Returns:
            bool: Success status of removal
        """
        try:
            user_id = str(document.user_id)
            document_id = str(document.id)
            
            # Remove from vector store
            success = self.vector_store_manager.remove_documents_from_user_store(
                user_id, 
                [document_id]
            )
            
            if success:
                logger.info(f"Successfully removed document {document.id} from vector store")
                return True
            else:
                logger.warning(f"Failed to remove document {document.id} from vector store")
                return False
                
        except Exception as e:
            logger.error(f"Error removing document {document.id} from vector store: {e}")
            return False
    
    def semantic_search(
        self, 
        user_id: str, 
        query: str, 
        k: int = 10, 
        filters: Optional[Dict] = None,
        score_threshold: Optional[float] = 0.3
    ) -> List[Tuple[Document, float]]:
        """
        Perform semantic search on user's knowledge base.
        
        Args:
            user_id: User ID for personalized search
            query: Search query string
            k: Number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of (Document, similarity_score) tuples
        """
        try:
            # Get user's vector store
            vector_store = self.vector_store_manager.load_user_store(user_id)
            
            if not vector_store:
                logger.warning(f"No vector store found for user {user_id}")
                return []
            
            # Perform similarity search
            docs_and_scores = vector_store.similarity_search_with_score(query, k=k * 2)
            
            # Extract document IDs and get full document objects
            results = []
            seen_doc_ids = set()
            
            for doc, score in docs_and_scores:
                doc_id = doc.metadata.get('document_id')
                if doc_id and doc_id not in seen_doc_ids:
                    # Get full document from database
                    full_doc = Document.query.filter_by(
                        id=doc_id,
                        user_id=int(user_id)
                    ).first()
                    
                    if full_doc:
                        # Apply filters if provided
                        if self._apply_filters(full_doc, filters):
                            # Convert FAISS distance to similarity score using reciprocal function
                            # This handles distances > 1.0 gracefully and always returns positive values
                            # Distance 0 → similarity 1.0, Distance 1 → similarity 0.5, Distance 10 → similarity 0.091
                            similarity_score = 1.0 / (1.0 + score)
                            
                            logger.info(f"[+] AI Processing Pipeline: Distance: {score:.4f} → Similarity: {similarity_score:.4f}")
                            if similarity_score >= score_threshold:
                                results.append((full_doc, similarity_score))
                                seen_doc_ids.add(doc_id)
                        
                        if len(results) >= k:
                            break
            
            # Rerank results if reranker is available
            if self.reranker and results:
                results = self._rerank_results(query, results)
            
            logger.info(f"Semantic search returned {len(results)} results for user {user_id}")
            return results[:k]
            
        except Exception as e:
            logger.error(f"Semantic search error for user {user_id}: {e}")
            return []
    
    def generate_summary(self, content: str, max_length: int = 200) -> Optional[str]:
        """
        Generate a summary of the given content using LLM.
        
        Args:
            content: Text content to summarize
            max_length: Maximum length of summary
            
        Returns:
            Generated summary or None if failed
        """
        if not self.llm:
            return None
        
        try:
            # Truncate content if too long
            if len(content) > 3000:
                content = content[:3000] + "..."
            
            prompt = f"""
            Please provide a concise summary of the following text in no more than {max_length} characters:
            
            {content}
            
            Summary:
            """
            
            summary = self.llm(prompt)
            
            # Clean up the summary
            summary = summary.strip()
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return None

    def generate_summary_stream(self, content: str, max_length: int = 200):
        """
        Generate a summary of the given content using LLM with streaming output.
        
        Args:
            content: Text content to summarize
            max_length: Maximum length of summary
            
        Yields:
            dict: Streaming progress updates with partial summary text
        """
        if not self.llm:
            yield {
                'status': 'error',
                'message': 'LLM not available for streaming summary',
                'partial_text': ''
            }
            return
        
        try:
            # Truncate content if too long
            if len(content) > 3000:
                content = content[:3000] + "..."
            
            prompt = f"""
            Please provide a concise summary of the following text in no more than {max_length} characters:
            
            {content}
            
            Summary:
            """
            
            yield {
                'status': 'starting',
                'message': 'Starting AI summary generation...',
                'partial_text': ''
            }
            
            # Use streaming with Ollama
            accumulated_text = ""
            try:
                # Stream the response from Ollama
                for chunk in self.llm.stream(prompt):
                    accumulated_text += chunk
                    
                    # Yield streaming update with current accumulated text
                    yield {
                        'status': 'streaming',
                        'message': 'Generating summary...',
                        'partial_text': accumulated_text.strip()
                    }
                    
                    # Stop if we've reached max length
                    if len(accumulated_text.strip()) >= max_length:
                        break
                
                # Clean up the final summary
                final_summary = accumulated_text.strip()
                if len(final_summary) > max_length:
                    final_summary = final_summary[:max_length - 3] + "..."
                
                yield {
                    'status': 'completed',
                    'message': 'Summary generation completed',
                    'partial_text': final_summary,
                    'final_summary': final_summary
                }
                
            except AttributeError:
                # Fallback if stream method doesn't exist - use regular generation
                logger.warning("LLM doesn't support streaming, falling back to regular generation")
                summary = self.llm(prompt)
                
                # Clean up the summary
                summary = summary.strip()
                if len(summary) > max_length:
                    summary = summary[:max_length - 3] + "..."
                
                yield {
                    'status': 'completed',
                    'message': 'Summary generation completed (non-streaming)',
                    'partial_text': summary,
                    'final_summary': summary
                }
                
        except Exception as e:
            logger.error(f"Streaming summary generation error: {e}")
            yield {
                'status': 'error',
                'message': f'Summary generation failed: {str(e)}',
                'partial_text': '',
                'error': str(e)
            }
    
    def answer_question(
        self, 
        user_id: str, 
        question: str, 
        context_docs: Optional[List[Document]] = None
    ) -> Optional[str]:
        """
        Answer a question using the knowledge base and LLM.
        
        Args:
            user_id: User ID for personalized search
            question: Question to answer
            context_docs: Optional pre-retrieved context documents
            
        Returns:
            Generated answer or None if failed
        """
        if not self.llm:
            return None
        
        try:
            # Get relevant documents if not provided
            if not context_docs:
                search_results = self.semantic_search(user_id, question, k=5)
                context_docs = [doc for doc, _ in search_results]
            
            if not context_docs:
                return "I couldn't find relevant information in your knowledge base to answer this question."
            
            # Prepare context from documents
            context_text = "\n\n".join([
                f"Document: {doc.title}\n{doc.content[:500]}..."
                for doc in context_docs[:3]  # Limit context to avoid token limits
            ])
            
            # Generate prompt
            prompt = f"""
            Based on the following documents from the knowledge base, please answer the question.
            If the information is not sufficient, please say so.
            
            Documents:
            {context_text}
            
            Question: {question}
            
            Answer:
            """
            
            answer = self.llm(prompt)
            
            return answer.strip()
            
        except Exception as e:
            logger.error(f"Question answering error: {e}")
            return None
    
    def _apply_filters(self, document: Document, filters: Optional[Dict]) -> bool:
        """
        Apply filters to determine if document should be included in results.
        
        Args:
            document: Document to check
            filters: Filter criteria
            
        Returns:
            bool: True if document passes filters
        """
        if not filters:
            return True
        
        try:
            # Source type filter
            if filters.get('source_type') and document.source_type != filters['source_type']:
                return False
            
            # Date range filters
            if filters.get('date_from') and document.published_date:
                date_from = datetime.fromisoformat(filters['date_from'])
                if document.published_date < date_from:
                    return False
            
            if filters.get('date_to') and document.published_date:
                date_to = datetime.fromisoformat(filters['date_to'])
                if document.published_date > date_to:
                    return False
            
            # Tag filters
            if filters.get('tags'):
                filter_tags = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                document_tags = [tag.name for tag in document.tags]
                if not any(tag in document_tags for tag in filter_tags):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Filter application error: {e}")
            return True  # Include document if filter fails
    
    def _rerank_results(
        self, 
        query: str, 
        results: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """
        Rerank search results using cross-encoder while preserving similarity scores.
        
        Args:
            query: Original search query
            results: List of (Document, similarity_score) tuples
            
        Returns:
            Reranked results with preserved similarity scores
        """
        if not self.reranker or len(results) <= 1:
            return results
        
        try:
            # Prepare query-document pairs
            pairs = []
            for doc, _ in results:
                content = f"{doc.title} {doc.content[:500]}"  # Title + content snippet
                pairs.append([query, content])
            
            # Get reranking scores (for ordering only)
            rerank_scores = self.reranker.predict(pairs)
            
            # Create tuples with both original similarity and rerank scores
            combined_results = []
            for i, (doc, original_similarity) in enumerate(results):
                rerank_score = float(rerank_scores[i])
                # Keep original similarity score, use rerank score only for ordering
                combined_results.append((doc, original_similarity, rerank_score))
                logger.debug(f"Doc {doc.id}: Similarity={original_similarity:.4f}, Rerank={rerank_score:.4f}")
            
            # Sort by reranking score (descending) but keep similarity scores
            combined_results.sort(key=lambda x: x[2], reverse=True)  # Sort by rerank_score
            
            # Extract results with original similarity scores preserved
            reranked_results = [(doc, similarity_score) for doc, similarity_score, _ in combined_results]
            
            logger.info(f"Reranked {len(results)} results while preserving similarity scores (order changed by cross-encoder)")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return results  # Return original results if reranking fails
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get status information about the AI pipeline components.
        
        Returns:
            Dictionary with component status information
        """
        status = {
            'embedding_manager': {
                'available': self.embedding_manager is not None,
                'model': self.config.get('EMBEDDINGS_MODEL', 'N/A')
            },
            'vector_store_manager': {
                'available': self.vector_store_manager is not None,
                'base_path': self.config.get('VECTOR_STORE_PATH', 'N/A')
            },
            'llm': {
                'available': self.llm is not None,
                'model': self.config.get('LLM_MODEL', 'N/A'),
                'base_url': self.config.get('OLLAMA_BASE_URL', 'N/A')
            },
            'reranker': {
                'available': self.reranker is not None,
                'model': self.config.get('RERANKER_MODEL', 'N/A')
            },
            'text_splitter': {
                'available': self.text_splitter is not None,
                'chunk_size': 1000,
                'chunk_overlap': 200
            }
        }
        
        return status


# Alias for backward compatibility and easier imports
LangChainService = AIProcessingPipeline
