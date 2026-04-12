# YAML 설정 필드 명세서 (Price Tracker Engine)

이 프로젝트는 YAML 파일을 통해 가격 추적 대상과 알림 설정을 관리합니다.

## `common` 섹션
전역 설정과 팀 정보를 포함합니다.

| 필드명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `team_name` | `string` | `"default"` | **[NEW]** 로그 및 알림에 표시할 팀 이름 |
| `display` | `int` | `100` | 네이버 쇼핑 검색 결과에서 가져올 최대 상품 수 |
| `exclude` | `string` | `"used:cbshop"` | 검색에서 제외할 옵션 (예: 중고 제품) |
| `timeout_seconds` | `int` | `20` | API 요청 타임아웃 (초) |
| `alert_threshold_percent` | `float` | `5.0` | 가격 변동 알림을 보낼 최소 변동률(%) |

## `targets` 섹션 (리스트)
추적할 개별 상품들의 목록입니다.

| 필드명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `name` | `string` | (필수) | 타겟의 고유 식별자 및 대시보드 표시 이름 |
| `mode` | `string` | (필수) | `api_query` (API 검색) 또는 `browser_url` (브라우저 스크래핑) |
| `query` | `string` | `null` | `api_query` 모드에서 사용할 검색어 |
| `rank_query` | `string` | `name` | 랭킹 수집 시 사용할 기본 검색어 |
| `rank_query_aliases` | `list[str]` | `[]` | **[NEW]** 랭킹 수집 시 추가로 확장할 별칭 검색어 목록 |
| `category` | `string` | `"기타"` | 대시보드 분류용 카테고리 |
| `url` | `string` | `null` | `browser_url` 모드에서 방문할 직접 URL |
| `fallback_url` | `string` | `null` | `api_query` 결과가 없을 시 대비용 브라우저 URL |

### `match` 서브 섹션
검색 결과 내에서 정확한 제품을 찾기 위한 필터링 옵션입니다.

| 필드명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `required_keywords` | `list[str]` | `[]` | 상품 제목에 반드시 포함되어야 하는 키워드들 |
| `exclude_keywords` | `list[str]` | `[]` | 상품 제목에 포함되면 안 되는 키워드들 |
| `product_id` | `string` | `null` | 네이버 쇼핑 카탈로그 ID (MID) |
| `allowed_product_types` | `list[int]` | `[]` | 허용하는 상품 타입 (1: 카탈로그, 3: 일반상품 등) |
