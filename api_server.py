from fastapi      import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from urllib.parse import urlparse, ParseResult
from pydantic     import BaseModel
from typing       import List, Optional, Union, Dict
from datetime     import datetime
from core         import Grok
from core.grok     import GrokAPIError
from uvicorn      import run


app = FastAPI()

class ConversationRequest(BaseModel):
    proxy: str
    message: str
    model: str = "grok-3-auto"
    extra_data: dict = None

class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str

class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[OpenAIModel]

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatChoice(BaseModel):
    index: int
    message: OpenAIChatMessage
    finish_reason: str

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChatChoice]
    usage: Optional[OpenAIUsage] = None

def format_proxy(proxy: str) -> str:

    if not proxy.startswith(("http://", "https://")):
        proxy: str = "http://" + proxy

    try:
        parsed: ParseResult = urlparse(proxy)

        if parsed.scheme not in ("http", ""):
            raise ValueError("Not http scheme")

        if not parsed.hostname or not parsed.port:
            raise ValueError("No url and port")

        if parsed.username and parsed.password:
            return f"http://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"

        else:
            return f"http://{parsed.hostname}:{parsed.port}"

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid proxy format: {str(e)}")

async def stream_response(grok_response: dict, model: str):
    """Helper function to stream Grok response in OpenAI format"""

    import json
    import asyncio

    response_content = grok_response.get("response", "")
    stream_tokens = grok_response.get("stream_response", [])

    response_id = f"chatcmpl-{int(datetime.now().timestamp())}"
    created = int(datetime.now().timestamp())

    if not response_content and not stream_tokens:
        # If no content, still send a completion
        chunk_data = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": ""
                    },
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Stream tokens if available, otherwise split the response content
    tokens_to_stream = stream_tokens if stream_tokens else response_content.split()

    for i, token in enumerate(tokens_to_stream):
        chunk_data = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": token + (" " if i < len(tokens_to_stream) - 1 else "")
                    },
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        # Small delay to simulate streaming
        await asyncio.sleep(0.01)

    # Send final chunk with finish_reason
    final_chunk_data = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield f"data: {json.dumps(final_chunk_data)}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/ask")
