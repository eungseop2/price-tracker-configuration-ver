import yaml
import os

# 제외 키워드 리스트 수정 (사용자 요청 반영)
# - 미개봉 제거
# - 강화유리, 스트랩, 케이스 제거
# - 구형 모델명(워치4~6, 버즈2 등) 제거 (1번은 없애고 요청 반영)
KEYWORDS_TO_EXCLUDE = [
    "패키지", "시계줄", "밴드", "충전독", "거치대", "파우치", 
    "스탠드", "스킨", "커버", "필름", "보호막", "어댑터", "젠더", "이어팁", "청소키트", 
    "공구", "헤드폰", "이어캡", "버클", "브레이슬릿", "이용권", "보이스캐디", "증정", 
    "사은품", "학생전용", "쿠폰", "갤럭시S", "S25", "S26", "퀀텀", "버디", "와이드", 
    "갤럭시탭", "탭A", "갤럭시북", "아이폰", "에어팟", "갤럭시핏", "핏3", "핏e", 
    "그랑데AI", "중고", "리퍼", "가개통"
]

def update_targets():
    yaml_path = "targets.yaml"
    if not os.path.exists(yaml_path):
        print(f"Error: {yaml_path} not found")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if "mall_targets" in data:
        for t in data["mall_targets"]:
            # 핵심: 기존 키워드를 완전히 덮어쓰거나, 사용자 요청대로 정제함
            # 여기서는 일관성을 위해 정의된 리스트로 덮어쓰겠습니다.
            t["exclude_keywords"] = sorted(KEYWORDS_TO_EXCLUDE)
            
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    
    print("Successfully re-updated mall_targets exclusion keywords based on user feedback.")

if __name__ == "__main__":
    update_targets()
