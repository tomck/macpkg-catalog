import json, urllib.request
SOURCES={'formula':'https://formulae.brew.sh/api/formula.json','cask':'https://formulae.brew.sh/api/cask.json'}
def fetch(kind):
    with urllib.request.urlopen(SOURCES[kind],timeout=60) as r: data=json.load(r)
    out=[]
    for x in data:
        out.append({'manager':'homebrew','package_type':kind,'native_name':x.get('name',''),'aliases':x.get('aliases',[]),'description':x.get('desc',''),'homepage':x.get('homepage',''),'upstream':x.get('head',{}).get('url','') if isinstance(x.get('head'),dict) else '','version':(x.get('versions') or {}).get('stable',''),'revision':'','provides':[],'conflicts':[],'replaces':[],'renamed_by':[],'source_url':SOURCES[kind],'source_revision':'','last_seen':''})
    return out
