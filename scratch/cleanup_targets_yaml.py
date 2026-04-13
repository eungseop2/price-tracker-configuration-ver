import yaml
import sys

def cleanup_yaml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading YAML: {e}")
        return

    # 1. Define global excludes (Keep as is)
    global_excludes = ["중고", "리퍼", "커버", "필름", "스킨", "스티커", "케이스", "스트랩"]
    
    if "common" not in data:
        data["common"] = {}
    data["common"]["global_exclude_keywords"] = global_excludes

    # 2. Colors to remove from required_keywords
    colors = [
        "블랙", "화이트", "black", "white", "그라파이트", "실버", "골드", "silver", "gold",
        "그레이", "gray", "grey", "티타늄", "titanium", "옐로우", "yellow", "오렌지", "orange",
        "민트", "mint", "라벤더", "lavender", "핑크", "pink", "레드", "red", "블루", "blue", 
        "그린", "green", "베이지", "beige", "카키", "khaki"
    ]
    
    forbidden_ids = ["R540N", "SM-R540N", "R640", "SM-R640", "R420", "R420N"]

    def optimize_match(config):
        if not config or not isinstance(config, dict):
            return
        
        # Cleanup excludes
        if "exclude_keywords" in config:
            local_excludes = config["exclude_keywords"]
            if local_excludes and isinstance(local_excludes, list):
                config["exclude_keywords"] = [k for k in local_excludes if k not in global_excludes]
        
        # Relax required keywords (remove models and COLORS)
        if "required_keywords" in config:
            reqs = config["required_keywords"]
            if reqs and isinstance(reqs, list):
                new_reqs = [r for r in reqs if r not in colors and r not in forbidden_ids]
                config["required_keywords"] = new_reqs

    # 3. Apply to targets
    if "targets" in data:
        for t in data["targets"]:
            if "match" in t:
                optimize_match(t["match"])

    # 4. Apply to mall_targets
    if "mall_targets" in data:
        for mt in data["mall_targets"]:
            if "exclude_keywords" in mt:
                mt["exclude_keywords"] = [k for k in mt["exclude_keywords"] if k not in global_excludes]

    # 5. Save back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)
        print("Successfully optimized targets.yaml (Removed Colors & Models)")
    except Exception as e:
        print(f"Error saving YAML: {e}")

if __name__ == "__main__":
    cleanup_yaml("targets.yaml")
