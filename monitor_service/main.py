import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp

app = FastAPI(
    title="Monitor Service",
    description="System monitoring and health checking service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ServiceStatus(BaseModel):
    name: str
    url: str
    status: str
    response_time: float
    last_check: str

class SystemHealth(BaseModel):
    overall_status: str
    services: List[ServiceStatus]
    timestamp: str

# Service endpoints to monitor
SERVICES = {
    "ai-core": os.getenv("AI_CORE_URL", "http://ai-core:8000"),
    "mcp-server": os.getenv("MCP_SERVER_URL", "http://mcp-server:8001"),
    "database": os.getenv("DATABASE_URL", "http://database:8002"),
    "websocket": os.getenv("WEBSOCKET_URL", "http://websocket:8003"),
}

service_statuses: Dict[str, ServiceStatus] = {}

async def check_service_health(name: str, url: str) -> ServiceStatus:
    start_time = datetime.now()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = (datetime.now() - start_time).total_seconds()
                
                if response.status == 200:
                    status = "healthy"
                else:
                    status = "unhealthy"
                    
                return ServiceStatus(
                    name=name,
                    url=url,
                    status=status,
                    response_time=response_time,
                    last_check=datetime.now().isoformat()
                )
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        print(f"❌ Health check failed for {name}: {e}")
        
        return ServiceStatus(
            name=name,
            url=url,
            status="down",
            response_time=response_time,
            last_check=datetime.now().isoformat()
        )

async def monitor_services():
    while True:
        print("🔍 Checking service health...")
        
        for name, url in SERVICES.items():
            status = await check_service_health(name, url)
            service_statuses[name] = status
            
            if status.status != "healthy":
                print(f"⚠️ Service {name} is {status.status}")
            else:
                print(f"✅ Service {name} is healthy ({status.response_time:.2f}s)")
        
        await asyncio.sleep(30)  # Check every 30 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_services())

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "monitor",
        "monitored_services": len(SERVICES)
    }

@app.get("/system-health", response_model=SystemHealth)
async def get_system_health():
    services = list(service_statuses.values())
    
    # Determine overall status
    if not services:
        overall_status = "unknown"
    elif all(s.status == "healthy" for s in services):
        overall_status = "healthy"
    elif any(s.status == "down" for s in services):
        overall_status = "critical"
    else:
        overall_status = "degraded"
    
    return SystemHealth(
        overall_status=overall_status,
        services=services,
        timestamp=datetime.now().isoformat()
    )

@app.get("/services/{service_name}")
async def get_service_status(service_name: str):
    if service_name in service_statuses:
        return service_statuses[service_name]
    else:
        return {"error": "Service not found"}

@app.get("/logs")
async def get_logs():
    # Simple log aggregation - in production, use proper log aggregation
    logs = []
    
    for name, status in service_statuses.items():
        logs.append({
            "timestamp": status.last_check,
            "service": name,
            "level": "INFO" if status.status == "healthy" else "ERROR",
            "message": f"Service {name} is {status.status} (response time: {status.response_time:.2f}s)"
        })
    
    return {"logs": sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:100]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
