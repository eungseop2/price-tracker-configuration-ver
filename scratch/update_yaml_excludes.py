import yaml
import os

KEYWORDS_TO_EXCLUDE = [
    "강화유리", "패키지", "스트랩", "시계줄", "밴드", "충전독", "거치대", "케이스", "파우치", 
    "스탠드", "스킨", "커버", "필름", "보호막", "어댑터", "젠더", "이어팁", "청소키트", 
    "공구", "헤드폰", "이어캡", "버클", "브레이슬릿", "이용권", "보이스캐디", "증정", 
    "사은품", "학생전용", "쿠폰", "갤럭시S", "S25", "S26", "퀀텀", "버디", "와이드", 
    "갤럭시탭", "탭A", "갤럭시북", "아이폰", "에어팟", "갤럭시핏", "핏3", "핏e", 
    "그랑데AI", "중고", "리퍼", "가개통", "미개봉", 
    "워치4", "워치5", "워치6", "워치3", "액티브", "기어", "버즈2", "버즈+", "버즈라이브"
]

def update_targets():
    yaml_path = r"c:\Users\youn1\바탕 화면\최저가 config\targets.yaml"
    if not os.path.exists(yaml_path):
        print(f"Error: {yaml_path} not found")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if "mall_targets" in data:
        for t in data["mall_targets"]:
            if "exclude_keywords" not in t:
                t["exclude_keywords"] = []
            
            # 기존 키워드에 새 키워드 합치기 (중복 제거)
            existing = set(t["exclude_keywords"])
            for k in KEYWORDS_TO_EXCLUDE:
                existing.add(k)
            t["exclude_keywords"] = sorted(list(existing))
            
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    
    print("Successfully updated mall_targets exclusion keywords.")

if __name__ == "__main__":
    update_targets()
