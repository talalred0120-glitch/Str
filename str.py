"""
MegaSource Arab Scraper
======================
هذا السكرايبر مخصص لجلب الأفلام والمسلسلات العربية أو المترجمة/المدبلجة للعربية
"""

import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TITLE = "MegaSource Arabic"
VERSION = "1.0.0"
DESCRIPTION = "أفلام ومسلسلات عربية ومترجمة"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# مفتاح TMDB للبحث عن أسماء العناوين باللغة العربية
TMDB_API_KEY = "92c1507cc18d85290e7a0b96abb37316"
# رابط محرك البحث العربي (مثال لمصدر عربي)
ARABIC_BASE_URL = "https://faselhd.center" 

_cookiejar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookiejar))


def _request(url, method="GET", data=None, headers=None):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    }
    if headers:
        request_headers.update(headers)

    body = None
    if method == "POST":
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode("utf-8")
        elif data is not None:
            body = data

    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with _opener.open(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception:
        return 0, ""


def get_arabic_title(imdb_id):
    """جلب اسم الفيلم/المسلسل بالعربي أو الإنجليزي من TMDB"""
    find_url = f"https://api.themoviedb.org/3/find/{urllib.parse.quote(imdb_id)}"
    query = urllib.parse.urlencode(
        {"api_key": TMDB_API_KEY, "external_source": "imdb_id", "language": "ar-SA"}
    )
    status, body = _request(find_url + "?" + query)
    if status != 200:
        return None
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return None

    if data.get("movie_results"):
        item = data["movie_results"][0]
        return {"type": "movie", "title": item.get("title") or item.get("original_title")}
    if data.get("tv_results"):
        item = data["tv_results"][0]
        return {"type": "tv", "title": item.get("name") or item.get("original_name")}
    return None


def search_arabic_source(title, media_type, season=None, episode=None):
    """البحث في المصدر العربي عن الفيديو"""
    search_query = urllib.parse.quote(title)
    search_url = f"{ARABIC_BASE_URL}/?s={search_query}"
    
    status, body = _request(search_url)
    if status != 200:
        return {}

    # البحث عن روابط الفيديو المباشرة أو سيرفرات التشغيل داخل الصفحة العربية
    # استخراج سيرفرات التشغيل (Embed / m3u8)
    video_urls = re.findall(r'file":\s*"([^"]+\.m3u8[^"]*)"', body)
    if not video_urls:
        video_urls = re.findall(r'<iframe[^>]+src="([^"]+)"', body)

    if video_urls:
        return {
            "url": video_urls[0],
            "User-Agent": USER_AGENT,
            "Referer": ARABIC_BASE_URL + "/",
        }
    return {}


def get_streams(media_type, media_id, config=None):
    imdb_id = media_id
    season = episode = None
    if ":" in media_id:
        parts = media_id.split(":", 2)
        imdb_id, season, episode = parts[0], parts[1], parts[2]

    # 1. جلب اسم المحتوى العربي من TMDB
    media_info = get_arabic_title(imdb_id)
    if not media_info or not media_info.get("title"):
        return []

    arabic_title = media_info["title"]

    # 2. البحث في الموقع العربي عن الفيديو
    info = search_arabic_source(arabic_title, media_type, season, episode)

    if not info or not info.get("url"):
        return []

    # 3. إرجاع النتائج بتنسيق Stremio باللغة العربية
    return [
        {
            "name": TITLE,
            "title": f"عربي / مترجم - {arabic_title}",
            "url": info["url"],
            "behaviorHints": {
                "notMyMetadata": True,
                "proxyHeaders": {
                    "request": {
                        "User-Agent": info.get("User-Agent", USER_AGENT),
                        "Referer": info.get("Referer", ARABIC_BASE_URL + "/"),
                    }
                },
            },
        }
    ]
