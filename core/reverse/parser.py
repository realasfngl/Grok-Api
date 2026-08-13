from re import findall, search
from json import loads, dumps
from base64 import b64decode
from typing import Optional, Tuple, List
from curl_cffi import requests
from core import Utils

class Parser:
    
    @staticmethod
    def parse_values_from_rsc(rsc_text: str, anim: int = 0) -> str:
        m = search(r'curves\\?":(\[\[.*?\]\])', rsc_text)
        if not m:
            m = search(r'curves\\\\?":(\[\[.*?\]\])', rsc_text)
        if m:
            curves_raw = m.group(1).replace('\\"', '"').replace('\\\\"', '"')
            d_values = loads(curves_raw)[anim]
            svg_data = "M 10,30 C" + " C".join(
                f" {item['color'][0]},{item['color'][1]} {item['color'][2]},{item['color'][3]} {item['color'][4]},{item['color'][5]}"
                f" h {item['deg']}"
                f" s {item['bezier'][0]},{item['bezier'][1]} {item['bezier'][2]},{item['bezier'][3]}"
                for item in d_values
            )
            return svg_data
        raise ValueError("Could not parse curves from RSC response")
    
    @staticmethod
    def get_anim(html: str) -> tuple[str, int]:
        m_ver = search(r'grok-site[^\"]*verification["\s]+content="([^"]+)"', html)
        if not m_ver:
            m_ver = search(r'content="([^"]+)"[^>]*name="grok-site[^\"]*verification"', html)
        if not m_ver:
            m_ver = search(r'"name":"grok-site[^\"]*verification","content":"([^"]+)"', html)
        if not m_ver:
            m_ver = search(r'verification\\\\?",\\\\?"content\\\\?":\\\\?"([^"]+)\\\\?"', html)
            
        if m_ver:
            verification_token = m_ver.group(1).replace('\\\\', '')
            array = list(b64decode(verification_token))
            anim = int(array[5] % 4)
            return verification_token, anim
        raise ValueError("Could not parse verification token")
    
    @staticmethod
    def parse_grok(scripts: list, session: requests.Session) -> tuple[list, list]:
        actions = []
        for script in scripts:
            url = script if script.startswith('http') else f'https://grok.com{script}'
            try:
                content = session.get(url).text
            except Exception:
                continue
            if "createAnonUser" in content:
                m0 = search(r'createServerReference\)\("([a-f0-9]+)"[^\)]*"createAnonUser"\)', content)
                m1 = search(r'createServerReference\)\("([a-f0-9]+)"[^\)]*"createChallenge"\)', content)
                m2 = search(r'createServerReference\)\("([a-f0-9]+)"[^\)]*"setAnonCookies"\)', content)
                if m0 and m1 and m2:
                    actions = [m0.group(1), m1.group(1), m2.group(1)]
                    break
        
        numbers = [22, 15, 3, 43]
        return actions, numbers
