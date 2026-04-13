import yaml
import sys

def cleanup_yaml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading YAML: {e}")
        return

    # 1. Define global excludes
    global_excludes = ["중고", "리퍼", "커버", "필름", "스킨", "스티커", "케이스", "스트랩"]
    
    if "common" not in data:
        data["common"] = {}
    
    # Store global list
    data["common"]["global_exclude_keywords"] = global_excludes

    # 2. Cleanup function
    def optimize_match(config):
        if not config or not isinstance(config, dict):
            return
        
        # Cleanup excludes
        if "exclude_keywords" in config:
            local_excludes = config["exclude_keywords"]
            if local_excludes and isinstance(local_excludes, list):
                new_local = [k for k in local_excludes if k not in global_excludes]
                config["exclude_keywords"] = new_local
        
        # Relax required keywords (remove models and colors per user feedback)
        if "required_keywords" in config:
            reqs = config["required_keywords"]
            if reqs and isinstance(reqs, list):
                # Remove strict identifiers and color names
                forbidden = ["R540N", "SM-R540N", "R640", "SM-R640", "R420", "R420N", 
                             "블랙", "화이트", "black", "white", "그라파이트", "실버", "골드"]
                new_reqs = [r for r in reqs if r not in forbidden]
                config["required_keywords"] = new_reqs

    # 3. Apply to targets
    if "targets" in data:
        for t in data["targets"]:
            if "match" in t:
                optimize_match(t["match"])

    # 4. Apply to mall_targets
    if "mall_targets" in data:
        for mt in data["mall_targets"]:
            # Mall targets have exclude_keywords at the top level in some schemas, 
            # or inside a 'match' if it followed the same structure. 
            # Looking at config.py, MallTargetConfig has exclude_keywords directly.
            if "exclude_keywords" in mt:
                local_excludes = mt["exclude_keywords"]
                if local_excludes and isinstance(local_excludes, list):
                    mt["exclude_keywords"] = [k for k in local_excludes if k not in global_excludes]

    # 5. Save back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)
        print("Successfully optimized targets.yaml")
    except Exception as e:
        print(f"Error saving YAML: {e}")

if __name__ == "__main__":
    cleanup_yaml("targets.yaml")
