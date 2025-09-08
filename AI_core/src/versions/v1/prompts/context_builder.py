import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.llms.gemini import LLMGemini
from src.utils.logger import Logger
import yaml

from src.memory.conversation.redisMemory import RedisConversationMemory

logger = Logger(__name__)


def load_short_term_memory(session_id: str):
    """Load short term memory from Redis"""
    try:
        redis_memory = RedisConversationMemory(session_id=session_id).get_conversation_history()
        logger.info(f"Loaded messages from short term memory")
        return redis_memory
    except Exception as e:
        logger.error(f"❌ Error loading short term memory: {e}")
        return ""



def load_prompt(md_file_path: str) -> str:
    """
    Load and build booking prompt from YAML file with function definitions
    """
    try:
        # Load YAML content
        with open(md_file_path, 'r', encoding='utf-8') as file:
            prompt_config = file.read()

        # Build the complete prompt
        prompt_parts = []
        if 'ROLE' in prompt_config:
            prompt_parts.append("## ROLE")
            prompt_parts.append(prompt_config['ROLE'])
        complete_prompt = str(prompt_parts)
        return complete_prompt

    except Exception as e:
        logger.error(f"❌ Error loading prompt from YAML: {str(e)}")
        return ""

def rag_context(query: str="", user_id: str = None) -> str:
    """
    Prepare enhanced query with RAG context using hybrid search.
    Flow: query → RAG → enhance context → prompt → agent

    Args:
        query: User's question/query
        user_id: Optional user ID for personalized results

    Returns:
        str: Enhanced query with RAG context or original query if no context found
    """
    try:
        if not query or not query.strip():
            logger.warning("⚠️ [RAG Context] Empty query provided")
            return query

        from src.versions.v1.tools.knowledge_RAG import KnowledgeBase

        # Initialize KnowledgeBase
        kb = KnowledgeBase()

        # Check health first
        health = kb.get_health_status()
        if health.get("status") != "healthy":
            logger.warning(f"⚠️ [RAG Context] Database service unhealthy: {health.get('error', 'Unknown error')}")
            return query

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
            return enhanced_query

        # Format context for prompt
        knowledge_context = kb.format_for_prompt(rag_result, include_metadata=False)

        if knowledge_context and "No relevant information found" not in knowledge_context:
            # Build enhanced prompt with RAG context
            enhanced_query_with_context = f"""
Reference information from the knowledge base:
{knowledge_context}
"""

            # Log success metrics
            search_type = rag_result.get("search_type", "unknown")
            source_count = rag_result.get("source_count", 0)
            context_length = rag_result.get("context_length", 0)

            logger.info(f"[RAG Context] Enhanced query with {search_type} search: {source_count} sources, {context_length} chars")

            return enhanced_query_with_context.strip()
        else:
            logger.warning(f"[RAG Context] No usable context generated for query: '{enhanced_query}'")
            return enhanced_query

    except ImportError as e:
        logger.error(f"[RAG Context] Import error: {str(e)}")
        return query
    except Exception as e:
        logger.error(f"[RAG Context] Error preparing enhanced query: {str(e)}")
        return query
        
        
        
def build_context_v1(
    yaml_path: str,
    query: str = None,
    session_id: str = "default",
    user_id: str = None
    ):
    """Create a tasker-specific prompt template for V1 with static tools section"""
    short_term_memory = load_short_term_memory(session_id)
    system_prompt = load_prompt(yaml_path)

    # RAG Context: query → RAG → enhance context → prompt → agent
    rag_context_result = ""
    if query and query.strip():
        try:
            rag_context_result = rag_context(query)  # Temporarily remove user_id filtering for UI testing
            logger.info(f"✅ [Context Builder] RAG context prepared for query: '{query[:50]}...'")
        except Exception as e:
            logger.error(f"❌ [Context Builder] Failed to prepare RAG context: {str(e)}")
            rag_context_result = ""

    # Handle empty short_term_memory
    memory_context = ""
    if short_term_memory and len(short_term_memory) > 0:
        # Format memory for context
        memory_parts = []
        for msg in short_term_memory:
            if msg.get("type") == "human":
                memory_parts.append(f"User: {msg.get('content', '')}")
            elif msg.get("type") == "ai":
                memory_parts.append(f"Assistant: {msg.get('content', '')}")
        memory_context = "\n".join(memory_parts) if memory_parts else ""

    # Combine all system instructions into one message to avoid multiple SystemMessages
    # Build prompt messages - only include memory context if it exists
    messages = [
        ("system",system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", rag_context_result),
        ("human", "The user's query: **{input}**"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
    # Add memory context only if it exists
    if memory_context:
        messages.append(("assistant", f"Memory:\n{memory_context}"))

    prompt = ChatPromptTemplate.from_messages(messages)

    return prompt


