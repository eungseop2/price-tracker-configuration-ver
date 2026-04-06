# Price Tracker (Configuration Version) 🚀

네이버 쇼핑 최저가 추적 및 랭킹 수집 자동화 시스템입니다.  
`targets.yaml`에 원하는 상품을 등록하는 것만으로 24시간 나만의 가격 대시보드를 소유할 수 있습니다. 📊✨

---

## 📖 초보자용 가이드 (1부터 100까지!)
이 프로그램을 처음 접하시나요? **아래 가이드를 클릭해서 5분 만에 나만의 트래커를 설치해 보세요.** 
- **[👉 나만의 대시보드 만들기 (MASTER GUIDE)](docs/MASTER_GUIDE_KO.md)**

---

## ✨ 핵심 기능
- **🌳 계층형 사이드바**: [셀러 > 상품] 트리 구조로 수많은 품목도 빠르고 정확하게 탐색!
- **⏳ 누적 히스토리 타임라인**: 과거부터 현재까지 쌓인 모든 가격 기록을 리스트로 확인!
- **📈 동적 시계열 그래프**: 최근 50개 수집 포인트의 변동 추이를 시각적으로 분석!
- **🤖 완전 자동화**: GitHub Actions를 통해 매일 정해진 시간에 데이터를 수집하고 대시보드를 갱신!

---

## 🛠️ 개발자용 빠른 시작 (Quick Start)

```bash
pip install -r requirements.txt
cp .env.example .env          # API 키 설정
vi targets.yaml               # 추적 타겟 편집
python -m tracker.main once --config targets.yaml
```

## 📚 상세 문서
- **[상세 가이드 (MASTER_GUIDE_KO.md)](docs/MASTER_GUIDE_KO.md)**
- **[한국어 README](docs/README_ko.md)**
- **[설정 필드 명세서 (configs/SCHEMA.md)](configs/SCHEMA.md)**
- **[설정 예시 파일 (configs/targets.example.yaml)](configs/targets.example.yaml)**

---

저작권 및 문의 사항은 저장소의 이슈(Issue) 탭을 이용해 주세요. 🛡️💎🕺
