import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse, ParseResult
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from core import Grok
from uvicorn import run

app = FastAPI(title="Grok API Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    expected_api_key = os.getenv("PROXY_API_KEY")
    if expected_api_key:
        if not credentials or credentials.credentials != expected_api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API Key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials.credentials
    return None

class ConversationRequest(BaseModel):
    proxy: Optional[str] = None
    cookie: Optional[Union[str, Dict[str, str]]] = None
    message: str
    model: str = "grok-3-fast"
    extra_data: Optional[Dict[str, Any]] = None

def format_proxy(proxy: str) -> str:
    if not proxy.startswith(("http://", "https://", "socks5://")):
        proxy = "http://" + proxy
    try:
        parsed: ParseResult = urlparse(proxy)
        if not parsed.hostname or not parsed.port:
            raise ValueError("No hostname or port")
        if parsed.username and parsed.password:
            return f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
        else:
            return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid proxy format: {str(e)}")

@app.get("/")
def index():
    return {"status": "running", "message": "Grok API Proxy is active and ready"}

@app.post("/ask")
async def create_conversation(request: ConversationRequest, auth: Optional[str] = Depends(verify_api_key)):
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    proxy = format_proxy(request.proxy) if request.proxy else None
    cookie = request.cookie or os.environ.get("GROK_COOKIE", None)
    
    try:
        answer: dict = Grok(model=request.model, proxy=proxy, cookie=cookie).start_convo(request.message, request.extra_data)
        return {
            "status": "success",
            **answer
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    run("api_server:app", host="0.0.0.0", port=6969)
