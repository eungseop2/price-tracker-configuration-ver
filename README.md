# Price Tracker (Configuration Version)

네이버 쇼핑 최저가 추적 및 랭킹 수집 엔진입니다.  
`targets.yaml`을 수정하여 원하는 제품을 추적할 수 있습니다.

## 빠른 시작

```bash
pip install -r requirements.txt
cp .env.example .env          # API 키 설정
vi targets.yaml               # 추적 대상 편집
python -m tracker.main once --config targets.yaml
```

## 문서

- [한국어 상세 설명](docs/README_ko.md)
- [설정 필드 명세서](configs/SCHEMA.md)
- [설정 예시 파일](configs/targets.example.yaml)
