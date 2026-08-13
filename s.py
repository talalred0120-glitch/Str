"""
MegaSource Multi-Arabic Scraper
================================
جلب الأفلام والمسلسلات العربية والمترجمة من 5 مصادر عربية مشهورة
"""

import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TITLE = "MegaSource ARABIC Multi"
VERSION = "2.0.0"
DESCRIPTION = "سيرفرات عربية ومترجمة (FaselHD, Akwam, EgyBest, Cima4U, Embed)"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

TMDB_API_KEY = "92c1507cc18d85290e7a0b96abb37316"

# 5 مواقع عربية مشهورة مع نطاقاتها الحديثة
DOMAINS = {
    "embed": "https://vidsrc.me",
    "fasel": "https://www.faselhd.center",
    "akwam": "https://ak.akwam.one",
    "egybest": "https://egybest.site",
    "cima4u": "https://cima4u.vip"
}

_cookiejar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookiejar))


def _request(url, method="GET", data=None, headers=None):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
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
        with _opener.open(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception:
        return 0, ""


def get_tmdb_info(imdb_id):
    """جلب معلومات الفيلم بـ اللغة العربية والإنجليزية من TMDB"""
    find_url = f"https://api.themoviedb.org/3/find/{urllib.parse.quote(imdb_id)}"
    query = urllib.parse.urlencode(
        {"api_key": TMDB_API_KEY, "external_source": "imdb_id", "language": "ar-SA"}
    )
    status, body = _request(find_url + "?" + query)
    if status != 200:
        return None
    try:
        data = json.loads(body)
        if data.get("movie_results"):
            item = data["movie_results"][0]
            return {
                "type": "movie",
                "title_ar": item.get("title"),
                "title_en": item.get("original_title"),
            }
        if data.get("tv_results"):
            item = data["tv_results"][0]
            return {
                "type": "tv",
                "title_ar": item.get("name"),
                "title_en": item.get("original_name"),
            }
    except Exception:
        pass
    return None


# --- المصدر 1: Arabic Embed Server (سيرفر بث سريع بحساب المعرف) ---
def scrape_embed(imdb_id, media_type, season=None, episode=None):
    if media_type == "movie":
        url = f"{DOMAINS['embed']}/embed/movie?imdb={imdb_id}"
    else:
        url = f"{DOMAINS['embed']}/embed/tv?imdb={imdb_id}&season={season}&episode={episode}"
    return {"source": "Embed Player (عربي / مترجم)", "url": url}


# --- المصدر 2: FaselHD (فاصل إعلاني) ---
def scrape_fasel(title):
    if not title: return None
    search_url = f"{DOMAINS['fasel']}/?s={urllib.parse.quote(title)}"
    status, body = _request(search_url)
    if status == 200:
        links = re.findall(r'href="([^"]+faselhd[^"]+)"', body)
        if links:
            return {"source": "FaselHD (فاصل إعلاني)", "url": links[0]}
    return None


# --- المصدر 3: Akwam (أكوام) ---
def scrape_akwam(title):
    if not title: return None
    search_url = f"{DOMAINS['akwam']}/search?q={urllib.parse.quote(title)}"
    status, body = _request(search_url)
    if status == 200:
        links = re.findall(r'href="(https://ak\.akwam\.[^"]+/movie/[^"]+)"', body)
        if links:
            return {"source": "Akwam (أكوام)", "url": links[0]}
    return None


# --- المصدر 4: EgyBest (إيجي بست) ---
def scrape_egybest(title):
    if not title: return None
    search_url = f"{DOMAINS['egybest']}/auto-complete.php?q={urllib.parse.quote(title)}"
    status, body = _request(search_url)
    if status == 200:
        try:
            data = json.loads(body)
            if data and isinstance(data, list):
                link = data[0].get("link")
                if link:
                    return {"source": "EgyBest (إيجي بست)", "url": DOMAINS['egybest'] + link}
        except Exception:
            pass
    return None


# --- المصدر 5: Cima4U (سيما فور يو) ---
def scrape_cima4u(title):
    if not title: return None
    search_url = f"{DOMAINS['cima4u']}/?s={urllib.parse.quote(title)}"
    status, body = _request(search_url)
    if status == 200:
        links = re.findall(r'href="([^"]+cima4u[^"]+)"', body)
        if links:
            return {"source": "Cima4U (سيما فور يو)", "url": links[0]}
    return None


def get_streams(media_type, media_id, config=None):
    imdb_id = media_id
    season = episode = None
    if ":" in media_id:
        parts = media_id.split(":", 2)
        imdb_id, season, episode = parts[0], parts[1], parts[2]

    streams = []
    tmdb_data = get_tmdb_info(imdb_id)
    title = tmdb_data.get("title_ar") or tmdb_data.get("title_en") if tmdb_data else None

    # 1. فحص Embed (سيرفر مباشر مضمون)
    embed_res = scrape_embed(imdb_id, media_type, season, episode)
    if embed_res:
        streams.append({
            "name": TITLE,
            "title": f"🎬 {embed_res['source']}",
            "url": embed_res["url"],
            "behaviorHints": {"notMyMetadata": True}
        })

    # 2. فحص المواقع العربية الخمسة بواسطة العناوين
    scrapers = [
        ("FaselHD", scrape_fasel),
        ("Akwam", scrape_akwam),
        ("EgyBest", scrape_egybest),
        ("Cima4U", scrape_cima4u)
    ]

    for name, scraper_func in scrapers:
        res = scraper_func(title)
        if res and res.get("url"):
            streams.append({
                "name": TITLE,
                "title": f"🍿 {res['source']}",
                "url": res["url"],
                "behaviorHints": {
                    "notMyMetadata": True,
                    "proxyHeaders": {
                        "request": {
                            "User-Agent": USER_AGENT,
                            "Referer": res["url"]
                        }
                    }
                }
            })

    return streams
