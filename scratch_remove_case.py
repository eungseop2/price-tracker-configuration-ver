import os

def main():
    filepath = 'targets.yaml'
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = [line for line in lines if line.strip() != '- 케이스']
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print(f"Removed {len(lines) - len(new_lines)} instances of '- 케이스'")

if __name__ == '__main__':
    main()
