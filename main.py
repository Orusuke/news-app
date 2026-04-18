from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import feedparser
import asyncio
import httpx
import time
import re

app = FastAPI()

CACHE_TTL = 1800  # 30分キャッシュ
_cache: dict = {}

FEEDS = {
    "経済": [
        {"name": "Gニュース 株・市場", "url": "https://news.google.com/rss/search?q=%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87+%E6%A0%AA%E4%BE%A1+%E6%9D%B1%E8%A8%BC+%E7%9B%B8%E5%A0%B4&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 為替・金融", "url": "https://news.google.com/rss/search?q=%E7%82%BA%E6%9B%BF+%E5%86%86%E5%AE%89+%E5%86%86%E9%AB%98+%E9%87%91%E5%88%A9+%E6%97%A5%E9%8A%80&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース NISA・投資", "url": "https://news.google.com/rss/search?q=NISA+iDeCo+%E6%8A%95%E8%B3%87%E4%BF%A1%E8%A8%97+ETF+%E8%B3%87%E7%94%A3%E9%81%8B%E7%94%A8&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 税・財政・景気", "url": "https://news.google.com/rss/search?q=%E6%B8%9B%E7%A8%8E+%E8%B3%83%E4%B8%8A%E3%81%92+%E6%9C%80%E4%BD%8E%E8%B3%83%E9%87%91+%E6%99%AF%E6%B0%97+%E3%82%A4%E3%83%B3%E3%83%95%E3%83%AC&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 関税・貿易", "url": "https://news.google.com/rss/search?q=%E9%96%A2%E7%A8%8E+%E8%B2%BF%E6%98%93%E6%91%A9%E6%93%A6+%E5%80%92%E7%94%A3+%E5%9B%BD%E5%82%B5+%E8%B2%A1%E6%94%BF&hl=ja&gl=JP&ceid=JP:ja"},
    ],
    "健康": [
        {"name": "Yahoo! 健康", "url": "https://news.yahoo.co.jp/rss/categories/health.xml"},
        {"name": "Gニュース 病気・治療", "url": "https://news.google.com/rss/search?q=%E7%97%85%E6%B0%97+%E6%B2%BB%E7%99%82+%E5%8C%BB%E7%99%82+%E8%96%AC+%E6%8A%97%E4%BD%93&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース がん・生活習慣病", "url": "https://news.google.com/rss/search?q=%E3%81%8C%E3%82%93+%E7%B3%96%E5%B0%BF%E7%97%85+%E9%AB%98%E8%A1%80%E5%9C%A7+%E8%84%B3%E5%8D%92%E4%B8%AD+%E5%BF%83%E7%AD%8B%E6%A2%97%E5%A1%9E&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 健康・栄養", "url": "https://news.google.com/rss/search?q=%E5%81%A5%E5%BA%B7+%E6%A0%84%E9%A4%8A+%E7%9D%A1%E7%9C%A0+%E9%A3%9F%E4%BA%8B+%E8%85%B8%E5%86%85%E7%92%B0%E5%A2%83&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース メンタル・予防", "url": "https://news.google.com/rss/search?q=%E3%83%A1%E3%83%B3%E3%82%BF%E3%83%AB%E3%83%98%E3%83%AB%E3%82%B9+%E8%AA%8D%E7%9F%A5%E7%97%87+%E4%BA%88%E9%98%B2%E6%8E%A5%E7%A8%AE+%E3%82%A2%E3%83%AC%E3%83%AB%E3%82%AE%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja"},
    ],
    "筋トレ＆運動": [
        {"name": "Gニュース 筋トレ", "url": "https://news.google.com/rss/search?q=%E7%AD%8B%E3%83%88%E3%83%AC+%E3%83%88%E3%83%AC%E3%83%BC%E3%83%8B%E3%83%B3%E3%82%B0+%E7%AD%8B%E8%82%89+%E3%83%AF%E3%83%BC%E3%82%AF%E3%82%A2%E3%82%A6%E3%83%88&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 運動・スポーツ科学", "url": "https://news.google.com/rss/search?q=%E6%9C%89%E9%85%B8%E7%B4%A0%E9%81%8B%E5%8B%95+%E7%AD%8B%E5%8A%9B%E3%83%88%E3%83%AC%E3%83%BC%E3%83%8B%E3%83%B3%E3%82%B0+%E3%82%B9%E3%83%9D%E3%83%BC%E3%83%84%E7%A7%91%E5%AD%A6&hl=ja&gl=JP&ceid=JP:ja"},
    ],
    "家計・お得情報": [
        {"name": "Yahoo! マネー", "url": "https://news.yahoo.co.jp/rss/categories/money.xml"},
        {"name": "Gニュース 節約・家計", "url": "https://news.google.com/rss/search?q=%E7%AF%80%E7%B4%84+%E5%AE%B6%E8%A8%88+%E3%81%8A%E5%BE%97+%E5%89%B2%E5%BC%95&hl=ja&gl=JP&ceid=JP:ja"},
    ],
    "狩猟": [
        {"name": "Gニュース 狩猟", "url": "https://news.google.com/rss/search?q=%E7%8B%A9%E7%8C%9F+%E3%83%8F%E3%83%B3%E3%82%BF%E3%83%BC+%E7%8C%9F%E5%B8%AB+%E9%B9%BF+%E3%82%A4%E3%83%8E%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7%E3%82%B7&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース ジビエ", "url": "https://news.google.com/rss/search?q=%E7%8B%A9%E7%8C%9F+%E3%82%B8%E3%83%93%E3%82%A8+%E9%B9%BF%E8%82%89+%E3%82%A4%E3%83%8E%E3%82%B7%E3%82%B7%E8%82%89&hl=ja&gl=JP&ceid=JP:ja"},
    ],
    "クジラ類・海生哺乳類": [
        {"name": "Gニュース クジラ・イルカ", "url": "https://news.google.com/rss/search?q=%E3%82%AF%E3%82%B8%E3%83%A9+%E3%82%A4%E3%83%AB%E3%82%AB+%E9%AF%A8+%E6%B5%B7%E6%B4%8B%E5%93%BA%E4%B9%B3%E9%A1%9E&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Gニュース 鯨類研究", "url": "https://news.google.com/rss/search?q=%E3%82%AF%E3%82%B8%E3%83%A9+%E7%A0%94%E7%A9%B6+%E6%B5%B7%E7%94%9F%E5%93%BA%E4%B9%B3%E9%A1%9E+%E3%82%B7%E3%83%A7%E3%83%83%E3%82%AF%E3%82%A6%E3%82%A8%E3%83%BC+%E3%83%8F%E3%83%B3%E3%82%B6%E3%82%AF%E3%82%B8%E3%83%A9&hl=ja&gl=JP&ceid=JP:ja"},
    ],
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "経済": [
        "株価", "株式", "日経平均", "TOPIX", "東証", "相場", "配当",
        "為替", "円安", "円高", "ドル円", "ドル", "金利", "利上げ", "利下げ",
        "日銀", "FRB", "ECB", "金融政策", "量的緩和",
        "NISA", "ニーサ", "つみたて", "積立投資", "iDeCo", "イデコ",
        "投資信託", "ETF", "資産運用", "投資家", "ファンド", "インデックス",
        "GDP", "景気", "物価上昇", "物価高", "インフレ", "デフレ", "CPI",
        "景気後退", "景気回復", "経済成長",
        "所得税", "消費税", "法人税", "減税", "増税", "税制",
        "国債", "財政", "財源", "補正予算", "税収",
        "賃上げ", "最低賃金", "実質賃金",
        "関税", "貿易摩擦",
        "ビットコイン", "仮想通貨", "暗号資産",
        "倒産", "経営破綻", "金融危機",
        "円相場", "金融庁", "証券", "社債",
    ],
    "健康": [
        # 医療・治療
        "治療", "医療", "病院", "医師", "医薬品", "新薬", "処方", "手術", "入院",
        "診断", "疾患", "患者", "臨床試験",
        # 病気・症状
        "がん", "癌", "腫瘍", "糖尿病", "高血圧", "脳卒中", "心筋梗塞",
        "認知症", "アルツハイマー", "うつ病", "パーキンソン",
        "花粉症", "アレルギー", "喘息", "感染症", "ウイルス", "ワクチン",
        "熱中症", "骨粗しょう症", "肥満", "メタボ",
        # 健康・予防
        "健康寿命", "予防医学", "生活習慣病", "人間ドック",
        "血糖値", "血圧", "コレステロール", "腸内細菌", "免疫力",
        # 栄養・食事
        "栄養", "サプリメント", "ビタミン", "たんぱく質", "食事療法",
        # 睡眠・メンタル
        "睡眠障害", "不眠症", "メンタルヘルス",
        # 健康政策
        "厚生労働省", "医療費", "介護保険",
    ],
}

