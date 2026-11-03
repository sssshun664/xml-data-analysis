# Build a sentence-level co-occurrence knowledge graph from the parsed papers.
import json, re, sys
from collections import defaultdict

SPLIT = r'(?<=[.!?])\s+(?=[A-Z(\[])'   # must match the JS splitter in the page
DOWN = re.compile(r'\b(reduc|decreas|inhibit|suppress|prevent|lower|mitigat|diminish|minimi[sz])', re.I)
UP = re.compile(r'\b(increas|enhanc|improv|higher|rais|promot|elevat|boost)', re.I)
OWN = {'results', 'discussion', 'conclusion'}

ENT = {
 'mab': {
  'types': [['exc', '添加剤・緩衝液'], ['stress', 'ストレス・工程'], ['attr', '品質特性'], ['method', '評価・解析手法']],
  'ents': [
   ['arginine', 'アルギニン', 'exc', r'\barginine\b|\bl-?Arg\b|Arg·HCl|Arg-HCl'],
   ['glycine', 'グリシン', 'exc', r'\bglycine\b'],
   ['histidine', 'ヒスチジン', 'exc', r'\bhistidine\b'],
   ['proline', 'プロリン', 'exc', r'\bproline\b'],
   ['sucrose', 'ショ糖', 'exc', r'\bsucrose\b'],
   ['trehalose', 'トレハロース', 'exc', r'\btrehalose\b'],
   ['mannitol', 'マンニトール', 'exc', r'\bmannitol\b'],
   ['sorbitol', 'ソルビトール', 'exc', r'\bsorbitol\b'],
   ['polysorbate', 'ポリソルベート', 'exc', r'polysorbate|\bPS ?(20|80)\b|\bTween'],
   ['cyclodextrin', 'シクロデキストリン', 'exc', r'cyclodextrin|HPβCD|HP-β-CD|KLEPTOSE'],
   ['ectoine', 'エクトイン', 'exc', r'\bectoine\b'],
   ['nacl', '塩化ナトリウム', 'exc', r'\bNaCl\b|sodium chloride'],
   ['citrate', 'クエン酸', 'exc', r'\bcitrat|\bcitric'],
   ['phosphate', 'リン酸緩衝液', 'exc', r'phosphate buffer|sodium phosphate|\bPBS\b'],
   ['heat', '熱ストレス', 'stress', r'thermal stress|heat stress|elevated temperature|accelerated (stability|condition|storage)|high temperature'],
   ['agitation', '撹拌', 'stress', r'\bagitat|\bshaking\b|\bstirr'],
   ['freezethaw', '凍結融解', 'stress', r'freeze[- –]thaw'],
   ['light', '光照射', 'stress', r'light exposure|light stress|\bphoto(degrad|stab|-?induced|oxid)|\bUV\b'],
   ['lowph', '低pH', 'stress', r'\blow pH\b|acidic|virus inactivation'],
   ['interface', '界面（気液・油）', 'stress', r'\binterfac|air[- –](liquid|water)'],
   ['highconc', '高濃度', 'stress', r'high[- ]concentration|highly concentrated'],
   ['lyo', '凍結乾燥', 'stress', r'lyophili[sz]|freeze[- ]dr'],
   ['aggregation', '凝集', 'attr', r'\baggregat'],
   ['viscosity', '粘度', 'attr', r'\bviscosit'],
   ['tm', '熱安定性（Tm）', 'attr', r'\bT ?m\d?\b|melting temperature|thermal stability|\bunfolding'],
   ['monomer', '単量体の減少・保持', 'attr', r'monomer (loss|retention|content|purity)'],
   ['fragment', '断片化', 'attr', r'\bfragmentation|\bclipping'],
   ['particles', '微粒子', 'attr', r'subvisible|visible particle|\bparticulate'],
   ['chem', '化学的変化（脱アミド等）', 'attr', r'deamidat|glycat|isomeri[sz]|\boxidation\b'],
   ['colloidal', 'コロイド安定性・自己会合', 'attr', r'colloidal|self-associat|\bkD\b|\bB22\b'],
   ['sec', 'SEC', 'method', r'\bSEC\b|size[- ]exclusion'],
   ['dls', 'DLS', 'method', r'\bDLS\b|dynamic light scattering'],
   ['dsf', 'DSF・nanoDSF', 'method', r'\bDSF\b|nanoDSF|differential scanning fluorimetry'],
   ['dsc', 'DSC', 'method', r'\bDSC\b|differential scanning calorimetry'],
   ['md', '分子動力学', 'method', r'molecular dynamics|\bMD simulation'],
   ['ml', '機械学習', 'method', r'machine learning|deep learning|neural network|Bayesian optimi'],
   ['ms', '質量分析', 'method', r'mass spectrometr|LC-MS'],
  ],
  'rows': ['exc'], 'cols': ['attr', 'stress']},
 'pla': {
  'types': [['add', '添加剤・ブレンド'], ['proc', '加工・処理'], ['prop', '物性'], ['method', '評価手法']],
  'ents': [
   ['na', '核剤（一般）', 'add', r'nucleating agent|nucleator'],
   ['talc', 'タルク', 'add', r'\btalc\b'],
   ['tmc', 'TMC系核剤', 'add', r'\bTMC'],
   ['sc', 'PDLA・ステレオコンプレックス', 'add', r'\bPDLA\b|stereo-?complex'],
   ['cnt', 'カーボンナノチューブ', 'add', r'nanotube|\bMWCNT|\bCNTs?\b'],
   ['graphene', 'グラフェン', 'add', r'graphene'],
   ['cellulose', 'セルロース', 'add', r'cellulose|\bNCC\b|\bCNC\b'],
   ['natfiber', '天然繊維・植物系フィラー', 'add', r'\bhemp\b|\bkenaf\b|\bjute\b|\bflax\b|natural fib|bamboo|bagasse|Poaceae|coffee|horsetail|pineapple|yeast'],
   ['biochar', 'バイオ炭', 'add', r'biochar'],
   ['silica', 'シリカ', 'add', r'\bsilica\b|\bSiO2\b'],
   ['peg', '可塑剤・PEG', 'add', r'plasticiz|plasticis|\bPEG\b|poly\(ethylene glycol\)'],
   ['pbs', 'PBS', 'add', r'\bPBS\b|poly\(butylene succinate\)'],
   ['pcl', 'PCL', 'add', r'\bPCL\b|polycaprolactone'],
   ['phb', 'PHB・PHBV', 'add', r'\bPHBV?\b|polyhydroxy'],
   ['lignin', 'リグニン', 'add', r'lignin'],
   ['ha', 'ハイドロキシアパタイト', 'add', r'hydroxyapatite'],
   ['silicone', 'シリコーン', 'add', r'silicone|siloxane'],
   ['anneal', 'アニール・熱処理', 'proc', r'anneal|heat[- ]treat|thermal treatment|post-?process'],
   ['injection', '射出成形', 'proc', r'injection[- ]mo(u)?ld'],
   ['moldtemp', '金型温度', 'proc', r'mo(u)?ld temperature'],
   ['print3d', '3Dプリント', 'proc', r'3D[- ]print|\bFDM\b|fused (deposition|filament)|additive manufactur'],
   ['extrusion', '押出', 'proc', r'\bextru'],
   ['recycle', '再加工・リサイクル', 'proc', r'recycl|reprocess|multiple processing'],
   ['hdt', 'HDT', 'prop', r'\bHDT\b|heat (deflection|distortion)'],
   ['vicat', 'ビカット軟化温度', 'prop', r'Vicat|\bVST\b'],
   ['xc', '結晶化度', 'prop', r'crystallinity|degree of crystalli|\bX ?c\b'],
   ['crate', '結晶化温度・速度', 'prop', r'crystalli[sz]ation (rate|kinetic|temperature|half)|cold crystalli|\bT ?cc?\b'],
   ['tg', 'ガラス転移温度', 'prop', r'glass transition|\bT ?g\b'],
   ['tensile', '引張特性', 'prop', r'\btensile'],
   ['impact', '衝撃強度', 'prop', r'impact (strength|resistance)|\bnotched'],
   ['thermstab', '熱分解・熱安定性', 'prop', r'thermal (stability|degradation|decomposition)'],
   ['biodeg', '生分解性', 'prop', r'biodegrad'],
   ['dsc', 'DSC', 'method', r'\bDSC\b|differential scanning calorimetry'],
   ['xrd', 'XRD', 'method', r'\bXRD\b|X-ray diffraction|\bWAXD\b|\bWAXS\b'],
   ['pom', '偏光顕微鏡', 'method', r'\bPOM\b|polari[sz]ed optical'],
   ['dma', 'DMA', 'method', r'\bDMA\b|dynamic mechanical'],
   ['tga', 'TGA', 'method', r'\bTGA\b|thermogravimetr'],
   ['ftir', 'FTIR', 'method', r'\bFTIR\b|FT-IR'],
  ],
  'rows': ['add', 'proc'], 'cols': ['prop']},
}

