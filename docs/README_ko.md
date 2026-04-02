# 🚀 Fork 후 첫 설정 가이드

이 레포를 fork하여 본인만의 가격 추적기를 운영하는 전체 과정입니다.
코드 수정 없이 설정 파일(`targets.yaml`)과 GitHub Secrets만 등록하면 됩니다.

---

## STEP 1. 레포 Fork하기

1. 이 레포 우상단의 **Fork** 버튼 클릭
2. 본인 GitHub 계정으로 fork
3. fork 완료 후 본인 레포 URL 확인
   - 예: `https://github.com/{내 아이디}/price-tracker-configuration-ver`

---

## STEP 2. 네이버 API 키 발급

1. https://developers.naver.com/apps/#/register 접속
2. 애플리케이션 등록
   - 사용 API: **검색** 선택
   - 환경: **WEB 설정** → URL에 `http://localhost` 입력
3. 등록 완료 후 **Client ID**와 **Client Secret** 복사
4. 이 두 값을 메모 (STEP 5에서 사용)

---

## STEP 3. Google Cloud 설정 (GCS) — 선택사항

GCS는 수집된 DB를 영구 저장하는 외부 스토리지입니다.
설정하지 않으면 Actions 실행마다 DB가 초기화되지만 동작은 합니다.

1. https://console.cloud.google.com 접속 후 프로젝트 생성
2. **Cloud Storage** → 버킷(Bucket) 생성
   - 버킷 이름 메모 (예: `my-price-tracker-bucket`)
   - 리전: `asia-northeast3` (서울) 권장
3. **IAM 및 관리자** → **서비스 계정** 생성
   - 역할: **Storage 개체 관리자** 부여
4. 서비스 계정 → **키 추가** → JSON 형식으로 다운로드

> ⚠️ 이 JSON 파일은 절대 레포에 직접 올리지 마세요. GitHub Secrets에만 등록합니다.

5. 메모해둘 값:
   - `GCP_SA_KEY`: JSON 파일 전체 내용 (중괄호 `{ }` 포함)
   - `GCS_BUCKET`: 버킷 이름

---

## STEP 4. Gmail 앱 비밀번호 발급

일반 Gmail 비밀번호가 아닌 **앱 전용 비밀번호**가 필요합니다.

1. Google 계정 → **보안** → **2단계 인증** 활성화 (필수)
2. **앱 비밀번호** 검색 → 새 앱 비밀번호 생성
   - 앱 이름: `PriceTracker` (아무 이름)
3. 생성된 16자리 비밀번호 복사 (공백 제외)
4. 메모해둘 값:
   - `EMAIL_FROM`: 발신에 사용할 Gmail 주소
   - `EMAIL_APP_PASSWORD`: 16자리 앱 비밀번호
   - `EMAIL_TO`: 알림 받을 이메일 주소 (쉼표로 여러 개 가능)

---

## STEP 5. GitHub Secrets 등록

앞에서 발급한 값들을 GitHub에 등록합니다.

1. fork한 내 레포 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 버튼 클릭
3. 아래 7개를 하나씩 등록:

| Secret 이름 | 값 | 발급 출처 |
|---|---|---|
| `NAVER_CLIENT_ID` | 네이버 Client ID | STEP 2 |
| `NAVER_CLIENT_SECRET` | 네이버 Client Secret | STEP 2 |
| `GCP_SA_KEY` | JSON 파일 전체 내용 | STEP 3 (선택) |
| `GCS_BUCKET` | 버킷 이름 | STEP 3 (선택) |
| `EMAIL_FROM` | 발신 Gmail 주소 | STEP 4 |
| `EMAIL_APP_PASSWORD` | 앱 비밀번호 16자리 | STEP 4 |
| `EMAIL_TO` | 수신 이메일 주소 | STEP 4 |

---

## STEP 6. GitHub Actions 활성화

fork한 레포는 Actions가 기본으로 꺼져 있습니다.

1. 내 레포 → **Actions** 탭 클릭
2. **"I understand my workflows, go ahead and enable them"** 버튼 클릭
3. 왼쪽 목록에서 **Naver Price Tracker (Automated)** 클릭
4. **Run workflow** → **Run workflow** 클릭하여 첫 실행 테스트

---

## STEP 7. GitHub Pages 활성화

대시보드를 웹에서 볼 수 있게 설정합니다.

1. 내 레포 → **Settings** → **Pages**
2. **Source**: **GitHub Actions** 선택
3. Actions가 한 번 성공적으로 실행되면 자동으로 아래 URL에서 대시보드 접속 가능:
   - `https://{내 GitHub 아이디}.github.io/price-tracker-configuration-ver`

---

## STEP 8. 품목 설정 (targets.yaml 수정)

다음 섹션의 AI 프롬프트를 활용하면 더 쉽게 작성할 수 있습니다.

