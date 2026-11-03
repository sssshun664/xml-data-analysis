# Search Europe PMC and download full-text JATS XML.
#   search: python3 -I build/scripts/fetch_europepmc.py search '<query>' [page size]
#   fetch:  python3 -I build/scripts/fetch_europepmc.py fetch <out dir> PMC123 PMC456 ...
import json, os, sys, time, urllib.parse, urllib.request

API = "https://www.ebi.ac.uk/europepmc/webservices/rest"

def search(q, n):
    url = API + "/search?" + urllib.parse.urlencode({"query": q, "format": "json", "pageSize": n, "resultType": "core"})
    d = json.load(urllib.request.urlopen(url, timeout=60))
    print("hits:", d["hitCount"], file=sys.stderr)
    for r in d["resultList"]["result"]:
        print(r.get("pmcid"), r.get("pubYear"), r.get("license"), "|", r.get("journalInfo", {}).get("journal", {}).get("medlineAbbreviation"), "|", r["title"][:100])

def fetch(out, ids):
    os.makedirs(out, exist_ok=True)
    for pmc in ids:
        p = os.path.join(out, pmc + ".xml")
        if os.path.exists(p): continue
        try:
            data = urllib.request.urlopen(f"{API}/{pmc}/fullTextXML", timeout=60).read()
            open(p, "wb").write(data); print(pmc, len(data))
        except Exception as e:
            print(pmc, "ERR", e)
        time.sleep(0.2)

if __name__ == "__main__":
    if sys.argv[1] == "search": search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 50)
    elif sys.argv[1] == "fetch": fetch(sys.argv[2], sys.argv[3:])
