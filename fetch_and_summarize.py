"""
fetch_and_summarize.py
보험저널 및 금융 뉴스 RSS를 수집하고 Gemini API로 3줄 요약과 실무 인사이트를 생성하여 news_data.json으로 저장하는 스크립트입니다.
"""

import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 수집할 RSS 피드 목록
RSS_SOURCES = [
    {
        "name": "보험저널",
        "url": "https://www.insjournal.co.kr/rss/allArticle.xml",
        "default_cat": "ga"
    },
    {
        "name": "보험저널(종합)",
        "url": "https://www.insjournal.co.kr/rss/S1N1.xml",
        "default_cat": "insurer"
    }
]

# 네이버 뉴스 검색 API 정보 (선택 사항: 네이버 개발자센터 Client ID / Secret)
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# Gemini API Key (GitHub Secrets 또는 로컬 환경변수)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def fetch_rss_articles(source, limit=5):
    """RSS 피드에서 기사 제목, 링크, 요약문을 파싱합니다."""
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
            
            articles.append({
                "title": title,
                "url": link,
                "source": source["name"],
                "content": desc,
                "pub_date": pub_date
            })
    except Exception as e:
        print(f"[{source['name']}] RSS 수집 오류: {e}")
    
    return articles


def analyze_with_gemini(article):
    """Gemini API를 호출하여 카테고리 분류, AI 3줄 요약, 실무 인사이트를 도출합니다."""
    if not GEMINI_API_KEY:
        # API 키가 없을 때 기본 더미/규칙 기반 반환
        return {
            "category": "ga",
            "categoryName": "보험·GA",
            "categoryColor": "indigo",
            "isBreaking": False,
            "summary": [
                article["title"],
                "상세 내용은 원문 링크를 통해 확인하실 수 있습니다.",
                "최신 정책 및 영업 규정 준수 여부를 확인하세요."
            ],
            "insight": "GA 영업 현장 및 수수료 체계에 미치는 영향을 모니터링할 필요가 있습니다."
        }

    prompt = f"""당신은 15년 경력의 보험 및 금융 전문 시니어 애널리스트입니다.
아래 기사를 분석하여 JSON 형식으로만 응답해 주세요.

[기사 제목]: {article['title']}
[기사 내용 요약]: {article['content']}

[반드시 준수할 JSON 형식]:
{{
  "category": "ga" | "fee" | "insurer" | "finance",
  "categoryName": "보험·GA" | "수수료·제도" | "보험사 동향" | "경제·금융",
  "categoryColor": "indigo" (보험·GA) | "amber" (수수료·제도) | "blue" (보험사 동향) | "emerald" (경제·금융),
  "isBreaking": true 또는 false (업계에 즉각적인 파급력이 있는 주요 속보인 경우 true),
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
        return {
            "category": "ga",
            "categoryName": "보험·GA",
            "categoryColor": "indigo",
            "isBreaking": False,
            "summary": [article["title"]],
            "insight": "현장 영향도 분석 요망."
        }


def main():
    print("1. 기사 수집 시작...")
    collected_articles = []
    for src in RSS_SOURCES:
        collected_articles.extend(fetch_rss_articles(src, limit=5))

    print(f"총 {len(collected_articles)}개 기사 수집 완료. AI 분석 진행 중...")
    
    results = []
    for idx, art in enumerate(collected_articles):
        print(f"[{idx+1}/{len(collected_articles)}] 분석 중: {art['title'][:25]}...")
        ai_data = analyze_with_gemini(art)
        
        results.append({
            "id": f"news-{idx+1:02d}",
            "title": art["title"],
            "source": art["source"],
            "time": "방금 전",
            "url": art["url"],
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