1. 내 레포 루트의 `targets.yaml` 클릭
2. 우측 상단 ✏️ 편집 버튼 클릭
3. 추적할 상품 정보 수정 (작성법은 [설정 필드 명세서](../configs/SCHEMA.md) 참고)
4. **Commit changes** 클릭 → 자동으로 Actions 실행됨

---

# 🤖 AI로 targets.yaml 자동 생성하기

직접 YAML을 작성하지 않아도 됩니다.
아래 프롬프트를 복사해서 ChatGPT, Claude, Perplexity 등 AI에 붙여넣고
`[ ]` 안의 항목만 본인 상품 정보로 바꿔서 입력하면
바로 사용 가능한 `targets.yaml`이 생성됩니다.

### 사용 방법

1. 아래 프롬프트 복사
2. `[ ]` 항목을 내 상품 정보로 채우기
3. AI에 붙여넣기
4. 생성된 YAML을 `targets.yaml`에 그대로 붙여넣기

### 🔍 상품 ID 찾는 법 (입력 전 필수)

네이버 쇼핑에서 추적할 상품 페이지를 열면 URL에 ID가 있습니다:

```
https://search.shopping.naver.com/catalog/53507707536
                                         ↑ 이 숫자가 product_id
```

### 📝 AI 입력 프롬프트

아래 내용을 통째로 복사하여 AI에 붙여넣으세요:

````
아래 정보를 바탕으로 네이버 쇼핑 가격 추적기의 targets.yaml 파일을 생성해줘.

=== 내가 추적할 상품 정보 ===

[상품 1]
- 상품명: [예: 갤럭시 버즈3 화이트]
- 검색 키워드: [예: 갤럭시 버즈3 화이트]
- 순위 검색어 (상품 계열 전체): [예: 갤럭시 버즈3]
- 카테고리: [예: 버즈 / 워치 / 폰 / 노트북 등 자유롭게]
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
````

> ⚠️ 주의사항
> - `product_id`는 반드시 따옴표(`'`)로 감싸야 합니다
> - 생성된 YAML 붙여넣기 전 들여쓰기(스페이스)가 깨지지 않았는지 확인하세요
> - 탭(Tab) 대신 스페이스 2칸을 사용해야 합니다
> - `common` 섹션은 파일 맨 위에 한 번만 작성합니다

---

# ❓ FAQ (문제 해결)

**Q: Actions가 실패해요**
→ **Actions** 탭 → 실패한 워크플로우 클릭 → 빨간 ❌ 단계 클릭
→ 오류 메시지 확인. 대부분 Secrets 누락이나 오타가 원인입니다.

**Q: 이메일이 안 와요**
→ `EMAIL_APP_PASSWORD`가 일반 비밀번호가 아닌 **앱 비밀번호**인지 확인
→ Gmail **2단계 인증**이 활성화되어 있는지 확인

**Q: 대시보드가 안 열려요**
→ **Settings** → **Pages** → Source가 **GitHub Actions**인지 확인
→ Actions가 최소 한 번 성공적으로 실행됐는지 확인

**Q: GCS 인증 오류가 나요**
→ `GCP_SA_KEY`에 JSON 전체 내용이 들어갔는지 확인 (중괄호 `{ }` 포함)
→ 서비스 계정에 **Storage 개체 관리자** 역할이 부여됐는지 확인

**Q: Sync fork 시 충돌이 나요**
→ 내가 수정한 파일이 원본에서도 바뀐 경우 발생
→ `targets.yaml` 내용을 따로 백업 후 **Discard commits** → 다시 붙여넣기

---
---

# 네이버 쇼핑 최저가 / 셀러 자동 추적기 (Advanced)

이 프로젝트는 네이버 쇼핑에서 특정 상품의 최저가와 판매 셀러를 자동으로 추적하고, 가격 변동 및 하락 알림을 제공합니다.

## ✨ 주요 기능

1. **가격 변동 정밀 감지**: 직전 성공 수집값과 비교하여 `PRICE_DOWN`, `PRICE_UP`, `PRICE_SAME` 상태를 기록합니다.
2. **API → 브라우저 자동 폴백**: API 검색 결과가 없을(`NO_MATCH`) 경우 자동으로 Playwright 브라우저를 구동하여 수집을 보완합니다.
3. **가격 하락 알림**: 직전 가격 대비 설정된 임계값(기본 5%) 이상 하락 시 `price_alerts.log`에 기록하고 경고를 출력합니다.
4. **고도화된 리포트**: `export-html` 명령으로 가격 변동 이력이 컬러로 시각화된 HTML 리포트를 생성합니다.
5. **안전한 데몬 운영**: `asyncio.sleep`과 `time.monotonic`을 사용하여 이벤트 루프 블로킹 없이 안정적인 주행을 지원합니다.
6. **강력한 설정 검증**: 실행 전 `targets.yaml`의 모든 설정 오류를 전수 조사하여 즉시 리포트합니다 (Fail-Fast).
7. **DB 자동 마이그레이션**: 컬럼이 추가되어도 기존 DB 손실 없이 자동으로 스키마를 갱신합니다.

