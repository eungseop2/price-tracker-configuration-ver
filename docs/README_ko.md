# 🚀 Fork 후 첫 설정 가이드

이 프로젝트를 fork하여 본인만의 가격 추적기를 운영하는 전체 과정입니다.
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

1. 내 레포 루트의 `targets.yaml` 클릭
2. 우측 상단 ✏️ 편집 버튼 클릭
3. 추적할 상품 정보 수정 (작성법은 [설정 필드 명세서](../configs/SCHEMA.md) 참고)
4. **Commit changes** 클릭 → 자동으로 Actions 실행됨

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

---

# 🤖 AI로 targets.yaml 자동 생성하기

직접 YAML을 작성하지 않아도 됩니다. 아래 프롬프트를 AI에 붙여넣어 `targets.yaml`을 생성하세요.

### 📝 AI 입력 프롬프트

````
아래 정보를 바탕으로 네이버 쇼핑 가격 추적기의 targets.yaml 파일을 생성해줘.

=== 내가 추적할 상품 정보 ===
[상품명], [검색 키워드], [순위 검색어], [product_id] 등을 입력하세요.

=== 출력 규칙 ===
- product_id는 반드시 따옴표('')로 감쌀 것
- 탭(Tab) 대신 스페이스 2칸으로 들여쓰기할 것
- common 섹션은 파일 맨 위에 한 번만 작성할 것
````

---

# ❓ FAQ (문제 해결)

**Q: Actions가 실패해요**
→ **Actions** 탭 → 실패한 워크플로우 클릭 → 빨간 ❌ 단계 클릭하여 오류 메시지 확인.

**Q: 대시보드가 안 열려요**
→ **Settings** → **Pages** → Source가 **GitHub Actions**인지 확인하세요.
