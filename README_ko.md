# 네이버 쇼핑 최저가 / 셀러 자동 추적기 (Advanced)

이 프로젝트는 네이버 쇼핑에서 특정 상품의 최저가와 판매 셀러를 자동으로 추적하고, 가격 변동 및 하락 알림을 제공합니다.

## ✨ 주요 기능

1. **가격 변동 정밀 감지**: 직전 성공 수집값과 비교하여 `PRICE_DOWN`, `PRICE_UP`, `PRICE_SAME` 상태를 기록합니다.
2. **API → 브라우저 자동 폴백**: API 검색 결과가 없을(`NO_MATCH`) 경우 자동으로 Playwright 브라우저를 구동하여 수집을 보완합니다.
3. **가격 하락 알림**: 직전 가격 대비 설정된 임계값(기본 5%) 이상 하락 시 `price_alerts.log`에 기록하고 경고를 출력합니다.
4. **일일 리포트 자동화**: `export-report` 명령으로 최근 10일간의 가격 동향을 요약한 HTML 리포트를 생성하며, 설정 시 이메일 발송이 가능합니다.
5. **웹 대시보드 제공**: `export-ui`를 통해 Chart.js 기반의 세련된 대시보드용 데이터를 생성하며, GitHub Pages를 통해 배포됩니다.
6. **강력한 설정 검증**: 실행 전 `targets.yaml`의 모든 설정 오류를 전수 조사하여 즉시 리포트합니다 (Fail-Fast).
7. **GCS 원격 동기화**: Google Cloud Storage와 연동하여 여러 환경에서 동일한 DB를 공유하고 데이터를 영구 보존합니다.

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
# 1. 1회 즉시 수집
export PYTHONPATH=src
python -m tracker.main once

# 2. 실시간 모니터링 데몬 (기본 1시간 간격)
python -m tracker.main monitor --interval 3600

# 3. 대시보드 UI 데이터 내보내기 (dashboard_data.json 생성)
python -m tracker.main export-ui

# 4. 일일 가격 변동 HTML 리포트 생성
python -m tracker.main export-report --output daily_report.html

# 5. 로컬에서 대시보드 서버 실행 (http://localhost:8000)
python -m tracker.main serve
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
