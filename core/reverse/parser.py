from re        import findall, search
from json      import load, dump
from base64    import b64decode
from typing    import Optional
from curl_cffi import requests
from core      import Utils
from os        import path

class Parser:
    
    mapping: dict = {}
    _mapping_loaded: bool = False
    
    grok_mapping: list = []
    _grok_mapping_loaded: bool = False
    
    @classmethod
    def _load__xsid_mapping(cls):
        if not cls._mapping_loaded and path.exists('core/mappings/txid.json'):
            with open('core/mappings/txid.json', 'r') as f:
                cls.mapping = load(f)
            cls._mapping_loaded = True
            
    @classmethod
    def _load_grok_mapping(cls):
        if not cls._grok_mapping_loaded and path.exists('core/mappings/grok.json'):
            with open('core/mappings/grok.json', 'r') as f:
                cls.grok_mapping = load(f)
            cls._grok_mapping_loaded = True
    
    @staticmethod
    def parse_values(html: str, loading: str = "loading-x-anim-0", scriptId: str = "") -> tuple[str, Optional[str]]:

        Parser._load__xsid_mapping()
        
        all_d_values = findall(r'"d":"(M[^"]{200,})"', html)
        svg_data = all_d_values[int(loading.split("loading-x-anim-")[1])]
        
        if scriptId:
            
            if scriptId == "ondemand.s":
                script_link: str = 'https://abs.twimg.com/responsive-web/client-web/ondemand.s.' + Utils.between(html, f'"{scriptId}":"', '"') + 'a.js'
            else:
                script_link: str = f'https://grok.com/_next/{scriptId}'

            if script_link in Parser.mapping:
                numbers: list = Parser.mapping[script_link]
                
            else:
                script_content: str = requests.get(script_link, impersonate="chrome136").text
                numbers: list = [int(x) for x in findall(r'x\[(\d+)\]\s*,\s*16', script_content)]
                Parser.mapping[script_link] = numbers
                with open('core/mappings/txid.json', 'w') as f:
                    dump(Parser.mapping, f)

            return svg_data, numbers

        else:
            return svg_data

    
    @staticmethod
    def get_anim(html:  str, verification: str = "grok-site-verification") -> tuple[str, str]:
        
        verification_token: str = Utils.between(html, f'"name":"{verification}","content":"', '"')
        array: list = list(b64decode(verification_token))
        anim: str = "loading-x-anim-" + str(array[5] % 4)

        return verification_token, anim
    
    @staticmethod
    def parse_grok(scripts: list) -> tuple[list, str]:
        
        Parser._load_grok_mapping()
        
        for index in Parser.grok_mapping:
            if index.get("action_script") in scripts:
                return index["actions"], index["xsid_script"]
            
        for script in scripts:
            content: str = requests.get(f'https://grok.com{script}', impersonate="chrome136").text
            if "anonPrivateKey" in content:
                script_content1: str = content
                action_script: str = script
            elif "880932)" in content:
                script_content2: str = content

        actions: list = findall(r'createServerReference\)\("([a-f0-9]+)"', script_content1)
        xsid_script: str = search(r'"(static/chunks/[^"]+\.js)"[^}]*?\(880932\)', script_content2).group(1)
        
        if actions and xsid_script:
            Parser.grok_mapping.append({
                "xsid_script": xsid_script,
                "action_script": action_script,
                "actions": actions
            })
            
            with open('core/mappings/grok.json', 'w') as f:
                dump(Parser.grok_mapping, f, indent=2)
                
            return actions, xsid_script
        else:
            print("Something went wrong while parsing script and actions")
        
        