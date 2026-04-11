import re
from pathlib import Path

path = Path('targets.yaml')
text = path.read_text(encoding='utf-8')

# 1. Clean up extra newlines (mishap from previous script)
text = re.sub(r'\n\s*\n', '\n', text)

# 2. Fix Watch garbled strings
repls = {
    '갤럭시?뚯튂8': '갤럭시워치8',
    '媛ㅻ윮?쒖썙移?: '갤럭시워치',
    '?대옒??: '클래식',
    '洹몃씪?뚯씠??': '그라파이트',
    '?명듃???고??': '울트라',
    '?뚯튂8': '워치8',
    '?뚯튂': '워치',
    '以묎퀬': '중고',
    '由ы띁': '리퍼',
    '而ㅻ쾭': '커버',
    '?꾨쫫': '필름',
    '?ㅽ궓': '스킨',
    '?ㅽ떚而?': '스티커',
    '?ㅽ듃??': '스트랩'
}

for k, v in repls.items():
    text = text.replace(k, v)

# 3. Specific rank_query fixes for Watch
# Watch 8 -> 갤러시워치8
text = re.sub(r"rank_query:\s*['\"]?갤럭시워치8\s*클래식['\"]?", "rank_query: '갤럭시워치8'", text)
text = text.replace("rank_query: '갤럭시워치8'", "rank_query: '갤럭시워치8'") # No-op just to be sure

# Watch Ultra -> 워치울트라
text = text.replace("rank_query: '갤럭시워치 울트라'", "rank_query: '워치울트라'")
text = text.replace("rank_query: '워치 울트라'", "rank_query: '워치울트라'")

path.write_text(text, encoding='utf-8')
print('Successfully fixed Galaxy Watch labels and cleaned targets.yaml')