## 🚀 빠른 시작

### 설치 및 설정
```bash
# 가상환경 생성 및 설치
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 설정 파일 생성
cp .env.example .env
cp targets.example.yaml targets.yaml
```

### 실행 및 리포트
```bash
# 1회 즉시 실행
PYTHONPATH=./src python -m tracker.main once

# HTML 리포트 생성
PYTHONPATH=./src python -m tracker.main export-html --html-out report.html

# 데몬 모드 (30분 간격)
PYTHONPATH=./src python -m tracker.main daemon --interval 1800
```

## ⚙️ 설정 가이드

### targets.yaml 명세
- `fallback_url`: `api_query` 모드 전용. API 결과가 없을 때 이동할 URL.
- `certified_item_id`: (또는 `certified_mall_product_id`) 인증점을 식별하기 위한 네이버 쇼핑 mallProductId (인증점 가격/비인증점 갯수 추적에 사용됨).
- `alert_threshold_percent`: (common 섹션) 알림 기준 하락폭 (예: 5.0).
- `required_keywords` & `exclude_keywords`: 검색 결과 중 정확히 원하는 상품만 골라내기 위한 필터링 옵션.
- `product_id`: 네이버 쇼핑 상품 카탈로그 ID. 정확한 매칭을 위해 입력을 강력 권장합니다.

### 📊 데이터 필드 정의
- `config_mode` / `source_mode`: `targets.yaml`에 정의된 원래 수집 모드 및 실제로 시도된 최종 수집 경로.
- `fallback_used`: API 검색 실패 후 브라우저 폴백으로 성공한 경우 `1`, 그 외 `0`.
- `status`: 수집 상태 (`OK`, `NO_MATCH`, `BrowserScrapeError` 등).
- **인증점 지표 (새로 추가됨)**:
  - `certified_between_non_auth_count`: 최저가와 인증점 가격 사이에 엄격히 위치한("끼어있는") 비인증점 수 (0이면 안전). 대표 지표.
  - `certified_cheaper_non_auth_count`: 인증점 가격보다 저렴한 모든 비인증점 수 (동률 제외). 보조 지표.
  - `certified_price` / `certified_rank` / `certified_total_sellers`: 인증점 가격, 전체 상품 중 순위, 전체 업체 수.

### 가격 변동 상태
- `FIRST_SEEN`: 첫 수집됨
- `PRICE_SAME`: 가격 변동 없음
- `PRICE_DOWN`: 가격 하락 (초록색 표시)
- `PRICE_UP`: 가격 상승 (빨간색 표시)

### 💡 정확한 추적을 위한 팁
1. **정합성 향상**: 액세서리(케이스, 필름 등)가 최저가로 잡히는 것을 방지하려면 `exclude_keywords`에 아래 단어들을 반드시 확인하세요.
   - 예시: `케이스`, `커버`, `필름`, `파우치`, `이어팁`, `호환`, `교체`, `부품`, `스트랩`, `거치대`, `스탠드`, `충전기`, `케이블`
2. **동일상품 매칭 우선**: `product_id`를 입력하면 키워드 필터링보다 우선적으로 해당 카탈로그 내 항목만 수집하므로 가장 정확합니다.
3. **fallback_url 운영**: API 결과가 없고 `fallback_url`이 null인 경우 브라우저 폴백 없이 즉시 에러 수집. 브라우저로 백업하려는 타겟만 URL을 설정하세요.
3. **리포트 수집경로 해석**:
   - `api_query → api_query`: API로 정상 수집
   - `api_query → browser_url [FALLBACK]`: API 검색 실패 후 브라우저 폴백 성공
   - `browser_url → browser_url`: 처음부터 브라우저로 수집

## 📁 파일 및 배포 구조
기본적으로 보안을 위해 GitHub Pages에는 대시보드 화면에 필요한 최소한의 내용만 공개됩니다.

### 🌐 공개 파일 (GitHub Pages - `public/` 디렉터리 배포)
- `dashboard.html`: 사용자 열람용 UI 컴포넌트
- `dashboard_data.json`: 시계열 가격 데이터 및 인증점 지표 요약본 (순수 공개 데이터)

### 🔒 비공개 운영 파일 (외부에 노출되지 않음)
- `.env`: Google Cloud 인증, Email 암호 등 Secrets
- `price_tracker.sqlite3`: 수집된 이력 전체 및 Error Log
- `artifacts/`, `logs/` 등: 브라우저 실패 스크린샷 및 추적 이력