async def create_conversation(request: ConversationRequest):
    if not request.proxy or not request.message:
        raise HTTPException(status_code=400, detail="Proxy and message are required")

    proxy = format_proxy(request.proxy)

    try:
        answer: dict = Grok(request.model, proxy).start_convo(request.message, request.extra_data)

        return {
            "status": "success",
            **answer
        }
    except GrokAPIError as e:
        # Return the actual Grok error with proper structure for OpenAI clients
        error_data = e.to_dict()
        raise HTTPException(
            status_code=503,  # Service Unavailable is more appropriate for API limits
            detail={
                "error": error_data,
                "type": "grok_api_error"
            }
        )
    except GrokAPIError as e:
        # Return the actual Grok error with proper structure for OpenAI clients
        error_data = e.to_dict()
        raise HTTPException(
            status_code=503,  # Service Unavailable is more appropriate for API limits
            detail={
                "error": error_data,
                "type": "grok_api_error"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/models")
async def list_models():
    """OpenAI-compatible models endpoint"""
    try:
        models = [
            OpenAIModel(
                id="grok-3-auto",
                created=int(datetime.now().timestamp()),
                owned_by="xai"
            ),
            OpenAIModel(
                id="grok-3-fast",
                created=int(datetime.now().timestamp()),
                owned_by="xai"
            ),
            OpenAIModel(
                id="grok-4",
                created=int(datetime.now().timestamp()),
                owned_by="xai"
            ),
            OpenAIModel(
                id="grok-4-mini-thinking-tahoe",
                created=int(datetime.now().timestamp()),
                owned_by="xai"
            )
        ]
        return OpenAIModelsResponse(data=models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    proxy: Optional[str] = None

@app.post("/v1/chat/completions")
async def chat_completions_v1(request: OpenAIChatRequest, proxy_header: Optional[str] = Header(None, alias="proxy")):
    """OpenAI-compatible chat completions endpoint"""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    try:
        # Try to get proxy from multiple sources in order of preference:
        # 1. Request body (for backward compatibility)
        # 2. Request headers (for OpenAI client compatibility)
        # 3. Environment variable (for server configuration)
        # 4. Use internal proxy functionality if no proxy provided
        proxy_str = request.proxy or proxy_header

        if not proxy_str:
            # Check environment variable as fallback
            import os
            proxy_str = os.getenv("GROK_PROXY")

        # Format proxy if provided, otherwise pass None for internal handling
        proxy = format_proxy(proxy_str) if proxy_str else None

        # Get the last user message
        last_message = None
        for message in reversed(request.messages):
            if message.role == "user":
                last_message = message.content
                break

        if not last_message:
            raise HTTPException(status_code=400, detail="No user message found")

        grok_response = Grok(request.model, proxy).start_convo(last_message)

        if "response" not in grok_response or not grok_response.get("response"):
            raise HTTPException(status_code=500, detail="No response from Grok")

        # Handle streaming vs non-streaming
        if request.stream:
            return StreamingResponse(
                stream_response(grok_response, request.model),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )
        else:
            response = OpenAIChatResponse(
                id=f"chatcmpl-{int(datetime.now().timestamp())}",
                created=int(datetime.now().timestamp()),
                model=request.model,
                choices=[
                    OpenAIChatChoice(
                        index=0,
                        message=OpenAIChatMessage(
                            role="assistant",
                            content=grok_response["response"]
                        ),
                        finish_reason="stop"
                    )
                ]
            )

            return response

    except GrokAPIError as e:
        # Return the actual Grok error with proper structure for OpenAI clients
        error_data = e.to_dict()
        raise HTTPException(
            status_code=503,  # Service Unavailable is more appropriate for API limits
            detail={
                "error": error_data,
                "type": "grok_api_error"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat/completions")
async def chat_completions(request: OpenAIChatRequest, proxy_header: Optional[str] = Header(None, alias="proxy")):
    """OpenAI-compatible chat completions endpoint"""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    try:
        # Try to get proxy from multiple sources in order of preference:
        # 1. Request body (for backward compatibility)
        # 2. Request headers (for OpenAI client compatibility)
        # 3. Environment variable (for server configuration)
        # 4. Use internal proxy functionality if no proxy provided
        proxy_str = request.proxy or proxy_header

        if not proxy_str:
            # Check environment variable as fallback
            import os
            proxy_str = os.getenv("GROK_PROXY")

        # Format proxy if provided, otherwise pass None for internal handling
        proxy = format_proxy(proxy_str) if proxy_str else None

        # Get the last user message
        last_message = None
        for message in reversed(request.messages):
            if message.role == "user":
                last_message = message.content
                break

        if not last_message:
            raise HTTPException(status_code=400, detail="No user message found")

        grok_response = Grok(request.model, proxy).start_convo(last_message)

        if "response" not in grok_response or not grok_response.get("response"):
            raise HTTPException(status_code=500, detail="No response from Grok")

        # Handle streaming vs non-streaming
        if request.stream:
            return StreamingResponse(
                stream_response(grok_response, request.model),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )
        else:
            response = OpenAIChatResponse(
                id=f"chatcmpl-{int(datetime.now().timestamp())}",
                created=int(datetime.now().timestamp()),
                model=request.model,
                choices=[
                    OpenAIChatChoice(
                        index=0,
                        message=OpenAIChatMessage(
                            role="assistant",
                            content=grok_response["response"]
                        ),
                        finish_reason="stop"
                    )
                ]
            )

            return response

    except GrokAPIError as e:
        # Return the actual Grok error with proper structure for OpenAI clients
        error_data = e.to_dict()
        raise HTTPException(
            status_code=503,  # Service Unavailable is more appropriate for API limits
            detail={
                "error": error_data,
                "type": "grok_api_error"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    run("api_server:app", host="0.0.0.0", port=6969, workers=50)