CATEGORY_BLOCKLIST: dict[str, list[str]] = {
    "経済": [
        "食品", "お菓子", "菓子", "スイーツ", "レシピ", "グルメ", "飲食",
        "ファッション", "アパレル", "コスメ", "化粧品", "美容", "スキンケア",
        "映画", "音楽", "アニメ", "ゲーム", "スポーツ選手", "芸能",
        "観光", "旅行", "ホテル", "レストラン", "カフェ",
        "ペット", "動物", "植物",
    ],
    "健康": [
        "ロケット", "JAXA", "宇宙", "衛星", "航空",
        "神社", "寺", "仏", "文化財", "世界遺産",
        "逮捕", "捜査", "事件", "事故", "裁判",
        "選挙", "議員", "国会", "政党", "外交",
        "ファッション", "音楽", "映画", "アニメ", "ゲーム",
        "スポーツ", "野球", "サッカー", "オリンピック",
    ],
}

CATEGORY_META = {
    "経済":           {"icon": "📈", "color": "#3b82f6"},
    "健康":           {"icon": "🏥", "color": "#10b981"},
    "筋トレ＆運動":   {"icon": "💪", "color": "#f59e0b"},
    "家計・お得情報": {"icon": "💰", "color": "#8b5cf6"},
    "狩猟":           {"icon": "🦌", "color": "#ef4444"},
    "クジラ類・海生哺乳類": {"icon": "🐋", "color": "#06b6d4"},
}


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def extract_image(entry) -> str:
    thumbnails = getattr(entry, "media_thumbnail", None)
    if thumbnails:
        return thumbnails[0].get("url", "")
    content = getattr(entry, "media_content", None)
    if content:
        for item in content:
            url = item.get("url", "")
            if url:
                return url
    enclosures = getattr(entry, "enclosures", None)
    if enclosures:
        for enc in enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", enc.get("url", ""))
    raw = entry.get("summary", "") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


