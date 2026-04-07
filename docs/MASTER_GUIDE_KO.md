# 최저가 트래커: 나만의 대시보드 만들기 (1~100 마스터 가이드) 🚀

이 가이드는 최저가 트래커 프로그램을 처음 접하는 사용자가 자신의 목적(품목, 추적 셀러, 키워드)에 맞게 시스템을 구축하고 24시간 자동화된 대시보드를 소유할 수 있도록 돕는 **완결판 매뉴얼**입니다. 📖✨

---

## 🏗️ 0. 전체 흐름 요약
1.  **프로젝트 복제(Fork)**: GitHub에서 내 계정으로 코드 가져오기.
2.  **API 발급**: 네이버 검색, 구글 시트, Gmail 비밀번호 준비.
3.  **보안 정보 등록(Secrets)**: GitHub에 안전하게 키 저장하기.
4.  **나만의 설정(Customizing)**: `targets.yaml` 파일 수정하기.
5.  **대시보드 확인**: 자동으로 생성된 나만의 URL 접속.

---

## 🛠️ 1단계: 프로젝트 복제 및 API 준비

### 1-1. GitHub 복제 (Fork)
- 이 저장소 우측 상단의 **[Fork]** 버튼을 클릭하여 본인의 계정으로 프로젝트를 가져옵니다.

