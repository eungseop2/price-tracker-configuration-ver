# 🚀 Fork 후 첫 설정 가이드

본 프로젝트를 fork하여 본인만의 가격 추적기를 운영하는 전체 과정입니다. 코드 수정 없이 설정 파일(`targets.yaml`)과 GitHub Secrets만 등록하면 자동 운영이 가능합니다.

---

## ✨ 본 가이드는 프로그래밍 지식이 없는 담당자도 처음부터 끝까지 독립적으로 **가격 추적 자동화 시스템을 구축하고 배포**할 수 있도록 작성된 단계별 매뉴얼입니다. 안내된 순서에 따라 설정을 진행해 주시기 바랍니다.

---

## 💎 시스템 핵심 기능 요약 (Current Features)

*   **실시간 최저가 감지**: 설정한 상품의 네이버 쇼핑 최저가를 매 주기마다 확인합니다.
*   **스마트 가격 알림**: 가격 변동 시 하락폭/상승폭을 계산하여 깔끔한 HTML 메일로 전송합니다.
*   **몰(Mall) 단위 추적**: 특정 브랜드나 공식셀러의 전체 상품 리스트를 한꺼번에 모니터링합니다.
*   **통합 대시보드**: 수집된 데이터를 그래프와 표로 시각화하여 웹(Pages)으로 제공합니다.
*   **데이터 자산화**: 모든 이력을 Google Sheets와 Cloud Storage에 영구 보관합니다.

---

## ✨ 현재 가용 가능한 주요 기능

1.  **실시간 가격 추적 & 스마트 알림**
    - 네이버 쇼핑 상품 최저가 실시간 감지
    - 가격 변동(하락/상승) 시 상세 내역(변동액, 변동률) 포함 이메일 즉시 발송
    - 대시보드 바로가기 버튼 제공

2.  **판매처 전용 모니터링 (Mall Seller Tracker)**
    - 특정 쇼핑몰(예: 위드모바일, 코잇 등) 내의 모든 상품 판매 상태 통합 관리
    - 검색 결과가 없는 경우에도 '상품 없음' 상태를 명확히 기록 (데이터 투명성 확보)
    - 최대 100위까지의 깊은 검색 심도 지원 (누락 없는 수집)

3.  **멀티 탭 SPA 대시보드**
    - 단일 페이지 앱(SPA) 형태의 세련된 대시보드 UI
    - 판매처별 탭 전환을 통해 수많은 상품 정보를 한눈에 파악
    - 모바일 최적화 레이아웃 지원

4.  **클라우드 기반 데이터 영구 저장**
    - Google Cloud Storage(GCS) 연동을 통한 데이터 무제한 누적
    - Google Sheets 자동 기록으로 엑셀 기반 데이터 분석 가능
    - GitHub Actions를 활용한 24/7 자동화 환경

5.  **AI 기반 간편 설정**
    - 복잡한 코드 수정 없이 `targets.yaml` 파일만으로 제어
    - AI 프롬프트를 활용한 대화형 상품 등록 가이드 제공

---

### STEP 1. 레포 Fork하기
1. 원본 레포 우상단 **Fork** 버튼 클릭
2. 본인 계정으로 fork
3. fork 완료 후 본인 레포 URL 확인
   - 예: `https://github.com/{내 아이디}/price-tracker-configuration-ver`

