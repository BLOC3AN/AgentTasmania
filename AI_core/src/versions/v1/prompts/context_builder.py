import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.utils.logger import Logger
from src.versions.v1.tools.knowledge_RAG import KnowledgeBase
logger = Logger(__name__)

def load_prompt(md_file_path: str) -> str:
    """
    Load and build booking prompt from YAML file with function definitions
    """
    try:
        # Load YAML content
        with open(md_file_path, 'r', encoding='utf-8') as file:
            prompt_config = file.read()
        return prompt_config

    except Exception as e:
        logger.error(f"❌ Error loading prompt from Markdown: {str(e)}")
        return ""

def rag_context(query: str="", user_id: str = None) -> str:
    """
    Prepare enhanced RAG context using hybrid search.
    Flow: query → RAG → enhance context → return context only

    Args:
        query: User's question/query
        user_id: Optional user ID for personalized results

    Returns:
        str: RAG context information or empty string if no context found
    """
    try:
        if not query or not query.strip():
            logger.warning("⚠️ [RAG Context] Empty query provided")
            return ""

        # Initialize KnowledgeBase
        kb = KnowledgeBase()
        # Check health first
        health = kb.get_health_status()
        if health.get("status") != "healthy":
            logger.warning(f"⚠️ [RAG Context] Database service unhealthy: {health.get('error', 'Unknown error')}")
            return ""

        enhanced_query = query.strip()
        logger.info(f"🔍 [RAG Context] Processing query: '{enhanced_query}'")

        # RAG Pipeline: search → enhance context → format for prompt
        rag_result = kb.search_and_enhance(
            query=enhanced_query,
            limit=5,                    # Top 5 most relevant results
            score_threshold=0.5,        # Minimum relevance score
            max_context_length=2000,    # Max context length for prompt
            user_id=None               # Temporarily disable user filtering for UI testing
        )

        # Check if we got relevant results
        if not rag_result.get("search_success", False) or rag_result.get("source_count", 0) == 0:
            logger.info(f"ℹ️ [RAG Context] No relevant information found for query: '{enhanced_query}'")
            return ""  # Return empty string instead of query to avoid duplication

        # Format context for prompt
        knowledge_context = kb.format_for_prompt(rag_result, include_metadata=False)

        if knowledge_context and "No relevant information found" not in knowledge_context:
            # Build enhanced RAG context
            rag_context_formatted = f"""Reference information from the document:{knowledge_context}"""

            # Log success metrics
            search_type = rag_result.get("search_type", "unknown")
            source_count = rag_result.get("source_count", 0)
            context_length = rag_result.get("context_length", 0)

            logger.info(f"[RAG Context] Enhanced context with {search_type} search: {source_count} sources, {context_length} chars")

            return rag_context_formatted.strip()
        else:
            logger.warning(f"[RAG Context] No usable context generated for query: '{enhanced_query}'")
            return ""

    except ImportError as e:
        logger.error(f"[RAG Context] Import error: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"[RAG Context] Error preparing enhanced query: {str(e)}")
        return ""
        
        
        
def build_context_v1(
    yaml_path: str,
    query: str = None,
    user_id: str = None
    ):
    """Create a tasker-specific prompt template for V1 with static tools section"""
    system_prompt = load_prompt(yaml_path)

    # RAG Context: query → RAG → enhance context → prompt → agent
    rag_context_result = ""
    if query and query.strip():
        try:
            rag_context_result = rag_context(query, user_id)
            logger.info(f"[Context Builder] RAG context prepared for query: '{query[:50]}...'")
        except Exception as e:
            logger.error(f"[Context Builder] Failed to prepare RAG context: {str(e)}")
            rag_context_result = ""

    messages = [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
    ]

    # Add RAG context only if it exists and is not empty
    if rag_context_result and rag_context_result.strip():
        messages.append(("assistant", rag_context_result))

    # Add user input
    messages.extend([
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    prompt = ChatPromptTemplate.from_messages(messages)

    return prompt


