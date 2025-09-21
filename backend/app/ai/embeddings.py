"""
Embeddings management for semantic search and document processing.
"""
import logging
import numpy as np
from typing import List, Optional, Union, Dict
from sentence_transformers import SentenceTransformer
try:
    # Try new LangChain structure first
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    # Fall back to old structure
    from langchain.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingWrapper:
    """
    A wrapper class that makes SentenceTransformer compatible with LangChain embeddings interface.
    This is a fallback when HuggingFaceEmbeddings has compatibility issues.
    """
    
    def __init__(self, model):
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to embed documents: {e}")
            return []
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        try:
            embedding = self.model.encode([text], normalize_embeddings=True)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []


class EmbeddingManager:
    """
    Manager for generating and handling embeddings using various models.
    """
    
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """
        Initialize the embedding manager.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.langchain_embeddings = None
        
        try:
            # Initialize sentence transformer model with better error handling
            logger.info(f"Attempting to initialize SentenceTransformer model: {model_name}")
            
            # Try to initialize with cache_folder and offline mode if network fails
            from flask import current_app
            try:
                self.model = SentenceTransformer(model_name, cache_folder=current_app.config.get('EMBEDDINGS_MODEL_CACHE_FOLDER'))
                logger.info(f"SentenceTransformer model initialized successfully: {model_name}")
            except Exception as download_error:
                logger.warning(f"Failed to download/initialize model {model_name}: {download_error}")
                
                # Try to use a local cache or simpler approach
                try:
                    # Try with local_files_only to use cached version
                    self.model = SentenceTransformer(model_name, cache_folder=current_app.config.get('EMBEDDINGS_MODEL_CACHE_FOLDER'))
                    logger.info(f"Using cached SentenceTransformer model: {model_name}")
                except Exception as cache_error:
                    logger.error(f"Failed to use cached model: {cache_error}")
                    # Fallback to None - will use keyword search instead
                    self.model = None
                    self.langchain_embeddings = None
                    logger.warning("SentenceTransformer unavailable - will use keyword search fallback")
                    return
            
            # Try to initialize LangChain embeddings wrapper if model is available
            if self.model:
                try:
                    self.langchain_embeddings = HuggingFaceEmbeddings(
                        model_name=model_name,
                        model_kwargs={'device': 'cpu'},  # Use CPU by default
                        encode_kwargs={'normalize_embeddings': True}
                    )
                    logger.info(f"LangChain HuggingFaceEmbeddings initialized: {model_name}")
                except Exception as lc_error:
                    logger.warning(f"Failed to initialize LangChain HuggingFaceEmbeddings: {lc_error}")
                    # Create a simple wrapper for the sentence transformer
                    self.langchain_embeddings = SentenceTransformerEmbeddingWrapper(self.model)
                    logger.info(f"Using SentenceTransformer wrapper instead of LangChain embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding manager: {e}")
            # Don't raise - allow graceful degradation to keyword search
            self.model = None
            self.langchain_embeddings = None
    
    @property
    def embeddings(self):
        """Get LangChain embeddings wrapper."""
        return self.langchain_embeddings
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts into embeddings.
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            Numpy array of embeddings
        """
        try:
            if not texts:
                return np.array([])
            
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise
    
    def encode_single_text(self, text: str) -> np.ndarray:
        """
        Encode a single text into embedding.
        
        Args:
            text: Text string to encode
            
        Returns:
            Numpy array embedding
        """
        return self.encode_texts([text])[0]
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            embeddings = self.encode_texts([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1])
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def find_most_similar(
        self, 
        query: str, 
        candidates: List[str], 
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar texts to a query.
        
        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of top results to return
            
        Returns:
            List of (text, similarity_score) tuples
        """
        try:
            if not candidates:
                return []
            
            # Encode query and candidates
            query_embedding = self.encode_single_text(query)
            candidate_embeddings = self.encode_texts(candidates)
            
            # Compute similarities
            similarities = np.dot(candidate_embeddings, query_embedding)
            
            # Get top k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Return results
            results = []
            for idx in top_indices:
                results.append((candidates[idx], float(similarities[idx])))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find most similar texts: {e}")
            return []
    
    def get_model_info(self) -> Dict:
        """
        Get information about the embedding model.
        
        Returns:
            Dictionary with model information
        """
        try:
            return {
                'model_name': self.model_name,
                'embedding_dimension': self.model.get_sentence_embedding_dimension(),
                'max_seq_length': self.model.max_seq_length,
                'device': str(self.model.device),
            }
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {
                'model_name': self.model_name,
                'error': str(e)
            }