### 1-2. 네이버 검색 API 발급
- [네이버 개발자 센터](https://developers.naver.com/apps/#/register)에서 애플리케이션을 등록합니다.
    - **사용 API**: `검색` 선택.
    - **환경**: `WEB 설정` -> URL은 `http://localhost` 입력.
- 발급받은 **Client ID**와 **Client Secret**을 꼭 따로 메모해 두세요.

### 1-3. 구글 시트 및 서비스 계정
- [구글 시트](https://docs.google.com/spreadsheets)를 새로 만듭니다. 
- 주소창의 `.../d/1A2B3C.../edit` 부분에서 **ID(`1A2B3C...`)**를 메모합니다.
- [구글 클라우드 콘솔](https://console.cloud.google.com)에서 `Google Sheets API`를 활성화한 뒤 **서비스 계정 키(JSON)**를 발급받으세요.
- **필수**: 구글 시트의 [공유] 버튼을 눌러, 서비스 계정 이메일(JSON 데이터 내부의 `client_email`)에 '편집자' 권한을 주어야 합니다.

---

## 🔐 2단계: GitHub 보안 정보(Secrets) 등록

본인의 GitHub 저장소 상단 **[Settings]** -> **[Secrets and variables]** -> **[Actions]**에서 다음 6개를 등록합니다.

| Name | 값 (Value) | 설명 |
| :--- | :--- | :--- |
| `NAVER_CLIENT_ID` | 발급받은 ID | 네이버 검색용 |
| `NAVER_CLIENT_SECRET` | 발급받은 Secret | 네이버 검색용 |
| `GSHEET_ID` | 구글 시트 고유 ID | 데이터 저장용 |
| `GCP_SA_KEY` | JSON 키 파일 전체 내용 | 구글 서버 접속용 |
| `EMAIL_FROM` | 본인 Gmail 주소 | 알림 보낼 계정 |
| `EMAIL_APP_PASSWORD` | 16자리 앱 비밀번호 | Google 계정 보안에서 발급 |

---

## 📈 3단계: 나만의 타겟 설정 (`targets.yaml`) 🎯

이 부분이 프로젝트의 심장입니다! **`targets.yaml`** 파일을 본인의 상황에 맞게 수정하세요.

### ① 내 품목 등록 (`items`)
추적하고 싶은 상품마다 아래 덩어리를 추가/수정합니다.
- `name`: 대시보드에 보일 이름 (예: "S26 울트라")
- `query`: 네이버 쇼핑 실제 검색어 (정확할수록 좋습니다)
- `product_id`: 네이버 카탈로그 ID (상세페이지 URL 끝의 숫자) **<- 매우 중요!**

### ② 추적할 셀러 지정 (`monitored_sellers`)
내가 특히 관심 있게 보는 업체명을 리스트에 넣습니다. (예: "위드모바일", "삼성공식인증점")
여기에 적힌 이름과 검색 결과의 판매처가 일치하면 정밀 분석 대상이 됩니다.

### ③ 키워드 순위 추적 (`rank_query`)
해당 키워드로 검색했을 때 어떤 상품들이 상위에 있는지, 내 타겟이 몇 위에 있는지 감시합니다.

---

## 🎁 보너스: AI에게 대신 시키기 (Gemini / ChatGPT 용) 🪄

`targets.yaml` 설정을 직접 타이핑하기 어렵다면, 아래 **프롬프트(주문서)**를 복사해서 **Gemini나 ChatGPT**에 붙여넣으세요! AI가 완벽한 코드를 만들어 드립니다.

### [AI 마법 프롬프트 복사하기]
```text
너는 '네이버 쇼핑 최저가 트래커'의 전문 구성 작가야. 내가 주는 상품 정보를 바탕으로 아래 [표준 템플릿]의 구조를 100% 유지하며 `targets.yaml` 내용을 생성해줘.

### 📋 내가 추적하고 싶은 정보
- 상품명: [갤럭시 S26 울트라]
- 세부모델: [화이트 512GB, 바이올렛 512GB]
- 카테고리: [S26]
- 카탈로그 ID들: [화이트: 59045494153, 바이올렛: 59045494155]
- 추적 셀러: [위드모바일, 쇼마젠시, 코잇, 케이원정보]

### 🛠️ 출력할 [표준 템플릿] (이 구조를 절대로 변형하지 말 것)
common:
  exclude: used:cbshop
  display: 50
  timeout_seconds: 20
  ranking_limit: 100
  monitored_sellers:
    - "셀러명1"
    - "셀러명2"

targets:
  - name: "상품명 식별자"
    mode: api_query
    query: "검색어"
    rank_query: "순위체크용 검색어"
    category: "대분류"
    request:
      pages: 1
      sort: sim
    match:
      required_keywords: ["필수", "키워드"]
      exclude_keywords: ["중고", "리퍼", "케이스"]
      product_id: "카탈로그ID(문자열)"
      allowed_product_types: [1, 3]
    url: "https://search.shopping.naver.com/catalog/ID"
    browser:
      wait_until: domcontentloaded
      price_selector: "[class^='style_price_num']"
      seller_selector: "[class^='style_mall_name']"
      offer_row_selector: "li[class^='style_seller_item']"

mall_targets:
  - name: "셀러별 타겟 별명"
    query: "검색어"
    mall_name: "추적할 셀러명"
    category: "대분류"
    request:
      pages: 10

### ⚠️ 작성 규칙
1. `common.monitored_sellers`: 입력한 추적 셀러들을 리스트로 만듦.
2. `targets`: 각 세부 모델별로 하나씩 생성. `product_id`는 반드시 큰따옴표("")로 감쌀 것.
3. `match.required_keywords`: 상품명에서 중요한 단어들을 추출해서 리스트화.
4. `mall_targets`: 입력한 추적 셀러별로 각 상품에 대한 감시 설정을 생성 (pages: 10 고정).
5. 불필요한 설명 없이 바로 YAML 코드 블록만 출력할 것.
```

---

### 🗺️ 필드 매핑 가이드 (YAML -> UI)

1️⃣ **`category` (YAML)** ➡️ **상단 탭 (대분류)**
- YAML에 `category: "스마트폰"`이라고 적으면, 대시보드 상단에 **[스마트폰]**이라는 대메뉴 탭이 생깁니다. (워치, 냉장고, 세탁기 등 품목 단위 추천)

2️⃣ **`monitored_sellers` (YAML)** ➡️ **좌측 사이드바 (Mall)**
- `common:` 섹션에 등록한 판매처 이름들이 사이드바의 1차 메뉴가 됩니다.

3️⃣ **`name` (YAML)** ➡️ **셀러 하위 트리 (개별 상품) 🌲**
- 각 타겟의 `name` 필드가 상품의 별명이 되어 사이드바 최하단에 나타납니다.

4️⃣ **`rank_query` (YAML)** ➡️ **검색 노출 순위 (RANK) 🎯**
- **정의**: "고객이 이 키워드를 검색했을 때 내 상품이 몇 위에 있는가?"를 측정하는 키워드입니다.
- **차이점**: `query`는 가격 수집용(상세함), `rank_query`는 순위 체크용(대표 키워드)입니다.
- 대시보드 상단 지표나 리스트에서 **"Rank: 1위"**와 같은 수치로 나타납니다.

### 💡 한 줄 요약
> **"YAML 설정을 하는 것 자체가, 대시보드의 메뉴 구성과 순위 추적 대상을 설계하는 작업입니다."** 🛠️✨

---

## 🚀 4단계: 자동 구동 및 대시보드 확인

---

## 🚀 4단계: 자동 구동 및 대시보드 확인

### 4.1 Actions 활성화
- **[Actions]** 탭에서 `Enable workflows`를 누르고, `Naver Price Tracker` 워크플로우를 **[Run workflow]**로 첫 실행합니다.

### 4.2 대시보드 주소
- **[Settings]** -> **[Pages]** 에서 Source를 `GitHub Actions`로 변경하세요.
- 5분 뒤 나타나는 `https://아이디.github.io/프로젝트명/` 주소가 여러분의 실시간 대시보드입니다!

---

## 🕵️‍♂️ 5단계: 대시보드 200% 활용 포인트 (New!) 📈

- **계층형 사이드바**: 왼쪽 메뉴에서 셀러를 클릭하고 하위 상품을 골라보세요. 탐색이 압도적으로 빠릅니다. 🌳
- **누적 히스토리 타임라인**: 하단 테이블에는 수집된 모든 과거 데이터가 쌓여 있습니다. 가격의 고점과 저점을 수치로 정밀하게 추적하세요. ⏳
- **동적 그래프**: 각 상품별 최근 50개 포인트 변화를 실시간으로 확인하세요! 🎯

이제 여러분만의 최저가 추적 시스템이 완성되었습니다! 🚀💎✨🎯
