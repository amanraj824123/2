import os
import re
import sys
# Ensure root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import m3u8
import json
import time
import pytz
import asyncio
import requests
import subprocess
import urllib
import urllib.parse
import yt_dlp
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode

from modules.topic_handler import get_or_create_forum_topic, extract_autotopic_name, send_document_with_fallback, send_video_with_fallback, send_photo_with_fallback
from bs4 import BeautifulSoup
import saini as helper
import cw_helper
import html_handler
import globals
from db import db
from broadcast import broadcast_handler, broadusers_handler
from text_handler import text_to_txt
from youtube_handler import ytm_handler, y2t_handler, getcookies_handler, cookies_handler
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, CREDIT_LINK, cookies_file_path
from vars import api_url, api_token, token_cp, adda_token, photologo, photoyt, photocp, photozip
from aiohttp import ClientSession
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import random
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
import aiofiles
import zipfile
import shutil
import ffmpeg
from urllib.parse import urlparse, parse_qs
import base64
from custom_cipher import B64Cipher, Secret
from cp_encn import decrypt_cp_encn_video
from appx_al import (
    decrypt_aes_link,
    is_node_link,
    resolve_isp_link,
    resolve_node_link,
    decrypt_xor,
    download_xor_pdf,
    download_encrypted_pdf,
    download_cloudflare_pdf,
    zip_to_video,
    classify_appx_link,
    get_ytdlp_appx_header_args,
    get_appx_headers,
    deobfuscate_ts,
    AppxLinkInfo,
)

# ✅ Import new Classplus handler (replaces Golden Eagle)
from classplus_download import handle_classplus_link

# Classplus Headers for API calls
cp_headers = {
    "User-Agent": "Mobile-Android",
    "App-Version": "1.12.1.1",
    "Api-Version": "56",
    "Device-Id": "9d8ce7affa2f5032",
    "Device-Details": "motorola_Moto G4_SDK-32",
    "region": "IN",
    "accept-language": "en",
    "x-chrome-version": "143.0.7499.52",
    "Content-Type": "application/json",
    "Build-Number": "56",
    "isReviewerOn": "0",
    "is-apk": "0",
    "Connection": "Keep-Alive",
}

# AES Keys for aes:// handling
AES_KEY = "d62acaa3a9aaab68667cabdb850d4620"
AES_IV = "f12aa767375c0e58fa0b73c9bb9cb06f"


# ---------------------------------------------------------
# YOUTUBE FORMAT SELECTOR
# ---------------------------------------------------------
def youtube_format(raw_text2):
    return (
        f"bv*[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/"
        f"b[height<={raw_text2}]"
    )

# ---------------------------------------------------------
# YOUTUBE DOWNLOAD HANDLER (NO COOKIES)
# ---------------------------------------------------------
async def download_youtube(url, ytf, name):
    output_file = f"{name}.mp4"
    cmd = f'yt-dlp --concurrent-fragments 5 -f "{ytf}" "{url}" -o "{output_file}"'

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            if os.path.exists(output_file):
                print(f"YouTube download complete: {output_file}")
                return output_file
            else:
                print("Download finished but file missing.")
                return None
        else:
            print("YouTube download failed:")
            print(stderr.decode(errors="ignore"))
            return None

    except Exception as e:
        print(f"Error during YouTube download: {e}")
        return None


# ✅ CLASSPLUS VIDEO DOWNLOAD - Replaces Golden Eagle
async def download_classplus_signed(url, token, name, raw_text2):
    """
    Download Classplus video using direct signed API (NO Golden Eagle)
    """
    if not token or token == '/d':
        print(f"⚠️ No token for Classplus, skipping")
        return None
    
    try:
        print(f"🔐 Using direct Classplus signed API for: {url[:60]}...")
        
        # Use our new direct signed API handler
        result = await handle_classplus_link(url, token, name, raw_text2)
        
        if result:
            if result.startswith("DRM:"):
                # DRM content - handle separately
                mpd_url = result.replace("DRM:", "")
                return f"DRM:{mpd_url}"
            else:
                # Regular video downloaded
                return result
        
        return None
        
    except Exception as e:
        print(f"❌ Classplus download error: {e}")
        return None


async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    caption = globals.caption
    endfilename = globals.endfilename
    thumb = globals.thumb
    CR = globals.CR
    cwtoken = globals.cwtoken
    cptoken = globals.cptoken
    pwtoken = globals.pwtoken
    vidwatermark = globals.vidwatermark
    raw_text2 = globals.raw_text2
    quality = globals.quality
    res = globals.res
    topic = globals.topic

    # [Previous code remains the same until Classplus handling section around line 710]
    
    # ✅ SECTION: Classplus/Testbook handler - IMPROVED
    # OLD CODE (lines ~710-764) - REPLACED with better error handling
    if any(x in url for x in ["https://cpvod.testbook.com/", "classplusapp.com/drm/", "media-cdn.classplusapp.com", "media-cdn-alisg.classplusapp.com", "media-cdn-a.classplusapp.com"]):
        
        print(f"📺 Classplus video detected")
        
        # ✅ Use direct signed API (NO Golden Eagle)
        download_result = await download_classplus_signed(url, raw_text4, name, raw_text2)
        
        if download_result:
            if download_result.startswith("DRM:"):
                # DRM content
                mpd = download_result.replace("DRM:", "")
                keys_string = ""
                print(f"🔐 DRM content - will handle downstream")
            else:
                # Regular video
                url = download_result
                print(f"✅ Video signed and ready: {url[:60]}...")
        else:
            # Fallback to standard Classplus signing if direct API fails
            print(f"⚠️ Direct API failed, trying standard signing...")
            headers = {
                'host': 'api.classplusapp.com',
                'x-access-token': f'{raw_text4}',    
                'accept-language': 'en',
                'api-version': '56',
                'app-version': '1.12.1.1',
                'build-number': '56',
                'connection': 'Keep-Alive',
                'content-type': 'application/json',
                'device-details': 'motorola_Moto G4_SDK-32',
                'device-id': 'c28d3cb16bbdac01',
                'region': 'IN',
                'user-agent': 'Mobile-Android',
                'x-chrome-version': '143.0.7499.52',
                'isReviewerOn': '0',
                'is-apk': '0',
                'accept-encoding': 'gzip'
            }
            
            url_norm = url.replace('https://tencdn.classplusapp.com/', 'https://media-cdn.classplusapp.com/tencent/')
            params = {"url": f"{url_norm}"}
            
            try:
                res = requests.get("https://api.classplusapp.com/cams/uploader/video/jw-signed-url", params=params, headers=headers, timeout=30).json()
                if "url" in res:
                    url = res["url"]
                    print(f"✅ Fallback signing successful")
            except Exception as e:
                print(f"❌ Fallback signing failed: {e}")
    
    # [Rest of the download logic continues as before...]

