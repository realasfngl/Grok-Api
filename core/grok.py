from core      import Log, Run, Utils, Parser, Signature, Anon
from curl_cffi import requests, CurlMime
from bs4       import BeautifulSoup
from json      import dumps, loads
from uuid      import uuid4


class Grok:
    
    
    def __init__(self, proxy: str = None) -> None:
        self.session: requests.session.Session = requests.Session(impersonate="chrome136")
        self.session.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }
        self.c_run: int = 0
        self.keys: dict = Anon.generate_keys()
        if proxy:
            self.session.proxies = {
                "all": proxy
            }
    
    def _load(self, extra_data: dict = None) -> None:
        
        if not extra_data:
            load_site: requests.models.Response = self.session.get('https://grok.com/c')
            self.session.cookies.update(load_site.cookies)
            
            scripts: list = [s['src'] for s in BeautifulSoup(load_site.text, 'html.parser').find_all('script', src=True) if s['src'].startswith('/_next/static/chunks/')]

            self.actions, self.xsid_script = Parser.parse_grok(scripts)
            
            self.baggage: str = Utils.between(load_site.text, '<meta name="baggage" content="', '"')
            self.sentry_trace: str = Utils.between(load_site.text, '<meta name="sentry-trace" content="', '-')
        else:
            self.session.cookies.update(extra_data["cookies"])

            self.actions: list = extra_data["actions"]
            self.xsid_script: list =  extra_data["xsid_script"]
            self.baggage: str = extra_data["baggage"]
            self.sentry_trace: str = extra_data["sentry_trace"]
            
    
    def c_request(self, next_action: str) -> None:

        self.session.headers = {
            'accept': 'text/x-component',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'baggage': self.baggage,
            'cache-control': 'no-cache',
            'next-action': next_action,
            'next-router-state-tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22c%22%2C%7B%22children%22%3A%5B%5B%22slug%22%2C%22%22%2C%22oc%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
            'origin': 'https://grok.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://grok.com/c',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sentry-trace': f'{self.sentry_trace}-{str(uuid4()).replace("-", "")[:16]}-0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }
        
        if self.c_run == 0:
            mime = CurlMime()
            mime.addpart(name="1", data=bytes(self.keys["userPublicKey"]), filename="blob", content_type="application/octet-stream")
            mime.addpart(name="0", filename=None, data='[{"userPublicKey":"$o1"}]')
            
            c_request: requests.models.Response = self.session.post("https://grok.com/c", multipart=mime)
            self.session.cookies.update(c_request.cookies)
            
            self.anon_user: str = Utils.between(c_request.text, '{"anonUserId":"', '"')
            self.c_run += 1
            
        else:
            self.session.headers.update({
                'content-type': 'text/plain;charset=UTF-8'
            })
            
            match self.c_run:
                case 1:
                    data: str = dumps([{"anonUserId":self.anon_user}])
                case 2:
                    data: str = dumps([{"anonUserId":self.anon_user,**self.challenge_dict}])
            
            c_request: requests.models.Response = self.session.post('https://grok.com/c', data=data)
            self.session.cookies.update(c_request.cookies)

            match self.c_run:
                case 1:
                    start_idx = c_request.content.hex().find("3a6f38362c")
                    if start_idx != -1:
                        start_idx += len("3a6f38362c")
                        end_idx = c_request.content.hex().find("313a", start_idx)
                        if end_idx != -1:
                            challenge_hex = c_request.content.hex()[start_idx:end_idx]
                            challenge_bytes = bytes.fromhex(challenge_hex)

                    self.challenge_dict: dict = Anon.sign_challenge(challenge_bytes, self.keys["privateKey"])
                    Log.Success(f"Solved Challenge: {self.challenge_dict}")
                case 2:
                    self.verification_token, self.anim = Parser.get_anim(c_request.text, "grok-site-verification")
                    self.svg_data, self.numbers = Parser.parse_values(c_request.text, self.anim, self.xsid_script)
                    
            self.c_run += 1
        
    
    def start_convo(self, message: str, extra_data: str = None) -> dict:
        
        if not extra_data:
            self._load()
            self.c_request(self.actions[0])
            self.c_request(self.actions[1])
            self.c_request(self.actions[2])
            xsid: str = Signature.generate_sign('/rest/app-chat/conversations/new', 'POST', self.verification_token, self.svg_data, self.numbers)
        else:
            self._load(extra_data)
            self.c_run: int = 1
            self.anon_user: str = extra_data["anon_user"]
            self.keys["privateKey"] = extra_data["privateKey"]
            self.c_request(self.actions[1])
            self.c_request(self.actions[2])
            xsid: str = Signature.generate_sign(f'/rest/app-chat/conversations/{extra_data["conversationId"]}/responses', 'POST', self.verification_token, self.svg_data, self.numbers)

        self.session.headers = {
            'accept': '*/*',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'baggage': self.baggage,
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://grok.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://grok.com/c',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sentry-trace': f'{self.sentry_trace}-{str(uuid4()).replace("-", "")[:16]}-0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'x-statsig-id': xsid,
            'x-xai-request-id': str(uuid4()),
        }
        
        if not extra_data:
            conversation_data: dict = {
                'temporary': False,
                'modelName': 'grok-3',
                'message': message,
                'fileAttachments': [],
                'imageAttachments': [],
                'disableSearch': False,
                'enableImageGeneration': True,
                'returnImageBytes': False,
                'returnRawGrokInXaiRequest': False,
                'enableImageStreaming': True,
                'imageGenerationCount': 2,
                'forceConcise': False,
                'toolOverrides': {},
                'enableSideBySide': True,
                'sendFinalMetadata': True,
                'isReasoning': False,
                'webpageUrls': [],
                'disableTextFollowUps': False,
                'responseMetadata': {
                    'requestModelDetails': {
                        'modelId': 'grok-3',
                    },
                },
                'disableMemory': False,
                'forceSideBySide': False,
                'modelMode': 'MODEL_MODE_AUTO',
                'isAsyncChat': False,
            }
            
            convo_request: requests.models.Response = self.session.post('https://grok.com/rest/app-chat/conversations/new', json=conversation_data, timeout=9999)
            
            if "modelResponse" in convo_request.text:
                response = conversation_id = parent_response = None
                stream_response: list = []
                
                for response_dict in convo_request.text.strip().split('\n'):  
                    data: dict = loads(response_dict)

                    token: str = data.get('result', {}).get('response', {}).get('token')
                    if token:
                        stream_response.append(token)
                        
                    if not response and data.get('result', {}).get('response', {}).get('modelResponse', {}).get('message'):
                        response: str = data['result']['response']['modelResponse']['message']

                    if not conversation_id and data.get('result', {}).get('conversation', {}).get('conversationId'):
                        conversation_id: str = data['result']['conversation']['conversationId']

                    if not parent_response and data.get('result', {}).get('response', {}).get('modelResponse', {}).get('responseId'):
                        parent_response: str = data['result']['response']['modelResponse']['responseId']
                
                return {
                    "response": response,
                    "stream_response": stream_response,
                    "extra_data": {
                        "anon_user": self.anon_user,
                        "cookies": self.session.cookies.get_dict(),
                        "actions": self.actions,
                        "xsid_script": self.xsid_script,
                        "baggage": self.baggage,
                        "sentry_trace": self.sentry_trace,
                        "conversationId": conversation_id,
                        "parentResponseId": parent_response,
                        "privateKey": self.keys["privateKey"]
                    }
                }
            else:
                Log.Error("Something went wrong")
                Log.Error(convo_request.text)
                return {"error": convo_request.text}
        else:
            conversation_data: dict = {
                'message': message,
                'modelName': 'grok-3',
                'parentResponseId': extra_data["parentResponseId"],
                'disableSearch': False,
                'enableImageGeneration': True,
                'imageAttachments': [],
                'returnImageBytes': False,
                'returnRawGrokInXaiRequest': False,
                'fileAttachments': [],
                'enableImageStreaming': True,
                'imageGenerationCount': 2,
                'forceConcise': False,
                'toolOverrides': {},
                'enableSideBySide': True,
                'sendFinalMetadata': True,
                'customPersonality': '',
                'isReasoning': False,
                'webpageUrls': [],
                'metadata': {
                    'requestModelDetails': {
                        'modelId': 'grok-3',
                    },
                    'request_metadata': {
                        'model': 'grok-3',
                        'mode': 'auto',
                    },
                },
                'disableTextFollowUps': False,
                'disableArtifact': False,
                'isFromGrokFiles': False,
                'disableMemory': False,
                'forceSideBySide': False,
                'modelMode': 'MODEL_MODE_AUTO',
                'isAsyncChat': False,
                'skipCancelCurrentInflightRequests': False,
                'isRegenRequest': False,
            }

            convo_request: requests.models.Response = self.session.post(f'https://grok.com/rest/app-chat/conversations/{extra_data["conversationId"]}/responses', json=conversation_data, timeout=9999)

            if "modelResponse" in convo_request.text:
                
                response = conversation_id = parent_response = None
                stream_response: list = []
                
                for response_dict in convo_request.text.strip().split('\n'):
                    data: dict = loads(response_dict)

                    token: str = data.get('result', {}).get('token')
                    if token:
                        stream_response.append(token)
                        
                    if not response and data.get('result', {}).get('modelResponse', {}).get('message'):
                        response: str = data['result']['modelResponse']['message']

                    if not parent_response and data.get('result', {}).get('modelResponse', {}).get('responseId'):
                        parent_response: str = data['result']['modelResponse']['responseId']
                
                return {
                    "response": response,
                    "stream_response": stream_response,
                    "extra_data": {
                        "anon_user": self.anon_user,
                        "cookies": self.session.cookies.get_dict(),
                        "actions": self.actions,
                        "xsid_script": self.xsid_script,
                        "baggage": self.baggage,
                        "sentry_trace": self.sentry_trace,
                        "conversationId": extra_data["conversationId"],
                        "parentResponseId": parent_response,
                        "privateKey": self.keys["privateKey"]
                    }
                }
            else:
                Log.Error("Something went wrong")
                Log.Error(convo_request.text)
                return {"error": convo_request.text}
            

