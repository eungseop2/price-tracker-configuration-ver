import yaml

def enhance_targets(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 1. Expand global excludes
    new_excludes = [
        "강화유리", "보호필름", "액정", "유막", "실리콘", "하드", "투명", 
        "액세서리", "악세사리", "거치대", "충전기", "케이블", "어댑터", 
        "펜슬", "펜", "철가루", "방지", "먼지", "청소", "스탠드", 
        "그립톡", "링", "참", "키링", "충전독", "가방", "박스", "패키지", "벌크"
    ]
    current_global = data.get("common", {}).get("global_exclude_keywords", [])
    data["common"]["global_exclude_keywords"] = list(set(current_global + new_excludes))

    # 2. Add min_price to targets
    if "targets" in data:
        for t in data["targets"]:
            name = t.get("name", "")
            cat = t.get("category", "")
            
            # Default min_price by category or name
            min_price = None
            if "버즈" in cat or "버즈" in name:
                min_price = 80000 # 80k KRW for Buds
                if "프로" in name:
                    min_price = 120000 
            elif "워치" in cat or "워치" in name:
                min_price = 150000 # 150k KRW for Watch
                if "울트라" in name:
                    min_price = 450000
                elif "핏" in name or "Fit" in name:
                    min_price = 40000
            
            if min_price:
                if "match" not in t:
                    t["match"] = {}
                t["match"]["min_price"] = min_price

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

if __name__ == "__main__":
    enhance_targets("targets.yaml")
