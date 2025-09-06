from typing import List
from langchain_core.tools import BaseTool
import requests
from .mcp_base_tool import MCPTool
from src.utils.logger import Logger

logger = Logger(__name__)

def discover_and_create_mcp_tools(mcp_server_url: str, token: str = "", user_id: str = "") -> List[BaseTool]:
    """
    Khám phá các tools từ MCP Service và tạo các đối tượng BaseTool của LangChain.
    Optimize và reuse từ implementation cũ với better error handling.
    """
    headers = {"Content-Type": "application/json"}
    capabilities_url = f"{mcp_server_url}/capabilities"

    try:
        logger.info(f"🔍 Discovering MCP capabilities from: {capabilities_url}")
        response = requests.get(capabilities_url, headers=headers, timeout=10)
        response.raise_for_status()
        capabilities = response.json()
        
        logger.info(f"Capabilities MCP discovered: {[cap['mcp_schema'].get('name', 'unknown') for cap in capabilities]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error discovering MCP capabilities: {e}")
        return []

    langchain_tools = []
    for capability in capabilities:
        try:
            schema = capability['mcp_schema']
            
            name = schema.get("name")
            description = schema.get("description")
            
            # Validate schema structure
            if "endpoint" not in schema or "url" not in schema["endpoint"]:
                logger.error(f"❌ Missing endpoint or url in schema for {name}")
                continue
                
            endpoint = schema["endpoint"]["url"]
            
            # Get args_schema with fallback
            args_schema = schema.get("args_schema", {
                "type": "object",
                "properties": {}
            })
            
            mcp_tool_instance = MCPTool(
                name=name,
                description=description,
                mcp_server_url=mcp_server_url,
                args_schema=args_schema,
                endpoint=endpoint, 
                token=token,        
                user_id=user_id     
            )
            langchain_tools.append(mcp_tool_instance)
            
        except KeyError as ke:
            logger.error(f"❌ Missing required key in capability schema: {ke}")
            continue
        except Exception as e:
            logger.error(f"❌ Error creating tool from capability: {e}")
            continue

    logger.info(f"🎯 Successfully discovered {len(langchain_tools)} tools from MCP Service")
    return langchain_tools
