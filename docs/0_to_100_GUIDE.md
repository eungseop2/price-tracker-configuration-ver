# 🚀 네이버 최저가 추적 자동화 시스템 구축 가이드 (0부터 100까지!)

본 가이드는 프로그래밍 지식이 없는 입문자도 처음부터 끝까지 독립적으로 **가격 추적 자동화 시스템을 구축하고 배포**할 수 있도록 돕는 단계별 안내서입니다.

---

## 🏗️ 전체 흐름 요약
1.  **프로젝트 복제 (Fork)**: GitHub에서 내 계정으로 코드 가져오기.
2.  **API 및 인증 정보 발급**: 네이버 검색 API, 구글 시트 API, Gmail 앱 비밀번호 준비.
3.  **환경 변수 (Secrets) 등록**: GitHub에 보안이 필요한 키값들을 안전하게 저장.
4.  **자동화 및 대시보드 활성화**: GitHub Actions와 Pages 설정.
5.  **추적 타겟 설정**: `targets.yaml` 파일을 수정하여 원하는 상품 등록.

---

## 🛠️ 1단계: 프로젝트 복제 (Fork)
관리할 가격 추적기의 원본 프로젝트를 본인의 GitHub 계정으로 복제하여 개인 운영 환경을 구성합니다.
1.  GitHub에 로그인한 뒤, 본 저장소 우측 상단의 **[Fork]** 버튼을 클릭합니다.
2.  `Create fork`를 눌러 본인 계정으로 프로젝트를 가져옵니다.

## 🔑 2단계: API 및 인증 정보 발급

### 2-1. 네이버 검색 API 발급
1.  [네이버 개발자 센터](https://developers.naver.com/apps/#/register) 애플리케이션 등록.
2.  사용 API: **검색** 선택.
3.  환경: **WEB 설정** 선택 후 URL에 `http://localhost` 입력.
4.  발급된 **Client ID**와 **Client Secret**을 메모해 둡니다.

### 2-2. 구글 시트 및 서비스 계정 설정
1.  새 구글 스프레드시트를 만들고, 주소창에서 **시트 ID**를 복사합니다.
2.  [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 후 `Google Sheets API`와 `Google Drive API`를 활성화합니다.
3.  **서비스 계정**을 생성하고 **JSON 키 파일**을 다운로드하여 내용을 복사해 둡니다.
4.  구글 시트의 **[공유]** 버튼을 눌러 서비스 계정 이메일에 **편집자** 권한을 줍니다.

### 2-3. Gmail 앱 비밀번호 발급 (알림용)
1.  구글 계정 보안 설정에서 **2단계 인증**을 활성화합니다.
2.  **앱 비밀번호**를 검색하여 `PriceTracker` 등의 이름으로 16자리 비밀번호를 발급받아 저장합니다.

## 🔐 3단계: GitHub Secrets 등록
저장소의 **Settings > Secrets and variables > Actions**에서 아래 키들을 등록합니다.
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `GSHEET_ID`
- `GCP_SA_KEY` (JSON 키 내용 전체)
- `EMAIL_FROM` (발송용 Gmail)
- `EMAIL_APP_PASSWORD` (16자리 앱 비밀번호)

## 🚀 4단계: 자동 구동 및 대시보드 확인
1.  **Actions 탭**: `Enable workflows` 버튼을 누른 뒤 `Naver Price Tracker` 워크플로우를 **Run workflow**로 한 번 실행합니다.
2.  **Pages 설정**: **Settings > Pages**에서 Source를 **GitHub Actions**로 변경합니다.
3.  약 5분 뒤 상단에 나타나는 URL이 실시간 대시보드 주소가 됩니다.

## 🎯 5단계: 추약 타겟 설정 (targets.yaml)
저장소 루트에 있는 `targets.yaml` 파일을 편집하여 추적하고 싶은 상품 정보를 입력합니다.
- `name`: 대시보드 표시 이름
- `query`: 네이버 검색어
- `product_id`: 네이버 카탈로그 ID (MID)
- `category`: 대시보드 분류 탭 이름

---

## 💡 팁: AI 활용하기
`targets.yaml` 형식이 복잡하다면 ChatGPT나 Gemini에게 다음과 같이 요청해 보세요:
> "네이버 쇼핑에서 '갤럭시 워치7'을 추적하고 싶어. 카탈로그 ID는 12345야. 이 정보를 바탕으로 내 가격 트래커의 targets.yaml 형식을 만들어줘."
