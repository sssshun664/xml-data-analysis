# Pull the embedded collection data back out of the published demo page.
import json, re, sys
html = open(sys.argv[1], encoding='utf-8').read()
m = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
data = json.loads(m.group(1).replace('<\\/', '</'))
json.dump(data, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
for k, c in data.items():
    print(k, c['name'], len(c['papers']), 'papers;', sum(len(p['tables']) for p in c['papers']), 'tables')
