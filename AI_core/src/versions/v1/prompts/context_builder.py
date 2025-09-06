import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timezone, timedelta
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

def load_language_instructions(language: str) -> str:
    """Load language instructions from system"""
    language_instructions = {
        "VietNam": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in Vietnamese. All your answers must be written entirely in Vietnamese with no mixing of other languages.
    Do not use English or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full Vietnamese language only"
        },
        "ThaiLan": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in Thai. All your answers must be written entirely in Thai with no mixing of other languages.
    Do not use English or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full Thai language only"
        },
        "English": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in English. All your answers must be written entirely in English with no mixing of other languages.
    Do not use Vietnamese, Thai, or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full English language only"
        },
        # Support for detected_language codes from speech-to-text
        "en": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in English. All your answers must be written entirely in English with no mixing of other languages.
    Do not use Vietnamese, Thai, or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full English language only"
        },
        "vi": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in Vietnamese. All your answers must be written entirely in Vietnamese with no mixing of other languages.
    Do not use English or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full Vietnamese language only"
        },
        "th": {
            "system": """
    === RESPONSE LANGUAGE ===
    IMPORTANT: You MUST respond strictly in Thai. All your answers must be written entirely in Thai with no mixing of other languages.
    Do not use English or any other language in your response, even partially.
    """,
            "format": ", response language:Check gramma and response full Thai language  language only"
        }
    }
    
    lang_config = language_instructions.get(language, language_instructions["VietNam"])
    return lang_config

def load_prompt(yaml_file_path: str) -> str:
    """
    Load and build booking prompt from YAML file with function definitions
    """
    try:
        # Load YAML content
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            prompt_config = yaml.safe_load(file)

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

Please answer the question based on the reference information above.
Guidelines:
- Use the provided information as your primary source
- Be accurate and detailed in your response
- If the information is insufficient, clearly state what additional details are needed
- Keep the tool usage confidential and address the customer politely and respectfully
- Maintain a professional and helpful tone

User's question: {enhanced_query}
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
    language: str = "VietNam",
    session_id: str = "default",
    user_id: str = None
    ):
    """Create a tasker-specific prompt template for V1 with static tools section"""
    # Get current time for context
    vietnam_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vietnam_tz)
    current_time = now_vn.strftime("Today is %A, %Y-%m-%dT%H:%M:%S%z")

    lang_config = load_language_instructions(language)
    short_term_memory = load_short_term_memory(session_id)
    tasker_system_prompt = load_prompt(yaml_path)

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
    combined_system_prompt = f"""System Instructions: {tasker_system_prompt}\n {lang_config['system']}"""

    # Build prompt messages - only include memory context if it exists
    messages = [
        ("system", combined_system_prompt),
        ("human", f"\n---\nCurrent time: {current_time}\n---\n"),
        MessagesPlaceholder(variable_name="chat_history"),
    ]
    
    if rag_context_result and rag_context_result.strip() and rag_context_result != query:
        messages.append(("assistant", f"Knowledge Base Context:\n{rag_context_result}"))
        logger.info(f"📚 [Context Builder] RAG context added to prompt ({len(rag_context_result)} chars)")

    # Add memory context only if it exists
    if memory_context:
        messages.append(("assistant", f"Previous conversation context:\n{memory_context}"))

    # Add RAG context if available - as human message to avoid SystemMessage position issues

    messages.extend([
        ("human", "User Query: {input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    prompt = ChatPromptTemplate.from_messages(messages)

    return prompt


