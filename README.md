# Grok-Api

A Grok API wrapper that allows you to interact with Grok AI via Python or a FastAPI REST server.

## Overview

This project provides a Python-based API wrapper for Grok AI. It includes both a direct Python interface and a FastAPI server for easy integration into your applications.

## Features

- 🚀 **FastAPI Server** - Ready-to-use REST API endpoint
- 🔑 **SSO Cookie Support** - Authenticate with your free Grok account cookie (`sso`)
- 🌐 **Proxy Support** - Support for HTTP/HTTPS/SOCKS5 proxies
- 📡 **Streaming Responses** - Receive both complete responses and token-by-token streams
- ⚡ **Turbopack & Statsig Compatible** - Updated reverse-engineered signature & challenge handling
- 🐳 **Docker Support** - Easily deploy via Docker

## Installation

```bash
git clone https://github.com/Kirillka999/Grok-Api.git
cd Grok-Api
pip install -r requirements.txt
```

### Requirements

- Python 3.10+
- `curl_cffi`
- `fastapi`
- `uvicorn`
- `coincurve`
- `beautifulsoup4`
- `pydantic`
- `colorama`

## Usage

### Manual Usage (Python)

```python
from core import Grok

# Optional: pass your sso cookie and/or proxy
cookie = "sso=eyJ..."  # or export GROK_COOKIE="sso=..."
proxy = "http://username:password@ip:port"  # optional

grok = Grok(model="grok-3-fast", proxy=proxy, cookie=cookie)

# Start new conversation
response = grok.start_convo("Hello, how are you today?")
print(response["response"])

# Continue conversation
response2 = grok.start_convo("Tell me a joke", extra_data=response["extra_data"])
print(response2["response"])
```

### API Server

#### Starting the Server

```bash
python api_server.py
# Or with uvicorn:
uvicorn api_server:app --host 0.0.0.0 --port 6969
```

#### Docker

```bash
docker build -t grok-api .
docker run -p 6969:6969 -e PROXY_API_KEY=your_key grok-api
```

#### Making API Requests

**New conversation:**
```python
import requests

response = requests.post(
    "http://localhost:6969/ask",
    headers={"Authorization": "Bearer your_key"}, # optional if PROXY_API_KEY is set
    json={
        "cookie": "sso=eyJ...",  # optional if set via GROK_COOKIE
        "proxy": "http://user:pass@ip:port",  # optional
        "message": "Hello, Grok!",
        "model": "grok-3-fast"
    }
)
print(response.json())
```

**Continue conversation:**
```python
import requests

response1 = requests.post(
    "http://localhost:6969/ask",
    json={
        "cookie": "sso=eyJ...",
        "message": "Remember the number 42",
        "model": "grok-3-fast"
    }
)
data1 = response1.json()

response2 = requests.post(
    "http://localhost:6969/ask",
    json={
        "cookie": "sso=eyJ...",
        "message": "What was the number?",
        "model": "grok-3-fast",
        "extra_data": data1["extra_data"]
    }
)
print(response2.json())
```

### API Response Format

```json
{
  "status": "success",
  "response": "Complete response message from Grok",
  "stream_response": ["Token", "by", "token", "response", "array"],
  "images": null,
  "extra_data": {
    "conversationId": "...",
    "parentResponseId": "..."
  }
}
```
