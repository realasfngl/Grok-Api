# Grok-Api

A free Grok API wrapper that allows you to use Grok without API access or account authentication.

## Overview

This project provides a Python-based API wrapper for Grok AI, enabling you to interact with Grok's conversational AI without requiring official API access or account credentials. It includes both a direct Python interface and a FastAPI server for easy integration into your applications.

## Features

- 🔓 **No Authentication Required** - Access Grok without an account
- 🆓 **Completely Free** - No API keys or paid subscriptions needed
- 🚀 **FastAPI Server** - Ready-to-use REST API endpoint
- 🌐 **Proxy Support** - Full support for HTTP proxies
- 📡 **Streaming Responses** - Receive both complete responses and token-by-token streams
- ⚡ **High Performance** - Multi-worker support for concurrent requests

## Installation

```bash
git clone https://github.com/realasfngl/Grok-Api.git
cd Grok-Api
pip install -r requirements.txt
```

### Requirements

- Python 3.10+
- curl_cffi
- fastapi
- uvicorn
- coincurve
- beautifulsoup4
- pydantic
- colorama

## Usage

### Models:

| Model | Mode | Description |
|-------|------|-------------|
| `grok-3-auto` | auto | Automatic mode |
| `grok-3-fast` | fast | Fast processing mode |
| `grok-4` | expert | Expert mode |
| `grok-4-mini-thinking-tahoe` | grok-4-mini-thinking | Mini thinking mode |

### Manual Usage (Python)

**New conversation:**
```python
from core import Grok

response = Grok("grok-3-fast").start_convo("Hello, how are you today?")
print(response)

proxy = "http://username:password@ip:port"
response = Grok("grok-3-fast", proxy).start_convo("Tell me a joke")
print(response)
```

**Continue conversation:**
```python
from core import Grok

response = Grok().start_convo("Hello, how are you today?")
print(response)

response2 = Grok().start_convo("That's nice! Glad to hear!", extra_data=response["extra_data"])
print(response2)
```
**Example Output:**
```python
{
    "response": "Yo, I'm just chilling in the digital realm...",
    "stream_response": ["Yo", ",", " I'm", " just", " chilling", "..."],
    "images": None,
    "extra_data": {"..."}
}
```

### API Server

#### Starting the Server

**Simple start:**
```bash
python api_server.py
```

**Production start with custom configuration:**
```bash
uvicorn api_server:app --host 0.0.0.0 --port 6969 --workers 50
```

#### Making API Requests

**New conversation:**
```python
import requests

response = requests.post(
    "http://localhost:6969/ask",
    json={
        "proxy": "http://user:pass@ip:port",
        "message": "Hello, Grok!",
        "model": "grok-3-fast",
        "extra_data": None
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
        "proxy": "http://user:pass@ip:port",
        "message": "Hello!",
        "model": "grok-3-fast",
        "extra_data": None
    }
)
data1 = response1.json()
print(data1)

response2 = requests.post(
    "http://localhost:6969/ask",
    json={
        "proxy": "http://user:pass@ip:port",
        "message": "Tell me more",
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
  "extra_data": {"..."}
}
```

## Configuration

### Proxy Format

The wrapper accepts proxies in the following formats:
- `http://ip:port`
- `http://username:password@ip:port`
- `ip:port` (automatically prefixed with `http://`)

### API Server Settings

Modify `api_server.py` to change:
- **Host**: Default `0.0.0.0` (all interfaces)
- **Port**: Default `6969`
- **Workers**: Default `50` (adjust based on your server capacity)

## Troubleshooting

**Common Issues:**

1. **IP Flag** - `{"error":{"code":7,"message":"Request rejected by anti-bot rules.","details":[]}}` - This indicates your IP or proxy has been flagged. Try using a different proxy or IP address.

## Support

If you find this project helpful, consider starring the repository!

---

**Note:** This project may break if Grok updates their web interface. Please report any issues if the wrapper stops working.

**Contact:** This project is for educational purposes only. If Grok has an Issue with this Project please contact me via my email nuhuh3116@gmail.com.
