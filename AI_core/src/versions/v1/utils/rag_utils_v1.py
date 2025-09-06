import weaviate
from src.utils.logger import Logger
import os
logger = Logger(__name__)

class RAGRetrieverV1:
    """Enhanced RAG Retriever for V1 with hybrid search"""
    
    def __init__(self, host: str = "weaviate", port: int = 8080, collection: str = "cs"):
        self.host = os.getenv("WEAVIATE_HOST", "weaviate")
        self.port = int(os.getenv("WEAVIATE_PORT", "8080"))
        self.collection = os.getenv("WEAVIATE_COL_CS", "cs")
        self.client = self._connect_to_weaviate()
        
        # Check if collection exists, create it if it doesn't
        self._ensure_collection_exists()
        
        logger.info(f"✅ [V1] RAGRetrieverV1 initialized with hybrid search at {host}:{self.port}, collection {collection}")

    def _connect_to_weaviate(self):
        """Connect to Weaviate database"""
        try:
            client = weaviate.connect_to_local(
                host=self.host,
                port=self.port
            )
            return client
        except Exception as e:
            logger.error(f"❌ [V1] Failed to connect to Weaviate: {str(e)}")
            return None

    def _ensure_collection_exists(self):
        """Ensure the collection exists in Weaviate"""
        if not self.client:
            logger.error("❌ [V1] No Weaviate client available")
            return

        try:
            if self.client.collections.exists(self.collection):
                logger.info(f"✅ [V1] Collection {self.collection} exists")
            else:
                logger.warning(f"⚠️ [V1] Collection {self.collection} does not exist")
        except Exception as e:
            logger.error(f"❌ [V1] Error checking collection existence: {str(e)}")

    def retrieve(self, query: str, limit: int = 9):
        """Enhanced retrieval with hybrid search for V1"""   
        try:
            # Get the collection object
            collection = self.client.collections.get(self.collection)
            
            # Use hybrid search instead of near_text for better results
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                alpha=0.5 
            )

            chunks = []
            for obj in response.objects:
                chunk = obj.properties.get("content", "")
                if chunk:
                    chunks.append(chunk)
            
            logger.info(f"✅ [V1] Hybrid search retrieved {len(chunks)} documents for query: '{query}'")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ [V1] Error in hybrid search: {str(e)}")
            return ["Không thể truy cập dữ liệu. Vui lòng thử lại sau."]

    def close(self):
        """Close the Weaviate client connection"""
        try:
            if self.client:
                self.client.close()
        except Exception as e:
            logger.error(f"❌ [V1] Error closing Weaviate client: {str(e)}")

    def __del__(self):
        """Destructor to ensure connection is closed"""
        try:
            self.close()
        except:
            pass
