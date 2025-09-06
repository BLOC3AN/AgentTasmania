from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Dict, List
import os
import json
import sys
from utils.logger import Logger

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  
sys.path.insert(0, project_root)


logger = Logger(__name__)
logger.info(f"Current directory: {current_dir}")
logger.info(f"Project root: {project_root}")

app = FastAPI(
    title="MCP Research Tool Service",
    description="An API Gateway mimicking MCP for research purposes.",
    version="1.0.0"
)

# Add custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ Validation error: {exc.errors()}")
    logger.error(f"❌ Request body: {exc.body}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "success": False,
            "message": "Invalid request format. Please check your input.",
            "detail": exc.errors()
        }),
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

logger.info("✅ CORS middleware added to MCP server")

class ToolMetadata(BaseModel):
    mcp_schema:Dict

@app.get("/capabilities", 
         response_model=List[ToolMetadata],
         summary="Khám phá các khả năng (tools) có sẵn theo định dạng MCP.",
         dependencies=[])
async def get_capabilities():
    response_model = []
    schema_dir = os.path.join(current_dir,"schema")

    if os.path.exists(schema_dir):
        for file in os.listdir(schema_dir):
            if file.endswith(".json"):
                schema_path = os.path.join(schema_dir, file)
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                    logger.info(f"Loading schema: {schema.keys()}")
                    response_model.append(ToolMetadata(mcp_schema=schema))
    return response_model

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mcp-server",
        "version": "1.0.0"
    }

class TaskerKnowledgeRequest(BaseModel):
    query: str

@app.post("/tools/knowledges_base")
async def knowledge_base_tool(request: TaskerKnowledgeRequest):
    try:
        logger.info(f"🔍 [MCP] Knowledge base hybrid search query: {request.query}")

        # Call database service for hybrid search
        import requests
        import os
        from datetime import datetime

        database_service_url = os.getenv("DATABASE_URL", "http://vectordb:8002")

        try:
            # Perform hybrid search
            search_response = requests.post(
                f"{database_service_url}/hybrid-search",
                json={
                    "query_text": request.query,
                    "limit": 5,
                    "score_threshold": 0.5
                },
                timeout=15
            )

            if search_response.status_code == 200:
                search_result = search_response.json()
                search_type = search_result.get("search_type", "unknown")
                total_found = search_result.get("total_found", 0)

                # Extract content from search results
                documents = []
                for item in search_result.get("results", []):
                    if "payload" in item:
                        content = (item["payload"].get("content") or
                                 item["payload"].get("text") or
                                 item["payload"].get("document", ""))
                        if content:
                            documents.append({
                                "content": content,
                                "score": item.get("score", 0.0)
                            })

                # Format response
                if documents:
                    formatted_content = "\n\n".join([
                        f"[Score: {doc['score']:.3f}] {doc['content']}"
                        for doc in documents
                    ])
                    response_text = f"Tìm thấy {total_found} kết quả liên quan:\n\n{formatted_content}"
                else:
                    response_text = "Không tìm thấy thông tin liên quan đến câu hỏi của bạn."

                logger.info(f"✅ [MCP] Hybrid search ({search_type}) found {total_found} results")

                return {
                    "success": True,
                    "response": response_text,
                    "metadata": {
                        "query_length": len(request.query),
                        "search_type": search_type,
                        "total_found": total_found,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                logger.error(f"❌ [MCP] Database service error: {search_response.status_code}")
                return {
                    "success": False,
                    "response": "Không thể truy cập cơ sở dữ liệu. Vui lòng thử lại sau.",
                    "error": f"Database service returned {search_response.status_code}"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [MCP] Request error: {str(e)}")
            return {
                "success": False,
                "response": "Không thể kết nối đến dịch vụ tìm kiếm. Vui lòng thử lại sau.",
                "error": str(e)
            }

    except Exception as e:
        logger.error(f"❌ [MCP] Error processing knowledge base query: {e}")
        return {
            "success": False,
            "response": "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn.",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9099, reload=True)
