# 🛡️ 인슈어 인사이트 (InsurInsight)
> **나만의 모바일 보험·GA·금융 AI 뉴스룸 구축 가이드**

보험저널, GA 업계 동향, 수수료 제도, 주요 금융 뉴스를 매일 정해진 시간(아침 7시, 점심 12시, 저녁 6시)에 자동 수집하고, **Gemini AI가 3줄 핵심 요약과 실무 인사이트**를 도출해 스마트폰에서 앱처럼 볼 수 있는 100% 무료 시스템입니다.

---

## 📁 프로젝트 파일 구성

* `index.html`: 모바일 전용 반응형 대시보드 (속보 캐러셀, 카테고리 탭, 검색, 북마크, 요약 복사 기능 포함)
* `fetch_and_summarize.py`: 보험저널 RSS 수집 및 Gemini API를 통한 요약·인사이트 자동 생성 스크립트
* `.github/workflows/update_news.yml`: GitHub Actions를 통한 무료 3회/일 자동화 스케줄러

---

## 🚀 5분 무료 배포 및 스마트폰 즐겨찾기 세팅

### 1단계: GitHub 저장소 만들기
1. [GitHub](https://github.com)에 로그인 후 새 저장소(New repository)를 만듭니다. (예: `insurance-news`)
2. 프로젝트 파일들(`index.html`, `fetch_and_summarize.py`, `.github/workflows/update_news.yml`)을 업로드합니다.

### 2단계: Gemini API 키 등록 (무료)
1. [Google AI Studio](https://aistudio.google.com/)에서 무료 API 키를 발급받습니다.
2. GitHub 저장소의 **Settings** → **Secrets and variables** → **Actions**로 이동합니다.
3. **New repository secret**을 누르고:
   * Name: `GEMINI_API_KEY`
   * Secret: 발급받은 Gemini API 키 입력 후 저장

### 3단계: GitHub Pages 무료 호스팅 켜기
1. 저장소의 **Settings** → **Pages**로 이동합니다.
2. **Build and deployment** 항목의 Source를 `Deploy from a branch`로 설정하고, Branch를 `main` / `/(root)`로 지정한 뒤 **Save**를 누릅니다.
3. 약 1분 후 나만의 사이트 주소(`https://아이디.github.io/insurance-news/`)가 생성됩니다.

### 4단계: 스마트폰에서 앱처럼 즐겨찾기 (PWA)
* **아이폰 (Safari)**: 해당 웹 주소로 접속 후 하단 **[공유]** 버튼 → **[홈 화면에 추가]** 클릭
* **안드로이드 (Chrome)**: 해당 웹 주소로 접속 후 우측 상단 **[점 3개 메뉴]** → **[홈 화면에 추가]** 클릭
* 이제 스마트폰 홈 화면의 아이콘 터치 한 번으로 매일 아침 업데이트된 브리핑을 읽으실 수 있습니다.
