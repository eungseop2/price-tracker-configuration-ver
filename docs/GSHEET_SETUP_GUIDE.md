# 🚀 구글 스프레드시트 DB 연동 상세 가이드 (DB-test)

본 가이드는 `DB-test` 브랜치에서 SQLite 대신 구글 스프레드시트를 데이터베이스로 사용하기 위한 필수 설정 단계를 다룹니다.

## 💡 기존 GCS 키를 재사용하는 경우 (추천)
이미 프로젝트에서 GCS(Google Cloud Storage) 인증용 서비스 계정 키를 사용 중이시라면 아래 절차만으로 즉시 연동이 가능합니다.
1.  [Google Cloud Console](https://console.cloud.google.com/)에서 기존 프로젝트를 선택합니다.
2.  **API 및 서비스 > 라이브러리**에서 `Google Sheets API`와 `Google Drive API`를 **[사용]**으로 변경합니다.
3.  기존 JSON 키 파일의 `client_email` 주소를 복사하여, 사용하실 스프레드시트의 **[공유]** 메뉴에서 **편집자**로 추가합니다.
4.  환경 변수 `GOOGLE_SERVICE_ACCOUNT_KEY`에 기존 JSON 내용을 그대로 입력합니다.

## 1단계: Google Cloud 프로젝트 및 API 설정
1.  [Google Cloud Console](https://console.cloud.google.com/) 접속 및 새 프로젝트 생성.
2.  **API 및 서비스 > 라이브러리** 메뉴 이동.
3.  아래 두 가지 API를 검색하여 각각 **[사용]** 버튼 클릭:
    *   `Google Sheets API`
    *   `Google Drive API`

## 2단계: 서비스 계정(Service Account) 생성 및 키 다운로드
1.  **IAM 및 관리자 > 서비스 계정** 메뉴 이동.
2.  **[서비스 계정 만들기]** 클릭:
    *   이름 설정 (예: `price-tracker-bot`)
3.  생성된 계정 클릭 > **[키(Keys)]** 탭 이동.
4.  **[키 추가 > 새 키 만들기]** 클릭 후 **JSON** 형식 선택.
5.  다운로드된 `.json` 파일을 메모장으로 열어 내용을 복사해 둡니다. (이것이 `GOOGLE_SERVICE_ACCOUNT_KEY`가 됩니다.)

## 3단계: 스프레드시트 생성 및 권한 부여 (중요!)
1.  새로운 구글 스프레드시트를 생성합니다.
2.  브라우저 주소창의 URL에서 ID를 복사합니다:
    *   `https://docs.google.com/spreadsheets/d/`**[여기가 스프레드시트 ID]**`/edit`
3.  **[공유]** 버튼 클릭 > 2단계에서 만든 서비스 계정 이메일(예: `bot@...iam.gserviceaccount.com`)을 추가합니다.
4.  권한을 **[편집자(Editor)]**로 설정하고 저장합니다.

## 4단계: 프로젝트 환경 변수 등록 (로컬 테스트)
프로젝트 루트의 `.env` 파일에 아래 내용을 추가합니다.

```env
# 3단계에서 복사한 시트 ID
GSHEET_ID=your_spreadsheet_id_here

# 2단계에서 다운로드한 JSON 파일의 전체 내용 (GitHub Secrets에는 GCP_SA_KEY 이름으로 등록 권장)
GCP_SA_KEY='{"type": "service_account", "project_id": ...}'
```

---

## ✅ 정상 설정 확인 방법
모든 설정이 완료된 후, `DB-test` 브랜치에서 아래 명령어를 실행해 보세요.

```bash
# 수집 1회 실행
python -m src.tracker.main once --verbose
```

성공 시 스프레드시트에 `observations` 등의 탭이 자동으로 생성되면서 데이터가 입력됩니다.
