from re import findall, finditer, search
from json import loads, dumps
from base64 import b64decode
from typing import Optional, Tuple, List
from curl_cffi import requests
from bs4 import BeautifulSoup
from core import Utils

class Parser:
    _cached_numbers: Optional[List[int]] = None
    
    @classmethod
    def get_signature_numbers(cls, session: requests.Session, html: str, refresh: bool = False) -> List[int]:
        if cls._cached_numbers and not refresh:
            return cls._cached_numbers
        
        soup = BeautifulSoup(html, "html.parser")
        scripts = [s["src"] for s in soup.find_all("script", src=True) if s.get("src")]
        
        module_id = None
        all_chunks = {}
        
        for sc in scripts:
            url = sc if sc.startswith("http") else f"https://grok.com{sc}"
            try:
                txt = session.get(url).text
                if "x-statsig-id" in txt and not module_id:
                    m_mod = search(r"await\s+\w+\.A\((\d+)\)", txt)
                    if m_mod:
                        module_id = m_mod.group(1)
                
                for m in finditer(r"(\d+),s=>\{s\.v\(t=>Promise\.all\(\[\"static/chunks/([a-zA-Z0-9_\-]+)\.js\"\]", txt):
                    all_chunks[m.group(1)] = m.group(2)
            except Exception:
                continue
                
        chunk_name = all_chunks.get(module_id)
        if chunk_name:
            sig_url = f"https://cdn.grok.com/_next/static/chunks/{chunk_name}.js"
            sig_txt = session.get(sig_url).text
            
            m_nums = findall(r"W\[(\d+)\],\s*16", sig_txt)
            if len(m_nums) >= 4:
                cls._cached_numbers = [int(x) for x in m_nums[:4]]
                return cls._cached_numbers
                
            m_all = findall(r"W\[(\d+)\]", sig_txt)
            sig_indices = [int(x) for x in m_all if int(x) not in range(7)]
            if len(sig_indices) >= 3:
                cls._cached_numbers = [sig_indices[0], sig_indices[1], sig_indices[2], 4]
                return cls._cached_numbers
                
        raise ValueError("Could not dynamically parse signature numbers from Grok scripts")

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
        
        return actions
