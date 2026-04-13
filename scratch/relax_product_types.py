import yaml

def relax_product_types(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if "targets" in data:
        for t in data["targets"]:
            if "match" in t:
                # Always ensure 1, 2, 3 are allowed to include all merchant listings
                if "allowed_product_types" in t["match"]:
                    t["match"]["allowed_product_types"] = [1, 2, 3]
                else:
                    # If not present, the default is usually everything, but we can set it explicitly
                    t["match"]["allowed_product_types"] = [1, 2, 3]

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

if __name__ == "__main__":
    relax_product_types("targets.yaml")
