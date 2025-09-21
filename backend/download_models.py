

#!/usr/bin/env python3
"""
Model download script for XU-News AI-RAG.
Downloads and caches AI models to avoid network issues during runtime.
"""
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_sentence_transformer(model_name='sentence-transformers/all-MiniLM-L6-v2'):
    """Download and cache sentence transformer model."""
    try:
        logger.info(f"Downloading SentenceTransformer model: {model_name}")
        from sentence_transformers import SentenceTransformer
        
        # Create cache directory
        cache_dir = backend_dir / 'data' / 'models'
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Download model
        model = SentenceTransformer(model_name, cache_folder=str(cache_dir))
        logger.info(f"Successfully downloaded model: {model_name}")
        
        # Test the model
        test_text = "This is a test sentence."
        embedding = model.encode([test_text])
        logger.info(f"Model test successful. Embedding shape: {embedding.shape}")
        
        return True
        
    except ImportError as e:
        logger.error(f"sentence-transformers not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download model {model_name}: {e}")
        return False

def download_huggingface_models():
    """Download other required HuggingFace models."""
    models = [
        'sentence-transformers/all-MiniLM-L6-v2',
        # Add other models here if needed
    ]
    
    success_count = 0
    for model_name in models:
        if download_sentence_transformer(model_name):
            success_count += 1
        else:
            logger.warning(f"Failed to download {model_name}")
    
    return success_count, len(models)

def test_model_availability():
    """Test if models are available and working."""
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        
        # Try to load from cache
        logger.info("Testing model availability...")
        model = SentenceTransformer(model_name, cache_folder=str(backend_dir / 'data' / 'models'))
        
        # Test encoding
        test_texts = ["Hello world", "How are you?"]
        embeddings = model.encode(test_texts)
        
        logger.info(f"Model test successful:")
        logger.info(f"  - Model: {model_name}")
        logger.info(f"  - Test texts: {len(test_texts)}")
        logger.info(f"  - Embeddings shape: {embeddings.shape}")
        logger.info(f"  - Embedding dimension: {embeddings.shape[1]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Model availability test failed: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting model download process...")
    
    # Check if sentence-transformers is installed
    try:
        import sentence_transformers
        logger.info(f"sentence-transformers version: {sentence_transformers.__version__}")
    except ImportError:
        logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
        return 1
    
    # Download models
    success_count, total_count = download_huggingface_models()
    logger.info(f"Downloaded {success_count}/{total_count} models successfully")
    
    # Test model availability
    if test_model_availability():
        logger.info("✅ All models are available and working!")
        return 0
    else:
        logger.error("❌ Model availability test failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
