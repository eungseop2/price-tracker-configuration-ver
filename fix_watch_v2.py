import re
from pathlib import Path

path = Path('targets.yaml')
# Read with ignore to avoid erroring on leftover corruption
content = path.read_bytes().decode('utf-8', 'ignore')

# 1. Clean up excessive newlines (fix previous script artifacts)
content = re.sub(r'\n{3,}', '\n\n', content)

# 2. Watch restoration mapping
m = {
    '갤럭시?뚯튂8': '갤럭시워치8',
    '媛ㅻ윮?쒖썙移?': '갤럭시워치',
    '洹몃씪?뚯씠??': '그라파이트',
    '?명듃???고??': '울트라',
    '?대옒??': '클래식',
    '?뚯튂8': '워치8',
    '?뚯튂': '워치',
    '以묎퀬': '중고',
    '由ы띁': '리퍼',
    '?꾨쫫': '필름',
    '?ㅽ듃??': '스트랩'
}

for k, v in m.items():
    content = content.replace(k, v)

# 3. Consolidate rank_query for Watch
# Watch 8 variants -> 갤럭시워치8
content = re.sub(r"rank_query:\s*['\"]갤럭시워치8\s*클래식['\"]", "rank_query: '갤럭시워치8'", content)
content = re.sub(r"rank_query:\s*['\"]갤럭시워치8['\"]", "rank_query: '갤럭시워치8'", content)

# Ultra -> 워치울트라
content = re.sub(r"rank_query:\s*['\"]갤럭시워치\s*울트라['\"]", "rank_query: '워치울트라'", content)
content = re.sub(r"rank_query:\s*['\"]울트라['\"]", "rank_query: '워치울트라'", content)

path.write_text(content, encoding='utf-8')
print('Watch labels and ranking keywords fixed successfully in targets.yaml')
