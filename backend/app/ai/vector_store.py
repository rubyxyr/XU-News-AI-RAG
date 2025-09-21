"""
Vector store management using FAISS for efficient similarity search.
"""
import os
import pickle
import logging
from typing import List, Optional, Dict, Tuple, Any
import numpy as np
import faiss
try:
    # Try new LangChain structure first  
    from langchain_community.vectorstores import FAISS
    from langchain_core.embeddings import Embeddings
except ImportError:
    # Fall back to old structure
    from langchain.vectorstores import FAISS
    from langchain.embeddings.base import Embeddings

from langchain.docstore.document import Document as LangChainDocument

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manager for FAISS vector stores with user-specific isolation.
    """
    
    def __init__(self, base_path: str, embeddings: Embeddings):
        """
        Initialize the vector store manager.
        
        Args:
            base_path: Base directory path for storing vector stores
            embeddings: Embeddings instance for generating vectors
        """
        self.base_path = base_path
        self.embeddings = embeddings
        self.stores = {}  # Cache for loaded stores
        
        # Ensure base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        logger.info(f"Vector store manager initialized with base path: {base_path}")
    
    def _get_user_store_path(self, user_id: str) -> str:
        """Get the file path for a user's vector store."""
        return os.path.join(self.base_path, f"user_{user_id}")
    
    def create_user_store(self, user_id: str, documents: List[LangChainDocument]) -> bool:
        """
        Create a new vector store for a user with initial documents.
        
        Args:
            user_id: User identifier
            documents: Initial documents to add to the store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not documents:
                logger.warning(f"No documents provided for user {user_id} vector store")
                return False
            
            store_path = self._get_user_store_path(user_id)
            
            # Create new FAISS vector store
            vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # Save to disk
            vector_store.save_local(store_path)
            
            # Cache the store
            self.stores[user_id] = vector_store
            
            logger.info(f"Created vector store for user {user_id} with {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vector store for user {user_id}: {e}")
            return False
    
    def load_user_store(self, user_id: str) -> Optional[FAISS]:
        """
        Load a user's vector store from disk.
        
        Args:
            user_id: User identifier
            
        Returns:
            FAISS vector store or None if not found
        """
        try:
            # Check cache first
            if user_id in self.stores:
                return self.stores[user_id]
            
            store_path = self._get_user_store_path(user_id)
            
            # Check if store exists
            if not os.path.exists(store_path):
                logger.debug(f"No vector store found for user {user_id}")
                return None
            
            # Load from disk
            vector_store = FAISS.load_local(
                store_path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Cache the store
            self.stores[user_id] = vector_store
            
            logger.debug(f"Loaded vector store for user {user_id}")
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to load vector store for user {user_id}: {e}")
            return None
    
    def add_documents_to_user_store(
        self, 
        user_id: str, 
        documents: List[LangChainDocument]
    ) -> bool:
        """
        Add documents to an existing user's vector store.
        
        Args:
            user_id: User identifier
            documents: Documents to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not documents:
                logger.warning(f"No documents provided to add for user {user_id}")
                return False
            
            # Load existing store or create new one
            vector_store = self.load_user_store(user_id)
            
            if vector_store is None:
                # Create new store if none exists
                return self.create_user_store(user_id, documents)
            
            # Add documents to existing store
            vector_store.add_documents(documents)
            
            # Save updated store
            store_path = self._get_user_store_path(user_id)
            vector_store.save_local(store_path)
            
            # Update cache
            self.stores[user_id] = vector_store
            
            logger.info(f"Added {len(documents)} documents to user {user_id} vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to user {user_id} store: {e}")
            return False
    
    def remove_documents_from_user_store(
        self, 
        user_id: str, 
        document_ids: List[str]
    ) -> bool:
        """
        Remove documents from a user's vector store.
        Note: FAISS doesn't support direct deletion, so we need to rebuild the store.
        
        Args:
            user_id: User identifier
            document_ids: List of document IDs to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            vector_store = self.load_user_store(user_id)
            if vector_store is None:
                logger.warning(f"No vector store found for user {user_id}")
                return False
            
            # Get all documents, filtering out those to be removed
            all_docs = []
            docstore = vector_store.docstore
            
            for doc_id, doc in docstore._dict.items():
                # Check if this document should be removed by comparing metadata document_id
                doc_metadata = getattr(doc, 'metadata', {})
                metadata_doc_id = str(doc_metadata.get('document_id', ''))
                
                # Keep document if its document_id is not in the removal list
                if metadata_doc_id not in [str(did) for did in document_ids]:
                    all_docs.append(doc)
            
            if not all_docs:
                # If no documents left, delete the store
                return self.delete_user_store(user_id)
            
            # Rebuild store with remaining documents
            new_store = FAISS.from_documents(
                documents=all_docs,
                embedding=self.embeddings
            )
            
            # Save rebuilt store
            store_path = self._get_user_store_path(user_id)
            new_store.save_local(store_path)
            
            # Update cache
            self.stores[user_id] = new_store
            
            logger.info(f"Removed {len(document_ids)} documents from user {user_id} vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove documents from user {user_id} store: {e}")
            return False
    
    def search_user_store(
        self, 
        user_id: str, 
        query: str, 
        k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[LangChainDocument, float]]:
        """
        Search a user's vector store.
        
        Args:
            user_id: User identifier
            query: Search query
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of (document, score) tuples
        """
        try:
            vector_store = self.load_user_store(user_id)
            if vector_store is None:
                logger.debug(f"No vector store found for user {user_id}")
                return []
            
            # Perform similarity search with scores
            results = vector_store.similarity_search_with_score(query, k=k)
            
            # Filter by score threshold if provided
            if score_threshold is not None:
                results = [
                    (doc, score) for doc, score in results 
                    if (1 - score) >= score_threshold  # Convert distance to similarity
                ]
            
            logger.debug(f"Found {len(results)} results for user {user_id} query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search user {user_id} store: {e}")
            return []
    
    def delete_user_store(self, user_id: str) -> bool:
        """
        Delete a user's vector store.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            store_path = self._get_user_store_path(user_id)
            
            # Remove from cache
            if user_id in self.stores:
                del self.stores[user_id]
            
            # Delete files
            if os.path.exists(store_path):
                import shutil
                shutil.rmtree(store_path)
                logger.info(f"Deleted vector store for user {user_id}")
            else:
                logger.debug(f"No vector store to delete for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vector store for user {user_id}: {e}")
            return False
    
    def get_user_store_stats(self, user_id: str) -> Dict:
        """
        Get statistics about a user's vector store.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with statistics
        """
        try:
            vector_store = self.load_user_store(user_id)
            if vector_store is None:
                return {
                    'exists': False,
                    'document_count': 0,
                    'index_size': 0
                }
            
            # Get document count
            doc_count = len(vector_store.docstore._dict)
            
            # Get index size
            index_size = vector_store.index.ntotal if hasattr(vector_store.index, 'ntotal') else 0
            
            # Get store file size
            store_path = self._get_user_store_path(user_id)
            file_size = 0
            if os.path.exists(store_path):
                for root, dirs, files in os.walk(store_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_size += os.path.getsize(file_path)
            
            return {
                'exists': True,
                'document_count': doc_count,
                'index_size': index_size,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for user {user_id} store: {e}")
            return {
                'exists': False,
                'error': str(e)
            }
    
    def list_user_stores(self) -> List[str]:
        """
        List all user IDs that have vector stores.
        
        Returns:
            List of user IDs
        """
        try:
            user_ids = []
            
            for item in os.listdir(self.base_path):
                if item.startswith('user_') and os.path.isdir(os.path.join(self.base_path, item)):
                    user_id = item[5:]  # Remove 'user_' prefix
                    user_ids.append(user_id)
            
            return user_ids
            
        except Exception as e:
            logger.error(f"Failed to list user stores: {e}")
            return []
    
    def get_global_stats(self) -> Dict:
        """
        Get global statistics for all vector stores.
        
        Returns:
            Dictionary with global statistics
        """
        try:
            user_ids = self.list_user_stores()
            
            total_documents = 0
            total_size = 0
            store_count = len(user_ids)
            
            for user_id in user_ids:
                stats = self.get_user_store_stats(user_id)
                if stats['exists']:
                    total_documents += stats['document_count']
                    total_size += stats['file_size_bytes']
            
            return {
                'total_stores': store_count,
                'total_documents': total_documents,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cached_stores': len(self.stores)
            }
            
        except Exception as e:
            logger.error(f"Failed to get global stats: {e}")
            return {
                'error': str(e)
            }
    
    def optimize_user_store(self, user_id: str) -> bool:
        """
        Optimize a user's vector store (rebuild index for better performance).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            vector_store = self.load_user_store(user_id)
            if vector_store is None:
                logger.warning(f"No vector store found for user {user_id}")
                return False
            
            # Get all documents
            all_docs = list(vector_store.docstore._dict.values())
            
            if not all_docs:
                logger.warning(f"No documents in store for user {user_id}")
                return True
            
            # Rebuild store
            new_store = FAISS.from_documents(
                documents=all_docs,
                embedding=self.embeddings
            )
            
            # Save optimized store
            store_path = self._get_user_store_path(user_id)
            new_store.save_local(store_path)
            
            # Update cache
            self.stores[user_id] = new_store
            
            logger.info(f"Optimized vector store for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize store for user {user_id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear the in-memory cache of vector stores."""
        self.stores.clear()
        logger.info("Cleared vector store cache")
