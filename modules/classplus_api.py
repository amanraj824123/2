"""
✅ Classplus API Handler - Proper Signed Requests
Replaces Golden Eagle API with direct signed Classplus API calls
"""

import hmac
import hashlib
import time
import requests
import json
from typing import Optional, Dict, Tuple

class ClassplusSignedAPI:
    """Handle Classplus API requests with proper HMAC-SHA256 signing"""
    
    def __init__(self, api_key: str = "", secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.classplusapp.com"
        self.headers = {
            "User-Agent": "Mobile-Android",
            "App-Version": "1.12.1.1",
            "Api-Version": "56",
            "Device-Id": "9d8ce7affa2f5032",
            "Device-Details": "motorola_Moto G4_SDK-32",
            "region": "IN",
            "accept-language": "en",
            "Content-Type": "application/json",
            "Build-Number": "56",
            "Connection": "Keep-Alive",
        }
    
    def _generate_signature(self, timestamp: str, method: str, endpoint: str, data: Optional[Dict] = None) -> str:
        """Generate HMAC-SHA256 signature for Classplus"""
        message = f"{method}{endpoint}{timestamp}"
        if data:
            message += json.dumps(data, separators=(',', ':'), sort_keys=True)
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def get_signed_video_url(self, content_id: str, token: str) -> Optional[Dict]:
        """
        Get signed video URL from Classplus API (Direct - No Golden Eagle)
        
        Args:
            content_id: Video content ID
            token: User's Classplus token (x-access-token)
            
        Returns:
            Dict with 'url', 'drm_url', 'keys' or None if failed
        """
        try:
            timestamp = str(int(time.time()))
            endpoint = "/cams/uploader/video/jw-signed-url"
            
            headers = self.headers.copy()
            headers["x-access-token"] = token
            
            params = {
                "contentId": content_id,
                "offlineDownload": "false"
            }
            
            # Signature for GET request
            signature = self._generate_signature(timestamp, "GET", endpoint, params)
            headers["x-signature"] = signature
            headers["x-timestamp"] = timestamp
            
            url = f"{self.base_url}{endpoint}"
            print(f"🔑 Signing Classplus content: {content_id}")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract signed URL
            if isinstance(data, dict):
                signed_url = data.get("url") or (data.get("data", {}) or {}).get("url")
                drm_urls = data.get("drmUrls") or (data.get("data", {}) or {}).get("drmUrls")
                
                result = {}
                if signed_url:
                    result["url"] = signed_url
                    print(f"✅ Got signed URL")
                elif drm_urls:
                    result["url"] = drm_urls.get("manifestUrl", "")
                    result["drm_url"] = drm_urls.get("manifestUrl", "")
                    result["keys"] = data.get("data", {}).get("keys", [])
                    print(f"✅ Got DRM signed URL with {len(result.get('keys', []))} keys")
                
                return result if result else None
            
            return None
            
        except Exception as e:
            print(f"❌ Classplus API Error: {e}")
            return None
    
    def get_stream_url(self, url: str, token: str, retry_count: int = 3) -> Optional[str]:
        """
        Get playable stream URL from Classplus encrypted URL
        
        Args:
            url: Classplus stream URL (usually .m3u8)
            token: User's token
            retry_count: Number of retries
            
        Returns:
            Playable URL or None
        """
        for attempt in range(1, retry_count + 1):
            try:
                print(f"🔄 Attempt {attempt}/{retry_count} to get stream URL")
                
                timestamp = str(int(time.time()))
                endpoint = "/cams/uploader/video/jw-signed-url"
                
                headers = self.headers.copy()
                headers["x-access-token"] = token
                
                params = {"url": url}
                
                signature = self._generate_signature(timestamp, "GET", endpoint, params)
                headers["x-signature"] = signature
                headers["x-timestamp"] = timestamp
                
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                signed_url = data.get("url")
                
                if signed_url:
                    print(f"✅ Got signed stream URL")
                    return signed_url
                
                if attempt < retry_count:
                    print(f"⚠️ Attempt {attempt} failed, retrying...")
                    time.sleep(15)
            
            except Exception as e:
                print(f"❌ Attempt {attempt} error: {e}")
                if attempt < retry_count:
                    time.sleep(15)
        
        return None


# Singleton instance
_cp_api_instance = None

def get_classplus_api(token: str = "") -> ClassplusSignedAPI:
    """Get or create Classplus API instance"""
    global _cp_api_instance
    if _cp_api_instance is None:
        _cp_api_instance = ClassplusSignedAPI()
    return _cp_api_instance
