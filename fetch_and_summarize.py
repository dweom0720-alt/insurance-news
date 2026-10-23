"""
fetch_and_summarize.py
보험 뉴스뿐만 아니라 오늘의 주요뉴스, 경제동향, 사건사고까지 폭넓게 수집하고,
Gemini API를 통해 간결한 대표 키워드 카테고리(주요뉴스, 경제동향, 사건사고, 보험, GA, 수수료)로
분류 및 3줄 요약과 실무 인사이트를 생성하는 자동화 파이프라인입니다.
"""

import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 다각화된 언론사 RSS 소스 (주요뉴스, 경제동향, 사건사고, 보험 전문지)
RSS_SOURCES = [
    # 오늘의 주요뉴스 헤드라인
    {
        "name": "연합뉴스(주요뉴스)",
        "url": "https://www.yna.co.kr/rss/news.xml",
        "category": "headline",
        "categoryName": "주요뉴스"
    },
    # 경제동향 (거시경제, 금리, 환율)
    {
        "name": "매일경제(경제)",
        "url": "https://www.mk.co.kr/rss/30100041/",
        "category": "economy",
        "categoryName": "경제동향"
    },
    {
        "name": "한국경제(경제)",
        "url": "https://www.hankyung.com/feed/economy",
        "category": "economy",
        "categoryName": "경제동향"
    },
    # 사건사고 및 사회 이슈
    {
        "name": "연합뉴스(사회/사건사고)",
        "url": "https://www.yna.co.kr/rss/society.xml",
        "category": "incident",
        "categoryName": "사건사고"
    },
    # 보험 / GA / 수수료 전문 뉴스
    {
        "name": "보험저널(전체)",
        "url": "https://www.insjournal.co.kr/rss/allArticle.xml",
        "category": "insurance",
        "categoryName": "보험"
    }
]

# 2. 네이버 뉴스 검색 쿼리 (대표 키워드 매핑)
SEARCH_QUERIES = [
    {"query": "오늘의 주요뉴스", "category": "headline", "categoryName": "주요뉴스"},
    {"query": "경제동향 기준금리", "category": "economy", "categoryName": "경제동향"},
    {"query": "사건사고 금융사기", "category": "incident", "categoryName": "사건사고"},
    {"query": "보험 GA", "category": "ga", "categoryName": "GA"},
    {"query": "보험 수수료 1200%", "category": "fee", "categoryName": "수수료"}
]

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def fetch_rss_articles(source, limit=4):
    """RSS 피드에서 기사 상세 직통 URL과 제목, 요약문을 파싱합니다."""
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
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "source": source["name"],
                    "content": desc,
                    "pub_date": pub_date,
                    "default_cat": source.get("category", "headline"),
                    "default_cat_name": source.get("categoryName", "주요뉴스")
                })
    except Exception as e:
        print(f"[{source['name']}] RSS 수집 오류: {e}")

    return articles


def fetch_naver_search_articles(query_info, limit=3):
    """네이버 검색 API를 활용해 종합 뉴스 및 이슈 기사를 수집합니다."""
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
                title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                desc = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                link = item.get("originallink") or item.get("link")

                articles.append({
                    "title": title,
                    "url": link,
                    "source": "종합뉴스",
                    "content": desc,
                    "pub_date": item.get("pubDate", ""),
                    "default_cat": query_info["category"],
                    "default_cat_name": query_info["categoryName"]
                })
    except Exception as e:
        print(f"[네이버 검색 '{query_info['query']}'] 수집 오류: {e}")

    return articles


def analyze_with_gemini(article):
    """기사를 분석하여 간결한 대표 키워드 카테고리로 분류하고 3줄 요약과 실무 인사이트를 도출합니다."""
    default_cat = article.get("default_cat", "headline")
    default_cat_name = article.get("default_cat_name", "주요뉴스")

    if not GEMINI_API_KEY:
        return {
            "category": default_cat,
            "categoryName": default_cat_name,
            "summary": [
                article["title"],
                "기사 상세 내용은 원문 바로가기 링크에서 확인하실 수 있습니다.",
                "업계 및 사회 주요 이슈를 실시간으로 확인하세요."
            ],
            "insight": f"[{default_cat_name}] 관련 핵심 흐름을 지속적으로 모니터링할 필요가 있습니다."
        }

    prompt = f"""당신은 전문 시니어 뉴스 애널리스트입니다.
아래 기사를 분석하여 반드시 아래 JSON 형식으로만 응답해 주세요.

[기사 제목]: {article['title']}
[기사 내용 요약]: {article['content']}

[카테고리 분류 규칙]:
- 반드시 다음 대표 키워드 중 가장 적합한 하나를 선택하세요:
  1) "주요뉴스": 정치, 사회 전반, 주요 정책, 글로벌 헤드라인
  2) "경제동향": 거시경제, 기준금리, 물가, 환율, 증시 지표
  3) "사건사고": 사회적 사건사고, 금융 사기/피싱, 재난 및 안전
  4) "보험": 생·손보사 신상품, IFRS17 CSM, 실손/건강보험
  5) "GA": 법인보험대리점 조직, 제판분리, 설계사 채널 동향
  6) "수수료": 1200% 룰, 모집수수료 제도, 금감원 규제 및 시책

[JSON 출력 형식]:
{{
  "category": "headline" | "economy" | "incident" | "insurance" | "ga" | "fee",
  "categoryName": "주요뉴스" | "경제동향" | "사건사고" | "보험" | "GA" | "수수료",
  "summary": [
    "핵심 팩트 요약 1문장",
    "핵심 팩트 요약 2문장",
    "핵심 팩트 요약 3문장"
  ],
  "insight": "이 뉴스가 비즈니스, 영업 현장, 자산 관리, 개인 일상에 미치는 실질적인 시사점 1~2문장"
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
        return {
            "category": default_cat,
            "categoryName": default_cat_name,
            "summary": [article["title"]],
            "insight": f"[{default_cat_name}] 관련 주요 동향 확인 요망."
        }


def main():
    print("1. 주요뉴스, 경제동향, 사건사고, 보험 기사 수집 시작...")
    collected_articles = []

    # ① 주요 언론사 RSS 수집
    for src in RSS_SOURCES:
        collected_articles.extend(fetch_rss_articles(src, limit=4))

    # ② 네이버 뉴스를 통한 주요 종합 기사 수집
    for q_info in SEARCH_QUERIES:
        collected_articles.extend(fetch_naver_search_articles(q_info, limit=3))

    # 중복 제거
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
            "url": art["url"],
            "category": ai_data.get("category", art.get("default_cat", "headline")),
            "categoryName": ai_data.get("categoryName", art.get("default_cat_name", "주요뉴스")),
            "summary": ai_data.get("summary", []),
            "insight": ai_data.get("insight", "")
        })

    output_path = "news_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"성공! '{output_path}' 파일에 최신 기사 데이터가 저장되었습니다.")


if __name__ == "__main__":
    main()
