"""
fetch_and_summarize.py
보험저널뿐만 아니라 한국경제, 매일경제, 금융 전문지 등 다양한 언론사의 기사를 폭넓게 수집하고
Gemini API로 3줄 요약과 실무 인사이트를 생성하여 news_data.json으로 저장하는 파이프라인입니다.
"""

import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 폭넓은 언론사 RSS 피드 목록 (보험저널 + 주요 경제지 금융/보험 섹션)
RSS_SOURCES = [
    {
        "name": "보험저널",
        "url": "https://www.insjournal.co.kr/rss/allArticle.xml",
        "category": "ga"
    },
    {
        "name": "보험저널(종합)",
        "url": "https://www.insjournal.co.kr/rss/S1N1.xml",
        "category": "insurer"
    },
    {
        "name": "매일경제(금융)",
        "url": "https://www.mk.co.kr/rss/30100041/",
        "category": "finance"
    },
    {
        "name": "한국경제(경제·금융)",
        "url": "https://www.hankyung.com/feed/economy",
        "category": "finance"
    }
]

# 2. 네이버 뉴스 검색 키워드 (다양한 언론사의 보험/GA 관련 기사 폭넓은 수집)
SEARCH_QUERIES = [
    {"query": "보험 GA", "category": "ga"},
    {"query": "보험 수수료 1200%", "category": "fee"},
    {"query": "보험사 신상품 CSM", "category": "insurer"},
    {"query": "금감원 보험사 검사", "category": "fee"}
]

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def fetch_rss_articles(source, limit=4):
    """RSS 피드에서 개별 기사의 정확한 원문 URL과 제목, 요약문을 파싱합니다."""
    articles = []
    try:
        req = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items = root.findall(".//item")

        for item in items[:limit]:
            title = item.findtext("title", "").strip()
            # 정확한 기사 개별 원문 URL 추출
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            if title and link:
                articles.append({
                    "title": title,
                    "url": link,  # 기사 상세 원문 링크
                    "source": source["name"],
                    "content": desc,
                    "pub_date": pub_date,
                    "default_cat": source.get("category", "ga")
                })
    except Exception as e:
        print(f"[{source['name']}] RSS 수집 오류: {e}")

    return articles


def fetch_naver_search_articles(query_info, limit=3):
    """네이버 검색 API를 활용해 다양한 종합일간지/경제지의 보험 기사를 수집합니다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []

    articles = []
    try:
        encoded_q = urllib.parse.quote(query_info["query"])
        url = f"https://openapi.naver.com/v1/search/news.json?query={encoded_q}&display={limit}&sort=date"
        req = urllib.request.Request(url)
        req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("items", []):
                # HTML 태그 제거
                title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                desc = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                # 언론사 직접 원문 링크(originallink) 우선, 없으면 link
                link = item.get("originallink") or item.get("link")
                
                articles.append({
                    "title": title,
                    "url": link,  # 해당 기사 상세 페이지 링크
                    "source": "언론사 종합",
                    "content": desc,
                    "pub_date": item.get("pubDate", ""),
                    "default_cat": query_info["category"]
                })
    except Exception as e:
        print(f"[네이버 검색 '{query_info['query']}'] 수집 오류: {e}")

    return articles


def analyze_with_gemini(article):
    """Gemini API를 호출하여 정확한 카테고리 분류, AI 3줄 요약, 실무 인사이트를 도출합니다."""
    if not GEMINI_API_KEY:
        cat = article.get("default_cat", "ga")
        cat_map = {
            "ga": ("보험·GA", "indigo"),
            "fee": ("수수료·제도", "amber"),
            "insurer": ("보험사 동향", "blue"),
            "finance": ("경제·금융", "emerald")
        }
        name, color = cat_map.get(cat, ("보험·GA", "indigo"))
        return {
            "category": cat,
            "categoryName": name,
            "categoryColor": color,
            "isBreaking": False,
            "summary": [
                article["title"],
                "상세 기사 전문은 원문 바로가기 링크를 통해 확인하실 수 있습니다.",
                "업계 최신 동향과 정책 방향성을 확인하세요."
            ],
            "insight": "GA 현장 영업 조직과 판매 수수료 구조에 미칠 영향을 면밀히 모니터링해야 합니다."
        }

    prompt = f"""당신은 15년 경력의 보험 및 금융 전문 시니어 애널리스트입니다.
아래 다양한 언론사에서 수집된 기사를 분석하여 JSON 형식으로만 응답해 주세요.

[기사 제목]: {article['title']}
[기사 내용 요약]: {article['content']}

[반드시 준수할 JSON 형식]:
{{
  "category": "ga" | "fee" | "insurer" | "finance",
  "categoryName": "보험·GA" | "수수료·제도" | "보험사 동향" | "경제·금융",
  "categoryColor": "indigo" (보험·GA) | "amber" (수수료·제도) | "blue" (보험사 동향) | "emerald" (경제·금융),
  "isBreaking": true 또는 false (업계에 파급력이 매우 큰 주요 속보인 경우 true),
  "summary": [
    "핵심 팩트 요약 1문장",
    "핵심 팩트 요약 2문장",
    "핵심 팩트 요약 3문장"
  ],
  "insight": "이 뉴스가 GA 영업 현장, 설계사 조직, 수수료 마진, 상품 판매 전략에 미치는 실질적인 시사점 1~2문장"
}}
"""

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            json_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(json_text)
    except Exception as e:
        print(f"Gemini API 호출 실패: {e}")
        cat = article.get("default_cat", "ga")
        return {
            "category": cat,
            "categoryName": "보험·GA",
            "categoryColor": "indigo",
            "isBreaking": False,
            "summary": [article["title"]],
            "insight": "현장 영향도 분석 요망."
        }


def main():
    print("1. 폭넓은 언론사 기사 수집 시작...")
    collected_articles = []

    # ① 주요 언론사 RSS 수집
    for src in RSS_SOURCES:
        collected_articles.extend(fetch_rss_articles(src, limit=4))

    # ② 네이버 뉴스를 통한 주요 일간지/경제지 수집
    for q_info in SEARCH_QUERIES:
        collected_articles.extend(fetch_naver_search_articles(q_info, limit=3))

    # 중복 제거 (URL 기준)
    unique_articles = []
    seen_urls = set()
    for art in collected_articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique_articles.append(art)

    print(f"총 {len(unique_articles)}개 기사 수집 완료. AI 분석 진행 중...")

    results = []
    for idx, art in enumerate(unique_articles):
        print(f"[{idx+1}/{len(unique_articles)}] 분석 중: {art['title'][:25]}...")
        ai_data = analyze_with_gemini(art)

        results.append({
            "id": f"news-{idx+1:02d}",
            "title": art["title"],
            "source": art["source"],
            "time": "최신",
            "url": art["url"],  # 기사 상세 직통 링크
            "category": ai_data.get("category", "ga"),
            "categoryName": ai_data.get("categoryName", "보험·GA"),
            "categoryColor": ai_data.get("categoryColor", "indigo"),
            "isBreaking": ai_data.get("isBreaking", False),
            "summary": ai_data.get("summary", []),
            "insight": ai_data.get("insight", "")
        })

    output_path = "news_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"성공! '{output_path}' 파일에 최신 기사 데이터가 저장되었습니다.")


if __name__ == "__main__":
    main()
