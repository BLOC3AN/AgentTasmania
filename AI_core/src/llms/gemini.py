from langchain_google_genai import ChatGoogleGenerativeAI #type:ignore
from src.utils.logger import Logger
logger = Logger(__name__)

class LLMGemini:
    def __init__(self, llm_model_name:str = "gemini-2.0-flash"):
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model_name,
            temperature=0,
            top_p=0.2,
            top_k=50,
            max_tokens=None,
            max_output_tokens=1024,  # Increased from 250 to allow longer responses
            verbose=True,  
            disable_streaming=True,  
        )
        self.name = self.llm.model


