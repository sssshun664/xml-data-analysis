# Parse a folder of JATS XML files into the paper records the demo uses.
# usage: python3 -I build/scripts/parse_jats.py <xml dir> <out.json>
import json, os, re, sys
import xml.etree.ElementTree as ET

def ln(t): return t.rsplit('}', 1)[-1] if isinstance(t, str) else ''
SKIP = {'table-wrap', 'fig', 'disp-formula', 'table-wrap-foot', 'supplementary-material', 'graphic'}

def text(el, skip=SKIP):
    out = []
    def walk(e):
        n = ln(e.tag)
        if n in skip:
            if n == 'disp-formula': out.append(' [式] ')
            if e.tail: out.append(e.tail)
            return
        if n == 'math':
            out.append(''.join(e.itertext()).strip())
            if e.tail: out.append(e.tail)
            return
        if e.text: out.append(e.text)
        for c in e: walk(c)
        if e.tail: out.append(e.tail)
    walk(el)
    s = ''.join(out[:-1] if el.tail and out and out[-1] == el.tail else out)
    return re.sub(r'\s+', ' ', s).strip()

def find(el, name):
    for e in el.iter():
        if ln(e.tag) == name: return e
def findall(el, name): return [e for e in el.iter() if ln(e.tag) == name]
def child(el, name): return [c for c in el if ln(c.tag) == name]

def classify(title, stype):
    t = (stype or '') + ' ' + (title or '').lower()
    if re.search(r'intro|background', t): return 'intro'
    if re.search(r'method|material|experimental|procedure', t): return 'methods'
    if re.search(r'result', t): return 'results'
    if re.search(r'discussion', t): return 'discussion'
    if re.search(r'conclu|summary', t): return 'conclusion'
    return None

def parse(path):
    raw = open(path, 'rb').read()
    root = ET.fromstring(raw)
    rawtxt = raw.decode('utf-8', 'replace')
    am = find(root, 'article-meta'); jm = find(root, 'journal-meta')
    title = text(find(am, 'article-title'))
    jt = find(jm, 'journal-title'); journal = text(jt) if jt is not None else ''
    pub = find(jm, 'publisher-name'); publisher = text(pub) if pub is not None else ''
    ids = {e.get('pub-id-type'): (e.text or '').strip() for e in findall(am, 'article-id')}
    year = ''
    for pd in findall(am, 'pub-date'):
        y = find(pd, 'year')
        if y is not None: year = y.text.strip(); break
    authors = []
    for cg in findall(am, 'contrib-group'):
        if cg.get('content-type') in ('editor', 'reviewer'): continue
        for c in child(cg, 'contrib'):
            if c.get('contrib-type') in (None, 'author'):
                s = find(c, 'surname'); g = find(c, 'given-names')
                if s is not None: authors.append(((s.text or '') + ' ' + ((g.text or '')[:1] if g is not None else '')).strip())
    lic = {'url': '', 'text': ''}
    perm = find(am, 'permissions')
    if perm is not None:
        L = find(perm, 'license')
        if L is not None:
            lic['url'] = L.get('{http://www.w3.org/1999/xlink}href') or ''
            lr = find(L, 'license_ref')
            if lr is not None and not lic['url']: lic['url'] = (lr.text or '').strip()
            lp = find(L, 'license-p')
            if lp is not None: lic['text'] = text(lp)[:300]
        if not lic['url']:
            m = re.search(r'creativecommons\.org/licenses/[a-z\-]+/[0-9.]+/?', ET.tostring(perm, encoding='unicode'))
            if m: lic['url'] = 'https://' + m.group(0)
        cs = find(perm, 'copyright-statement')
        lic['copyright'] = text(cs) if cs is not None else ''
    kw = [text(k) for k in findall(am, 'kwd')][:12]
    abstract = []
    ab = find(am, 'abstract')
    if ab is not None:
        ps = findall(ab, 'p')
        abstract = [text(p) for p in ps] if ps else [text(ab)]
    sections = []
    body = find(root, 'body')
    def walk(sec, level, inherited):
        tnode = child(sec, 'title')
        st = text(tnode[0]) if tnode else ''
        cat = classify(st, sec.get('sec-type')) or inherited
        paras = [p for p in (text(p) for p in child(sec, 'p')) if p]
        sections.append({'title': st, 'level': level, 'cat': cat or 'other', 'paras': paras})
        for c in child(sec, 'sec'): walk(c, level + 1, cat)
    if body is not None:
        top_p = [text(p) for p in child(body, 'p')]
        if any(top_p): sections.append({'title': '', 'level': 1, 'cat': 'other', 'paras': [p for p in top_p if p]})
        for s in child(body, 'sec'): walk(s, 1, None)
    tables = []
    for tw in findall(root, 'table-wrap'):
        lab = find(tw, 'label'); cap = find(tw, 'caption'); tbl = find(tw, 'table')
        if tbl is None: continue
        head, rows = [], []
        thead = find(tbl, 'thead')
        head_trs = set(id(tr) for tr in findall(thead, 'tr')) if thead is not None else set()
        for tr in findall(tbl, 'tr'):
            cells = []
            for c in tr:
                if ln(c.tag) not in ('th', 'td'): continue
                span = int(c.get('colspan') or 1)
                # header cells repeat across their span; data cells keep the value once
                cells.extend([text(c)] + [''] * (span - 1) if ln(c.tag) == 'td' else [text(c)] * span)
            is_head = id(tr) in head_trs if head_trs else (not rows and all(ln(c.tag) == 'th' for c in tr if ln(c.tag) in ('th', 'td')))
            (head if is_head else rows).append(cells)
        tid = tw.get('id') or ''
        m = re.search(r'<table-wrap[^>]*id="%s".*?</table-wrap>' % re.escape(tid), rawtxt, re.S) if tid else None
        tables.append({'id': tid, 'label': text(lab) if lab is not None else '', 'caption': text(cap) if cap is not None else '',
                       'head': head[:3], 'rows': rows[:60], 'raw': (m.group(0) if m else '')[:3500]})
    figs = []
    for f in findall(root, 'fig'):
        lab = find(f, 'label'); cap = find(f, 'caption')
        figs.append({'label': text(lab) if lab is not None else '', 'caption': (text(cap) if cap is not None else '')[:600]})
    return {'id': ids.get('pmcid') or os.path.basename(path)[:-4], 'doi': ids.get('doi', ''), 'title': title, 'journal': journal,
            'publisher': publisher, 'year': year, 'authors': authors[:3] + (['et al.'] if len(authors) > 3 else []),
            'license': lic, 'kwd': kw, 'abstract': abstract, 'sections': sections, 'tables': tables, 'figs': figs, 'refs': len(findall(root, 'ref'))}

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    papers = []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.xml'): continue
        try:
            p = parse(os.path.join(src, fn))
            if not p['id'].startswith('PMC'): p['id'] = 'PMC' + p['id'] if p['id'].isdigit() else fn[:-4]
            papers.append(p)
        except Exception as e:
            print('ERR', fn, e, file=sys.stderr)
    json.dump(papers, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(papers), 'papers ->', out)
