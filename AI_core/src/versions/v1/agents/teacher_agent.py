from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from langchain.agents import AgentExecutor, create_tool_calling_agent
from src.memory.conversation.redisMemory import RedisConversationMemory,RedisBackedMemory
from src.mcp_client.mcp_discovery import discover_and_create_mcp_tools
from src.versions.v1.prompts.context_builder import build_context_v1
from src.utils.logger import Logger
import time

logger = Logger(__name__)

# Load tasker prompt from YAML
current_dir = os.path.dirname(__file__)
yaml_path = os.path.join(current_dir, "../", "prompts", "conversation", "conversation.md")

class TaskerAgent:
    """
    Conversational Tasker Agent sử dụng AgentConversation với tasker knowledge tools
    """
    def __init__(
        self,
        llm_model: str = "gemini-2.0-flash",
        token: str = "",
        user_id: str = ""
        ):
        self.llm_model = llm_model
        self.token = token
        self.user_id = user_id

        # Initialize Gemini LLM directly
        from src.llms.gemini import LLMGemini
        self.llm_model_instance = LLMGemini(llm_model)

        self.tools = []
        self._setup_mcp_tools()

        # Agent configuration
        self.MAX_ITERATIONS = 5
        self.EARLY_STOPPING_METHOD = "force"
        self.MAX_EXECUTION_TIME = 10
        self.HANDLE_PARSING_ERRORS = True
        self.RETURN_INTERMEDIATE_STEPS = True
        self.VERBOSE = True

    def _setup_mcp_tools(self):
        """Setup tasker tools for the agent using enhanced tasker knowledge"""
        try:
            # Try to setup MCP tools if available
            mcp_server_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:9099")
            mcp_tools = discover_and_create_mcp_tools(
                mcp_server_url=mcp_server_url,
                token=self.token,
                user_id=self.user_id
            )
            mcp_tools_available = [
                tool for tool in mcp_tools
                if tool.name in ["knowledges_base"]
            ]
            if mcp_tools_available:
                self.tools.extend(mcp_tools_available)
                logger.info(f"MCP Tasker tools added to TaskerAgent: {[tool.name for tool in mcp_tools_available]}")
            else:
                logger.warning("No MCP tasker tools found - using local tasker knowledge tool only")

        except Exception as e:
            logger.error(f"❌ Error setting up tasker knowledge tool for conversational agent: {str(e)}")
            self.tasker_knowledge_instance = None

    def run(self, user_query: str, session_id: str) -> dict:
        """
        Run tasker conversation using V1 custom prompt and agent
        """
        start_time = time.time()
        prompt = build_context_v1(yaml_path, user_query, self.user_id)
        try:
            memory_class = RedisConversationMemory(session_id=session_id)
            
            memory = RedisBackedMemory(
                session_id=session_id,
                redis_client=memory_class.redis_client,
                memory_key="chat_history",
                return_messages=True
            )

            logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
            
            before_invoke = time.time()
            logger.info(f"⏱️ Time to create agent: {before_invoke - start_time:.4f} seconds")

            logger.info(f"\nPROMTP: \n{prompt}\n")
            agent = create_tool_calling_agent(self.llm_model_instance.llm, self.tools,prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=self.VERBOSE,
                max_iterations=self.MAX_ITERATIONS,
                early_stopping_method=self.EARLY_STOPPING_METHOD,
                max_execution_time=self.MAX_EXECUTION_TIME,
                handle_parsing_errors=self.HANDLE_PARSING_ERRORS,
                return_intermediate_steps=self.RETURN_INTERMEDIATE_STEPS,
            )
            chat_history = memory.chat_memory.messages if hasattr(memory, 'chat_memory') else []
            result = agent_executor.invoke({
                "input": user_query,
                "chat_history": chat_history
            })

            # Save conversation to Redis memory
            try:
                memory.save_context(
                    {"input": user_query},
                    {"output": result.get("output", "")}
                )
            except Exception as e:
                logger.error(f"Error saving conversation to Redis: {str(e)}")

            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            logger.info(f"⏱️ Total execution time: {response_time_ms}ms")
            logger.info(f"💬 Agent response: {result}")
            # Log intermediate steps
            if result.get('intermediate_steps'):
                with open("intermediate_steps.txt", "a") as f:
                    f.write('\n\n' + str(result['intermediate_steps']))

            return {
                "success": True,
                "llmOutput": result.get("output", "Xin lỗi, không có phản hồi từ hệ thống."),
                "model": self.llm_model,
                "response_time_ms": response_time_ms
            }

        except Exception as e:
            logger.error(f"❌ Error in tasker conversation V1: {str(e)}")
            return {
                "success": False,
                "llmOutput": f"Xin lỗi, tôi gặp lỗi khi xử lý yêu cầu: {str(e)}",
                "error": str(e)
            }


