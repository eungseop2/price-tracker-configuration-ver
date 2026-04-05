# Price Tracker Design System

이 문서는 에이전트가 고품질(Premium) UI를 일관되게 생성할 수 있도록 정의된 프로젝트 전용 디자인 가이드라인입니다.

## 🎨 Color Palette (Zinc-950 System)
Toss 및 Stitch Taste Design의 원칙을 결합하여 깊이감 있는 **Off-black**을 베이스로 사용합니다.

- **Background (Main)**: `#f2f4f6` (Toss Grey)
- **Background (Sidebar)**: `#ffffff`
- **Text (Primary)**: `#191f28` (Zinc-950 스타일 Off-black)
- **Text (Secondary)**: `#4e5968` (Zinc-700 스타일 Grey)
- **Text (Muted)**: `#8b95a1` (Zinc-400 스타일)
- **Accent (Blue)**: `#3182f7` (Toss Blue)
- **Status (Up)**: `#3182f7`
- **Status (Down)**: `#ef4444`

## 🖋️ Typography
전문적이고 미려한 서체 사용을 최우선으로 합니다.

- **Heading**: `Outfit`, sans-serif (Google Fonts)
- **Body**: `Geist`, -apple-system, system-ui, sans-serif (Google Fonts)
- **Data/Monospace**: `Space Mono`, monospace
  - 모든 가격(`curr_price`, `delta`), 상품 번호, 날짜 데이터에 적용합니다.

## 📐 Layout & Components
- **Radius**: 16px ~ 24px (매우 둥근 모서리 적용)
- **Shadows**: 
  - `var(--card-shadow)`: 0 8px 16px -4px rgba(0, 0, 0, 0.04), 0 4px 8px -4px rgba(0, 0, 0, 0.02)
- **Density**: 콤팩트하면서도 여백(White-space)을 넉넉히 활용하여 전문성을 강조합니다.
- **Transitions**: `all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`

## ✨ Micro-interactions
- 모든 버튼 및 카드 호버 시 Subtle Lift 효과 및 배경색 변화 적용.
- 탭 전환 시 상하/좌우 0.3s 부드러운 트래지션 필수.
