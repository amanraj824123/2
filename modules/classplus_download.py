"""
✅ Classplus Video Download Handler - Direct Signed Requests (No Golden Eagle)
Improved video downloading with better error handling
"""

import asyncio
import os
import requests
from typing import Optional, Tuple
from modules.classplus_api import get_classplus_api

async def download_classplus_video(
    url: str,
    token: str,
    video_name: str,
    quality: str = "480",
    max_retries: int = 3
) -> Optional[str]:
    """
    Download Classplus video with proper signed API requests
    
    Args:
        url: Classplus video URL (can be contentHashId, stream.m3u8, etc)
        token: User's Classplus token
        video_name: Output video filename
        quality: Video quality (144, 240, 360, 480, 720, 1080)
        max_retries: Maximum retry attempts
        
    Returns:
        Path to downloaded file or None if failed
    """
    
    cp_api = get_classplus_api()
    
    try:
        # Extract content ID from URL if needed
        content_id = extract_content_id(url)
        
        if not content_id:
            print(f"⚠️ Could not extract content ID from: {url}")
            return None
        
        # Try to get signed URL using direct API
        print(f"🔑 Getting signed URL for content: {content_id}")
        signed_data = cp_api.get_signed_video_url(content_id, token)
        
        if not signed_data or "url" not in signed_data:
            print(f"❌ Failed to get signed URL")
            return None
        
        signed_url = signed_data["url"]
        print(f"✅ Got signed URL: {signed_url[:60]}...")
        
        # Download video with retry logic
        for attempt in range(1, max_retries + 1):
            try:
                print(f"📥 Download attempt {attempt}/{max_retries}...")
                
                # Build yt-dlp command with quality
                ytf = f"bv*[height<={quality}][ext=mp4]+ba[ext=m4a]/b[height<={quality}]"
                cmd = f'yt-dlp --concurrent-fragments 5 -f "{ytf}" "{signed_url}" -o "{video_name}.mkv" -R 25 --fragment-retries 25'
                
                os.system(cmd)
                
                # Check if download successful
                output_file = f"{video_name}.mkv"
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 * 1024:  # > 1MB
                    print(f"✅ Download successful: {output_file}")
                    return output_file
                else:
                    print(f"⚠️ Download incomplete or failed")
                    if attempt < max_retries:
                        await asyncio.sleep(15)
                        continue
                    else:
                        return None
                        
            except Exception as e:
                print(f"❌ Download error (attempt {attempt}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(15)
                else:
                    return None
        
        return None
        
    except Exception as e:
        print(f"❌ Classplus video download failed: {e}")
        return None


def extract_content_id(url: str) -> Optional[str]:
    """
    Extract content ID from various Classplus URL formats
    
    Supported formats:
    - stream.m3u8?contentHashId=xxx
    - stream.m3u8?url=xxx&previewToken=yyy
    - media-cdn.classplusapp.com/drm/xxx
    """
    
    if not url:
        return None
    
    # Format 1: contentHashId parameter
    if "contentHashId=" in url:
        try:
            content_id = url.split("contentHashId=")[1].split("&")[0]
            if content_id:
                return content_id
        except:
            pass
    
    # Format 2: Extract from stream URL with url parameter
    if "stream.m3u8?url=" in url:
        try:
            stream_url = url.split("stream.m3u8?url=")[1].split("&")[0]
            # Try to extract content ID from stream URL
            if "media-cdn" in stream_url:
                parts = stream_url.split("/")
                if len(parts) > 0:
                    return parts[-1].replace(".m3u8", "")
        except:
            pass
    
    # Format 3: Direct media-cdn path
    if "media-cdn" in url and "/drm/" in url:
        try:
            content_id = url.split("/drm/")[1].split("/")[0]
            if content_id:
                return content_id
        except:
            pass
    
    return None


async def get_classplus_drm_keys_and_mpd(
    url: str,
    token: str,
    max_retries: int = 3
) -> Tuple[Optional[str], list]:
    """
    Get DRM keys and MPD URL from Classplus API
    
    Returns:
        Tuple of (mpd_url, keys_list)
    """
    
    cp_api = get_classplus_api()
    content_id = extract_content_id(url)
    
    if not content_id:
        return None, []
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔐 Getting DRM keys (attempt {attempt}/{max_retries})...")
            
            signed_data = cp_api.get_signed_video_url(content_id, token)
            
            if signed_data:
                mpd_url = signed_data.get("drm_url") or signed_data.get("url")
                keys = signed_data.get("keys", [])
                
                if mpd_url and keys:
                    print(f"✅ Got DRM content with {len(keys)} keys")
                    return mpd_url, keys
            
            if attempt < max_retries:
                print(f"⚠️ Attempt {attempt} failed, retrying...")
                await asyncio.sleep(15)
        
        except Exception as e:
            print(f"❌ Error getting DRM info (attempt {attempt}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(15)
    
    return None, []


# Integration function for drm_handler.py
async def handle_classplus_link(url: str, token: str, video_name: str, quality: str = "480") -> Optional[str]:
    """
    Main handler for Classplus links - replaces Golden Eagle calls
    
    This function should replace lines ~715 in drm_handler.py that call Golden Eagle API
    """
    
    if not token or token == '/d':
        print(f"⚠️ No valid token provided for Classplus")
        return None
    
    try:
        print(f"🎥 Processing Classplus link with signed API")
        
        # Try to download video
        video_file = await download_classplus_video(url, token, video_name, quality)
        
        if video_file:
            return video_file
        
        # If video download fails, try to get DRM keys
        print(f"⚠️ Video download failed, checking for DRM content...")
        mpd_url, keys = await get_classplus_drm_keys_and_mpd(url, token)
        
        if mpd_url and keys:
            print(f"🔐 DRM content detected - requires separate decryption")
            # Return marker for DRM handling downstream
            return f"DRM:{mpd_url}"
        
        return None
        
    except Exception as e:
        print(f"❌ Classplus handler error: {e}")
        return None