def compile_pat(pat):
    # Case-insensitive overall; acronym branches (2+ capitals, e.g. SEC, NaCl) stay case-sensitive.
    parts, depth, cur = [], 0, ''
    for ch in pat:
        if ch == '(': depth += 1
        if ch == ')': depth -= 1
        if ch == '|' and depth == 0: parts.append(cur); cur = ''; continue
        cur += ch
    parts.append(cur)
    out = ['(?-i:%s)' % x if len(re.findall(r'[A-Z]', x.replace('\\b', ''))) >= 2 else x for x in parts]
    return re.compile('|'.join(out), re.I)

def build(key, papers):
    spec = ENT[key]
    ents = [(e[0], e[1], e[2], compile_pat(e[3])) for e in spec['ents']]
    edges = defaultdict(list); node_papers = defaultdict(set); node_sents = defaultdict(int)
    for pi, p in enumerate(papers):
        units = [('abstract', 'a%d' % i, t) for i, t in enumerate(p['abstract'])]
        for si, s in enumerate(p['sections']):
            units += [(s['cat'], 's%dp%d' % (si, k), t) for k, t in enumerate(s['paras'])]
        for cat, loc, text in units:
            for xi, sent in enumerate(re.split(SPLIT, text)):
                hit = [e for e in ents if e[3].search(sent)]
                for e in hit: node_papers[e[0]].add(pi); node_sents[e[0]] += 1
                if len(hit) < 2: continue
                d, u = bool(DOWN.search(sent)), bool(UP.search(sent))
                pol = -1 if d and not u else (1 if u and not d else 0)
                for i in range(len(hit)):
                    for j in range(i + 1, len(hit)):
                        a, b = sorted([hit[i][0], hit[j][0]])
                        edges[(a, b)].append([pi, loc, xi, cat, pol])
    nodes = [{'id': e[0], 'label': e[1], 'type': e[2], 'papers': len(node_papers[e[0]]), 'sents': node_sents[e[0]]} for e in ents if node_papers[e[0]]]
    E = []
    for (a, b), ev in edges.items():
        ps = {x[0] for x in ev}; own = {x[0] for x in ev if x[3] in OWN}
        E.append({'a': a, 'b': b, 'papers': len(ps), 'own': len(own), 'ev': ev})
    E.sort(key=lambda e: -e['papers'])
    return {'types': spec['types'], 'rows': spec['rows'], 'cols': spec['cols'], 'nodes': nodes, 'edges': E}

data = json.load(open(sys.argv[1], encoding='utf-8'))
out = {k: build(k, data[k]['papers']) for k in data}
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for k, g in out.items():
    lab = {n['id']: n['label'] for n in g['nodes']}
    print(k, len(g['nodes']), 'nodes', len(g['edges']), 'edges', sum(len(e['ev']) for e in g['edges']), 'evidence')
    for e in g['edges'][:12]: print('  ', lab[e['a']], '—', lab[e['b']], e['papers'], 'papers, own', e['own'])
