from core import Log, Signature, Anon, Headers, Parser
from curl_cffi import requests, CurlMime
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from json import dumps, loads
from secrets import token_hex
from uuid import uuid4
from base64 import b64decode
from typing import Optional, Dict, Any, Union
import re

@dataclass
class Models:
    models: dict[str, str] = field(default_factory=lambda: {
        "grok-3-fast": "fast",
        "grok-3-auto": "auto",
        "grok-3": "fast",
        "grok-4": "expert",
        "grok-4-mini-thinking-tahoe": "grok-4-mini-thinking"
    })

    def get_mode(self, model: str) -> str:
        return self.models.get(model, "fast")

_Models = Models()

class Grok:
    def __init__(self, model: str = "grok-3-fast", proxy: Optional[str] = None, cookie: Optional[Union[str, dict]] = None) -> None:
        self.session = requests.Session(impersonate="chrome136", default_headers=False)
        self.headers = Headers()
        self.model = model
        self.mode_id = _Models.get_mode(model)
        self.numbers: Optional[list[int]] = None
        self.cookie = cookie
        
        if proxy:
            self.session.proxies = {"all": proxy}
            
        if cookie:
            if isinstance(cookie, str):
                for item in cookie.split(';'):
                    if '=' in item:
                        k, v = item.strip().split('=', 1)
                        self.session.cookies.set(k.strip(), v.strip())
            elif isinstance(cookie, dict):
                for k, v in cookie.items():
                    self.session.cookies.set(k.strip(), str(v).strip())

    def _get_page_verification(self, refresh_numbers: bool = False) -> tuple[str, str]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        }
        res = self.session.get('https://grok.com/c', headers=headers)
        self.session.cookies.update(res.cookies)
        
        m_ver = re.search(r'grok-site[^\"]*verification["\s]+content="([^"]+)"', res.text)
        if not m_ver:
            m_ver = re.search(r'content="([^"]+)"[^>]*name="grok-site[^\"]*verification"', res.text)
        if not m_ver:
            m_ver = re.search(r'"name":"grok-site[^\"]*verification","content":"([^"]+)"', res.text)
        if not m_ver:
            m_ver = re.search(r'verification\\\\?",\\\\?"content\\\\?":\\\\?"([^"]+)\\\\?"', res.text)
            
        m_curves = re.search(r'curves\\?":(\[\[.*?\]\])', res.text)
        if not m_curves:
            m_curves = re.search(r'curves\\\\?":(\[\[.*?\]\])', res.text)
            
        if not m_ver or not m_curves:
            raise ValueError(f"Could not parse verification token or curves from Grok page (status {res.status_code})")
            
        verification_token = m_ver.group(1).replace('\\\\', '')
        curves_raw = m_curves.group(1).replace('\\"', '"').replace('\\\\"', '"')
        curves_data = loads(curves_raw)
        anim = int(list(b64decode(verification_token))[5] % 4)
        d_values = curves_data[anim]
        
        svg_data = "M 10,30 C" + " C".join(
            f" {item['color'][0]},{item['color'][1]} {item['color'][2]},{item['color'][3]} {item['color'][4]},{item['color'][5]}"
            f" h {item['deg']}"
            f" s {item['bezier'][0]},{item['bezier'][1]} {item['bezier'][2]},{item['bezier'][3]}"
            for item in d_values
        )

        self.numbers = Parser.get_signature_numbers(self.session, res.text, refresh=refresh_numbers)
        return verification_token, svg_data

    def start_convo(self, message: str, extra_data: Optional[Dict[str, Any]] = None, _retry: bool = True) -> dict:
        if extra_data and isinstance(extra_data, dict) and "cookies" in extra_data:
            self.session.cookies.update(extra_data["cookies"])

        verification_token, svg_data = self._get_page_verification()
        
        baggage = "sentry-environment=production,sentry-public_key=b3111d39fed54ab19985a10525251d82,sentry-trace_id=" + str(uuid4()).replace("-", "")
        sentry_trace = str(uuid4()).replace("-", "")
        
        if not extra_data or "conversationId" not in extra_data:
            path = '/rest/app-chat/conversations/new'
            xsid = Signature.generate_sign(path, 'POST', verification_token, svg_data, self.numbers)
            
            chat_headers = {
                'accept': '*/*',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'baggage': baggage,
                'content-type': 'application/json',
                'origin': 'https://grok.com',
                'referer': 'https://grok.com/c',
                'sentry-trace': f'{sentry_trace}-{str(uuid4()).replace("-", "")[:16]}-0',
                'traceparent': f"00-{token_hex(16)}-{token_hex(8)}-00",
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'x-statsig-id': xsid,
                'x-xai-request-id': str(uuid4())
            }
            
            payload = {
                "temporary": False,
                "modeId": self.mode_id,
                "message": message,
                "fileAttachments": [],
                "imageAttachments": [],
                "disableSearch": False,
                "enableImageGeneration": True,
                "returnImageBytes": False,
                "returnRawGrokInXaiRequest": False,
                "enableImageStreaming": True,
                "imageGenerationCount": 2,
                "forceConcise": False,
                "toolOverrides": {},
                "enableSideBySide": True,
                "sendFinalMetadata": True,
                "isReasoning": False,
                "webpageUrls": [],
                "disableTextFollowUps": False,
                "disableMemory": False,
                "isAsyncChat": False,
            }
            
            resp = self.session.post('https://grok.com/rest/app-chat/conversations/new', json=payload, headers=chat_headers)
            
            if resp.status_code == 200:
                conversation_id = None
                parent_model_resp_id = None
                stream_tokens = []
                full_message = ""
                
                for line in resp.text.strip().split('\n'):
                    try:
                        data = loads(line)
                        res_obj = data.get('result', {})
                        if not res_obj:
                            continue
                        
                        if not conversation_id and res_obj.get('conversation', {}).get('conversationId'):
                            conversation_id = res_obj['conversation']['conversationId']
                            
                        resp_item = res_obj.get('response', res_obj)
                        mr_id = resp_item.get('modelResponse', {}).get('responseId') or res_obj.get('responseId')
                        if mr_id:
                            parent_model_resp_id = mr_id
                            
                        t = resp_item.get('token')
                        if t:
                            stream_tokens.append(t)
                            full_message += t
                            
                        msg = resp_item.get('modelResponse', {}).get('message')
                        if msg:
                            full_message = msg
                    except Exception:
                        pass
                
                return {
                    "response": full_message,
                    "stream_response": stream_tokens,
                    "images": None,
                    "extra_data": {
                        "conversationId": conversation_id,
                        "parentResponseId": parent_model_resp_id,
                        "cookies": self.session.cookies.get_dict(),
                    }
                }
            else:
                res_json = resp.json() if resp.text.startswith('{') else {"error": resp.text}
                if _retry and isinstance(res_json, dict) and res_json.get("error", {}).get("code") == 7:
                    self._get_page_verification(refresh_numbers=True)
                    return self.start_convo(message, extra_data=extra_data, _retry=False)
                return res_json
        else:
            conv_id = extra_data["conversationId"]
            parent_id = extra_data.get("parentResponseId")
            path = f'/rest/app-chat/conversations/{conv_id}/responses'
            xsid = Signature.generate_sign(path, 'POST', verification_token, svg_data, self.numbers)
            
            chat_headers = {
                'accept': '*/*',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'baggage': baggage,
                'content-type': 'application/json',
                'origin': 'https://grok.com',
                'referer': f'https://grok.com/c/{conv_id}',
                'sentry-trace': f'{sentry_trace}-{str(uuid4()).replace("-", "")[:16]}-0',
                'traceparent': f"00-{token_hex(16)}-{token_hex(8)}-00",
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'x-statsig-id': xsid,
                'x-xai-request-id': str(uuid4())
            }
            
            payload = {
                "message": message,
                "modeId": self.mode_id,
                "parentResponseId": parent_id,
                "disableSearch": False,
                "enableImageGeneration": True,
                "imageAttachments": [],
                "returnImageBytes": False,
                "returnRawGrokInXaiRequest": False,
                "fileAttachments": [],
                "enableImageStreaming": True,
                "imageGenerationCount": 2,
                "forceConcise": False,
                "toolOverrides": {},
                "enableSideBySide": True,
                "sendFinalMetadata": True,
                "isReasoning": False,
                "webpageUrls": [],
                "disableTextFollowUps": False,
                "disableArtifact": False,
                "isFromGrokFiles": False,
                "disableMemory": False,
                "isAsyncChat": False,
            }
            
            resp = self.session.post(f'https://grok.com{path}', json=payload, headers=chat_headers)
            
            if resp.status_code == 200:
                parent_model_resp_id = None
                stream_tokens = []
                full_message = ""
                
                for line in resp.text.strip().split('\n'):
                    try:
                        data = loads(line)
                        res_obj = data.get('result', {})
                        if not res_obj:
                            continue
                            
                        resp_item = res_obj.get('response', res_obj)
                        mr_id = resp_item.get('modelResponse', {}).get('responseId') or res_obj.get('responseId')
                        if mr_id:
                            parent_model_resp_id = mr_id
                            
                        t = resp_item.get('token')
                        if t:
                            stream_tokens.append(t)
                            full_message += t
                            
                        msg = resp_item.get('modelResponse', {}).get('message')
                        if msg:
                            full_message = msg
                    except Exception:
                        pass
                
                return {
                    "response": full_message,
                    "stream_response": stream_tokens,
                    "images": None,
                    "extra_data": {
                        "conversationId": conv_id,
                        "parentResponseId": parent_model_resp_id,
                        "cookies": self.session.cookies.get_dict(),
                    }
                }
            else:
                res_json = resp.json() if resp.text.startswith('{') else {"error": resp.text}
                if _retry and isinstance(res_json, dict) and res_json.get("error", {}).get("code") == 7:
                    self._get_page_verification(refresh_numbers=True)
                    return self.start_convo(message, extra_data=extra_data, _retry=False)
                return res_json