OG_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
]


async def fetch_og_image(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> str:
    async with sem:
        try:
            async with client.stream("GET", url, timeout=8.0, follow_redirects=True) as resp:
                buf = b""
                async for chunk in resp.aiter_bytes(4096):
                    buf += chunk
                    if len(buf) > 20000 or b"</head>" in buf:
                        break
            text = buf.decode("utf-8", errors="ignore")
            for pat in OG_PATTERNS:
                m = pat.search(text)
                if m:
                    return m.group(1).strip()
        except Exception:
            pass
        return ""


async def fetch_feed(client: httpx.AsyncClient, source: dict) -> list:
    try:
        resp = await client.get(source["url"], timeout=12.0, follow_redirects=True)
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:20]:
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            sort_key = time.mktime(parsed) if parsed else 0
            summary = strip_html(entry.get("summary", "") or "")
            if len(summary) > 200:
                summary = summary[:200] + "…"
            articles.append({
                "title": strip_html(entry.get("title", "")),
                "url": entry.get("link", ""),
                "source": source["name"],
                "date": entry.get("published", entry.get("updated", "")),
                "image": extract_image(entry),
                "_sort": sort_key,
                "summary": summary,
            })
        return articles
    except Exception as e:
        print(f"  [WARN] {source['name']}: {e}")
        return []


@app.get("/api/categories")
def get_categories():
    return [
        {"id": k, **CATEGORY_META.get(k, {"icon": "📰", "color": "#64748b"})}
        for k in FEEDS
    ]


@app.get("/api/news/{category}")
async def get_news(category: str, refresh: bool = False):
    if category not in FEEDS:
        return JSONResponse({"error": "not found"}, status_code=404)

    now = time.time()
    cached = _cache.get(category)
    if not refresh and cached and (now - cached["at"]) < CACHE_TTL:
        return {"articles": cached["data"], "cached": True, "fetched_at": int(cached["at"])}

    print(f"[fetch] {category}")
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (compatible; PersonalNewsBot/1.0)"}) as client:
        results = await asyncio.gather(*[fetch_feed(client, s) for s in FEEDS[category]])

    articles = [a for r in results for a in r]

    seen, unique = set(), []
    for a in articles:
        if a["url"] and a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    keywords = CATEGORY_KEYWORDS.get(category)
    if keywords:
        blocklist = CATEGORY_BLOCKLIST.get(category, [])
        def is_relevant(a: dict) -> bool:
            haystack = (a["title"] + " " + a["summary"]).lower()
            if blocklist and any(bw.lower() in haystack for bw in blocklist):
                return False
            return any(kw.lower() in haystack for kw in keywords)
        unique = [a for a in unique if is_relevant(a)]

    unique.sort(key=lambda x: x.pop("_sort", 0), reverse=True)

    # og:image を持っていない記事から元記事のサムネを取得
    no_image = [a for a in unique if not a.get("image") and a.get("url")]
    if no_image:
        print(f"  [og:image] {len(no_image)}件 取得中...")
        sem = asyncio.Semaphore(10)
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
        ) as img_client:
            imgs = await asyncio.gather(*[fetch_og_image(img_client, a["url"], sem) for a in no_image])
        for a, img in zip(no_image, imgs):
            if img:
                a["image"] = img

    _cache[category] = {"data": unique, "at": now}
    return {"articles": unique, "cached": False, "fetched_at": int(now)}


# 静的ファイルは最後にマウント
app.mount("/", StaticFiles(directory="static", html=True), name="static")
