from typing import Any, Dict, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from src.utils.logger import Logger

logger = Logger(__name__)

class MCPTool(BaseTool):
    """Base class for MCP (Model Context Protocol) tools"""
    name: str = Field(description="Name of the tool") 
    description: str = Field(description="Description of what the tool does")
    mcp_server_url: str = Field(description="URL of the MCP server")
    tool_schema : Dict[str, Any] = Field(description="Schema definition for the tool")
    
    def __init__(self, name: str, description: str, mcp_server_url: str, args_schema : Dict[str, Any], **kwargs):
        super().__init__(
            name=name,
            description=description,
            mcp_server_url=mcp_server_url,
            tool_schema =args_schema ,
            **kwargs
        )
    
    def _run(self, tool_input: str, **kwargs) -> str:
        """Execute the MCP tool with given parameters"""
        try:
            # Parse tool_input if it's a JSON string
            if isinstance(tool_input, str):
                try:
                    import json
                    params = json.loads(tool_input)
                except json.JSONDecodeError:
                    # If not JSON, treat as simple string parameter
                    params = {"query": tool_input}
            else:
                params = tool_input if isinstance(tool_input, dict) else {"input": tool_input}

            # Merge with any additional kwargs
            params.update(kwargs)

            logger.info(f"✅ Executing MCP tool: {self.name} with params: {params}")

            # Make real HTTP request to MCP server
            import requests

            # Get endpoint from tool schema
            endpoint = getattr(self, 'endpoint', f"/tools/{self.name}")
            full_url = f"{self.mcp_server_url}{endpoint}"

            logger.info(f"🔗 [MCP] Calling: {full_url}")

            response = requests.post(
                full_url,
                json=params,
                headers={"Content-Type": "application/json"},
                timeout=20
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ [MCP] Tool {self.name} executed successfully")

                # Return the response content
                if isinstance(result, dict):
                    return result.get("response", str(result))
                else:
                    return str(result)
            else:
                logger.error(f"❌ [MCP] Tool {self.name} failed with status {response.status_code}")
                return f"Error: MCP tool returned status {response.status_code}"

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [MCP] Network error executing tool {self.name}: {e}")
            return f"Network error executing tool: {str(e)}"
        except Exception as e:
            logger.error(f"❌ [MCP] Error executing MCP tool {self.name}: {e}")
            return f"Error executing tool: {str(e)}"
    
    async def _arun(self, tool_input: str, **kwargs) -> str:
        """Async version of _run"""
        return self._run(tool_input, **kwargs)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about this tool"""
        return {
            "name": self.name,
            "description": self.description,
            "mcp_server_url": self.mcp_server_url,
            "schema": self.tool_schema
        }
