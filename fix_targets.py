import re
from pathlib import Path

path = Path('targets.yaml')
data = path.read_bytes()

# 1. Try to decode
try:
    text = data.decode('cp949')
    print('Decoded as CP949')
except:
    text = data.decode('utf-8', 'ignore')
    print('Decoded as UTF-8 (ignore)')

# 2. Hard replacements for common corruptions
repls = {
    '媛ㅻ윮??': '갤럭시',
    '踰꾩쫰3': '버즈3',
    '踰꾩쫰': '버즈',
    '?꾨줈': '프로',
    '?붿씠??': '화이트',
    '?ㅻ쾭': '실버',
    '踰꾩쫰3FE': '버즈3FE',
    '踰꾩쫰4': '버즈4',
    '荑좏뙜': '쿠팡'
}
for k, v in repls.items():
    text = text.replace(k, v)

# 3. Apply user requested rank_query mappings
# Defaulting most Buzz 3 to '갤럭시버즈3'
text = re.sub(r"rank_query:\s*['\"]?갤럭시\s*버즈3['\"]?", "rank_query: '갤럭시버즈3'", text)

# Tagging specific ones as '우리 버즈3' (Galaxy Buzz 3 White/Silver etc.)
text = text.replace("name: 갤럭시 버즈3 화이트", "name: 갤럭시 버즈3 화이트\n  rank_query: '우리 버즈3'")
text = text.replace("name: 갤럭시 버즈3 실버", "name: 갤럭시 버즈3 실버\n  rank_query: '우리 버즈3'")

# 4. Save
path.write_text(text, encoding='utf-8')
print('Successfully fixed targets.yaml')