### STEP 2. 네이버 API 키 발급
1. [네이버 개발자 센터](https://developers.naver.com/apps/#/register) 접속
2. 애플리케이션 등록
   - 사용 API: **검색** 선택
   - 환경: **WEB 설정** → URL에 `http://localhost` 입력
3. 등록 완료 후 **Client ID**와 **Client Secret** 복사
4. 이 두 값을 메모 (STEP 4에서 사용)

### STEP 3. Google 서비스 계정 및 시트 설정
본 시스템은 Google Sheets를 데이터베이스로 사용합니다.

1. **Google Sheet 생성**: 비어 있는 구글 시트를 하나 만들고, 주소창의 ID를 메모합니다.
   - 예: `https://docs.google.com/spreadsheets/d/{이_부분이_ID}/edit`
2. **Google Cloud Console** 접속 후 프로젝트 생성 (또는 기존 프로젝트 사용)
3. **API 및 서비스** → **라이브러리** → **Google Sheets API**, **Google Drive API** 각각 '사용' 설정
4. **IAM 및 관리자** → **서비스 계정** 생성
5. 서비스 계정 상세 → **키** 탭 → **키 추가** → **JSON** 다운로드
   > ⚠️ 이 JSON 파일(GCP_SA_KEY)은 절대 레포에 직접 올리지 마세요.
6. **시트 권한 부여**: 생성한 구글 시트 우측 상단 '공유' 클릭 → 서비스 계정 이메일(예: `...-sa@...iam.gserviceaccount.com`)을 '편집자'로 추가

### STEP 4. Gmail 앱 비밀번호 발급
일반 Gmail 비밀번호가 아닌 앱 전용 비밀번호가 필요합니다.

1. Google 계정 → **보안** → **2단계 인증** 활성화 (필수)
2. **앱 비밀번호** 검색 → 새 앱 비밀번호 생성
   - 앱 이름: `PriceTracker` (아무 이름이나 가능)
3. 생성된 16자리 비밀번호 복사 (공백 제외)
4. 메모해둘 값:
   - `EMAIL_FROM`: 발신에 사용할 Gmail 주소
   - `EMAIL_APP_PASSWORD`: 16자리 앱 비밀번호
   - `EMAIL_TO`: 알림 받을 이메일 주소 (쉼표로 여러 개 가능)

### STEP 5. GitHub Secrets 등록
앞에서 발급한 값들을 GitHub에 등록합니다.

1. fork한 내 레포 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 버튼 클릭
3. 아래 7개를 하나씩 등록합니다:

| Secret 이름 | 값 | 발급 출처 |
|---|---|---|
| `NAVER_CLIENT_ID` | 네이버 Client ID | STEP 2 |
| `NAVER_CLIENT_SECRET` | 네이버 Client Secret | STEP 2 |
| `GCP_SA_KEY` | 서비스 계정 JSON 파일 전체 내용 | STEP 3 |
| `GSHEET_ID` | 구글 시트 ID | STEP 3 |
| `EMAIL_FROM` | 발신 Gmail 주소 | STEP 4 |
| `EMAIL_APP_PASSWORD` | 앱 비밀번호 16자리 | STEP 4 |
| `EMAIL_TO` | 수신 이메일 주소 | STEP 4 |

### STEP 6. GitHub Actions 활성화
fork한 레포는 Actions 기능이 기본적으로 비활성화되어 있습니다.

1. 내 레포 → **Actions** 탭 클릭
2. **"I understand my workflows, go ahead and enable them"** 버튼 클릭
3. 왼쪽 목록에서 **Naver Price Tracker (Automated)** 클릭
4. **Run workflow** → **Run workflow** 클릭하여 첫 실행 테스트

### STEP 7. GitHub Pages 활성화
대시보드를 웹 브라우저에서 볼 수 있게 설정합니다.

1. 내 레포 → **Settings** → **Pages**
2. **Build and deployment** → **Source**: **GitHub Actions** 선택
3. Actions가 한 번 성공적으로 실행되면 자동으로 아래 URL에서 대시보드 접속 가능:
   - `https://{내 GitHub 아이디}.github.io/price-tracker-configuration-ver`
   > 💡 **Tip**: 메일 알림에 포함되는 '대시보드 바로가기' 버튼도 위 URL로 자동 연결됩니다. 만약 커스텀 도메인을 사용하신다면, GitHub Secrets에 `DASHBOARD_URL` 변수를 추가하여 본인의 도메인 주소를 등록해 주세요.

### STEP 8. 품목 설정 (targets.yaml 수정)
다음 섹션의 AI 프롬프트를 활용하면 더 쉽게 작성할 수 있습니다.

1. 내 레포 루트의 `targets.yaml` 클릭
2. 우측 상단 ✏️ **편집(Edit)** 버튼 클릭
3. 추적할 상품 정보 수정
4. **Commit changes** 클릭 → 자동으로 Actions 수집이 시작됨

### STEP 9. 쇼핑몰(Seller) 별 상품 추적 설정
특정 쇼핑몰(예: 위드모바일, 코잇 등) 내의 모든 상품을 추적하고 싶을 때 사용합니다.

1. `targets.yaml` 파일 하단의 `mall_targets` 섹션을 수정합니다.
2. 각 필드의 의미:
   - `name`: 리포트에서 보여질 이름 (자유롭게 설정)
   - `query`: 해당 검색어로 네이버 쇼핑에서 검색
   - `mall_name`: 이 쇼핑몰에서 판매 중인 상품만 필터링하여 수집
3. 수정 후 **Commit changes**를 하면 다음 수집 주기부터 반영됩니다.

---

# ❓ FAQ (문제 해결)

**Q: Actions가 실패해요**
- **Actions** 탭 → 실패한 워크플로우 클릭 → 빨간 **X** 단계 클릭하여 오류 메시지를 확인하세요. 대부분 Secrets 누락이나 오타가 원인입니다.

**Q: 이메일이 안 와요**
- `EMAIL_APP_PASSWORD`가 일반 비밀번호가 아닌 구글 **앱 비밀번호**인지 확인하세요.
- Gmail **2단계 인증**이 활성화되어 있는지 확인하세요.

**Q: 대시보드가 안 열려요**
- **Settings** → **Pages** → **Source**가 **GitHub Actions**로 설정되어 있는지 확인하세요.
- Actions 워크플로우가 최소 한 번은 성공적으로 완료되었는지 확인하세요.

**Q: GCS 인증 오류가 나요**
- `GCP_SA_KEY`에 JSON 파일 내용 전체가 들어갔는지 확인하세요 (중괄호 `{ }` 포함).
- 서비스 계정에 **Storage 개체 관리자** 역할이 부여되었는지 확인하세요.

**Q: Sync fork 시 충돌이 나요**
- 내가 수정 중인 파일이 원격 저장소에서도 바뀐 경우 발생합니다.
- `targets.yaml` 내용을 따로 백업한 뒤 **Discard commits**를 실행하고 다시 붙여넣으세요.

---

# 🤖 AI로 targets.yaml 자동 생성하기

직접 YAML 구문을 작성하지 않아도 됩니다. 아래 프롬프트를 복사하여 ChatGPT, Claude, Perplexity 등 AI에 붙여넣으세요. `[ ]` 안의 항목만 본인의 상품 정보로 바꾸면 즉시 사용 가능한 `targets.yaml` 내용이 생성됩니다.

### 사용 방법
1. 아래 프롬프트 복사
2. `[ ]` 항목을 내 상품 정보로 채우기
3. AI에 붙여넣기
4. 생성된 YAML 내용을 `targets.yaml`에 그대로 붙여넣기

### 🔍 상품 ID 찾는 법 (입력 전 필수)
네이버 쇼핑에서 추적할 상품 페이지를 열면 URL 주소창에 ID가 포함되어 있습니다.
- 예: `https://search.shopping.naver.com/catalog/53507707536`
  - 여기서 `53507707536` 숫자가 바로 `product_id`입니다.

### 📝 AI 입력 프롬프트

```text
아래 정보를 바탕으로 네이버 쇼핑 가격 추적기의 targets.yaml 파일을 생성해줘.

=== 내가 추적할 상품 정보 ===

[상품 1]
- 상품명: [예: 갤럭시 버즈3 화이트]
- 검색 키워드: [예: 갤럭시 버즈3 화이트]
- 순위 검색어 (상품 계열 전체): [예: 갤럭시 버즈3]
- 카테고리: [예: 버징 / 워치 / 폰 / 노트북 등 자유롭게]
- 네이버 쇼핑 product_id: [예: 53507707536]
- 반드시 포함되어야 할 키워드: [예: 버즈3, 화이트]
- 제외할 키워드: [예: 중고, 리퍼, 케이스, 커버, 필름]

[상품 2]
- 상품명: [예: 갤럭시 버즈3 실버]
- 검색 키워드: [예: 갤럭시 버즈3 실버]
- 순위 검색어: [예: 갤럭시 버즈3]
- 카테고리: [예: 버즈]
- 네이버 쇼핑 product_id: [예: 53507707537]
- 반드시 포함되어야 할 키워드: [예: 버즈3, 실버]
- 제외할 키워드: [예: 중고, 리퍼, 케이스, 커버, 필름]

(상품이 더 있으면 같은 형식으로 추가)

=== 출력 규칙 ===
- 아래 YAML 구조를 정확히 유지할 것
- product_id는 반드시 따옴표('')로 감쌀 것
- url 마지막 숫자는 product_id와 동일하게 할 것
- browser 섹션은 모든 상품에 아래 값을 동일하게 적용할 것
- 탭(Tab) 대신 스페이스 2칸으로 들여쓰기할 것
- common 섹션은 아래 값을 그대로 사용할 것

=== 출력 YAML 형식 ===

common:
  exclude: used:cbshop
  display: 50
  timeout_seconds: 20
targets:
- name: [상품명]
  mode: api_query
  query: '[검색 키워드]'
  rank_query: '[순위 검색어]'
  category: [카테고리]
  request:
    pages: 1
    sort: sim
    filter: null
  match:
    required_keywords:
    - [키워드1]
    - [키워드2]
    exclude_keywords:
    - 중고
    - 리퍼
    - [기타 제외어]
    product_id: '[product_id]'
    allowed_product_types:
    - 1
    - 3
  url: https://search.shopping.naver.com/catalog/[product_id]
  browser:
    wait_until: domcontentloaded
    click_selectors: []
    price_selector: "[class^='style_price_num']"
    seller_selector: "[class^='style_mall_name']"
    offer_row_selector: "li[class^='style_seller_item']"
```

> ⚠️ **주의사항**
> - `product_id`는 반드시 따옴표(`'`)로 감싸야 합니다.
> - 생성된 YAML을 붙여넣기 전, 들여쓰기(스페이스)가 깨지지 않았는지 확인하세요.
> - 탭(Tab) 대신 **스페이스 2칸**을 사용해야 합니다.
> - `common` 섹션은 파일 맨 위에 한 번만 작성합니다.

---
---

## 🚀 로컬 실행 명령어 (CLI)

로컬 개발 환경이나 서버에서 직접 실행할 때 사용하는 명령어입니다.

```bash
# 1. 1회 즉시 수집
export PYTHONPATH=src
py -m tracker.main once

# 2. 실시간 모니터링 데몬 (기본 1시간 간격)
py -m tracker.main monitor --interval 3600

# 3. 대시보드 UI 데이터 내보내기 (dashboard_data.json 생성)
py -m tracker.main export-ui

# 4. 일일 가격 변동 HTML 리포트 생성
py -m tracker.main export-report --output daily_report.html

# 5. 로컬에서 대시보드 서버 실행 (http://localhost:8000)
py -m tracker.main serve
```

---

## 📊 데이터 필드 및 상태 정의

### 수집 상태 (Status)
- `OK`: 수집 성공
- `NO_MATCH`: 검색 결과 매칭 실패
- `BrowserScrapeError`: 브라우저 크롤링 중 오류

### 가격 변동 상태
- `FIRST_SEEN`: 첫 수집됨
- `PRICE_SAME`: 가격 변동 없음
- `PRICE_DOWN`: 가격 하락 (초록색 표시)
- `PRICE_UP`: 가격 상승 (빨간색 표시)

### 🕒 시간대 및 데이터 기록 안내
- **한국 표준시(KST) 적용**: 모든 수집 데이터의 `collected_at` 및 대시보드 업데이트 시각은 한국 시간(UTC+9)을 기준으로 기록됩니다.
- **배치 기록(Batch Insert)**: Google Sheets API 성능 최적화를 위해 한 회차의 모든 수집 결과를 모아서 한 번에 기록합니다. 이를 통해 데이터 누락 방지 및 실행 속도가 대폭 개선되었습니다.
