import csv, json, re, subprocess, difflib, urllib.request
from urllib.parse import urljoin
from pathlib import Path
import shutil

def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())

def tokens(s):
    """Return meaningful name tokens for conservative heuristic matching."""
    return [x for x in re.split(r'[^a-z0-9]+', s.lower()) if x]

def heuristic_score(homebrew, port, kind='formula'):
    """Score only evidence-bearing similarities; reject arbitrary name lookalikes."""
    homebrew_norm, port_norm = norm(homebrew), norm(port)
    if not homebrew_norm or not port_norm:
        return None
    # A cask is an application bundle while a port is a source package. Without
    # explicit metadata, spelling alone is too weak to infer equivalence.
    if kind == 'cask':
        return None
    shorter, longer = sorted((homebrew_norm, port_norm), key=len)
    if len(shorter) >= 4 and shorter in longer:
        return .86, 'shared package stem'
    homebrew_tokens, port_tokens = set(tokens(homebrew)), set(tokens(port))
    shared = homebrew_tokens & port_tokens
    if shared and max(map(len, shared)) >= 4:
        coverage = max(len(token) for token in shared) / max(len(shorter), 1)
        return round(.68 + min(coverage, .28), 3), 'shared name token'
    return None

def inventory_from_brew(run=subprocess.run):
    p=run(['brew','info','--json=v2','--installed'],capture_output=True,text=True,check=True)
    data=json.loads(p.stdout); out=[]
    for f in data.get('formulae',[]):
        installed=f.get('installed',[]); requested=any(x.get('installed_on_request') for x in installed)
        if requested: out.append({'kind':'formula','name':f.get('name') or f.get('full_name'),'full_name':f.get('full_name')})
    for c in data.get('casks',[]): out.append({'kind':'cask','name':c.get('token') or c.get('name'),'full_name':c.get('full_name')})
    return out

def load_ports(path):
    text=Path(path).read_text();
    try:
        x=json.loads(text); return x if isinstance(x,list) else x.get('ports',[])
    except json.JSONDecodeError: pass
    rows=[]; lines=[x for x in text.splitlines() if x.strip()]
    if lines and ('\t' in lines[0] or ',' in lines[0]):
        dialect=csv.Sniffer().sniff(lines[0]); rows=list(csv.DictReader(lines,dialect=dialect))
    else:
        for line in lines:
            name=line.split()[0]; rows.append({'name':name,'description':line[len(name):].strip()})
    return rows

def fetch_macports_ports(url='https://ports.macports.org/api/v1/ports/', opener=urllib.request.urlopen, progress=None):
    """Fetch the public MacPorts port catalog, following API pagination."""
    rows=[]; next_url=url; pages=0
    while next_url:
        pages += 1
        if pages > 5000: raise RuntimeError('MacPorts API pagination exceeded safety limit')
        if progress: progress(f'Fetching MacPorts catalog page {pages}...')
        request=urllib.request.Request(next_url,headers={'User-Agent':'brew2port/'+__import__('brew2port').__version__})
        with opener(request) as response: payload=json.loads(response.read().decode())
        if isinstance(payload,list): page=payload; next_url=None
        else:
            page=payload.get('results',payload.get('ports',[]))
            next_url=urljoin(next_url,payload.get('next')) if payload.get('next') else None
        for port in page:
            if isinstance(port,dict):
                if isinstance(port.get('port'),dict): port={**port['port'],**port}
                name=port.get('name') or port.get('portname') or port.get('port')
                if name: rows.append({**port,'name':name})
    return rows

def cached_macports_ports(cache_path, refresh=False, url='https://ports.macports.org/api/v1/ports/', progress=None):
    path=Path(cache_path).expanduser()
    if path.exists() and not refresh:
        if progress: progress(f'Using cached MacPorts catalog: {path}')
        return load_ports(path)
    if progress: progress('No usable cached MacPorts catalog found; downloading a fresh copy...')
    rows=fetch_macports_ports(url,progress=progress)
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(rows,indent=2)+'\n')
    if progress: progress(f'Cached {len(rows)} MacPorts ports at {path}')
    return rows

def local_macports_ports(run=subprocess.run):
    """Read port names from MacPorts' already-maintained local PortIndex."""
    port=shutil.which('port') or ('/opt/local/bin/port' if Path('/opt/local/bin/port').exists() else None)
    if not port:
        raise RuntimeError('MacPorts is not installed')
    result=run([port,'-q','echo','all'],capture_output=True,text=True)
    if result.returncode != 0: raise RuntimeError('Unable to read the local MacPorts PortIndex')
    names=[]
    for line in result.stdout.splitlines():
        name=line.strip()
        if name and re.fullmatch(r'[A-Za-z0-9+_.-]+',name): names.append(name)
    if not names: raise RuntimeError('MacPorts returned an empty local PortIndex')
    return [{'name':name} for name in sorted(set(names))]

def update_macports(run=subprocess.run):
    """Refresh MacPorts base and its local ports tree."""
    port=shutil.which('port') or ('/opt/local/bin/port' if Path('/opt/local/bin/port').exists() else None)
    if not port: raise RuntimeError('MacPorts is not installed; run brew2port setup-macports first')
    result=run(['sudo',port,'selfupdate'])
    if result.returncode != 0: raise RuntimeError(f'MacPorts selfupdate failed with exit code {result.returncode}')
    return {'status':'updated','command':['sudo',port,'selfupdate']}

def candidates(item, ports, overrides=None, index=None):
    overrides=overrides or {}; name=item['name']
    if name in overrides: return [dict(overrides[name],port=overrides[name].get('port'))] if overrides[name] else []
    if index is None:
        index={'exact':{},'normalized':{},'aliases':{},'names':[],
               'normalized_names':[],'by_name':{}}
        for port in ports:
            port_name=port.get('name') or port.get('port')
            if not port_name: continue
            index['names'].append(port_name); index['normalized_names'].append(norm(port_name)); index['by_name'][port_name]=port
            index['exact'].setdefault(port_name,[]).append(port); index['normalized'].setdefault(norm(port_name),[]).append(port)
            for value in re.split(r'[,\s]+',' '.join(str(port.get(k,'')) for k in ('aliases','provides','replaces','conflicts'))):
                if value: index['aliases'].setdefault(norm(value),[]).append(port)
    pool=index['exact'].get(name,[]) or index['normalized'].get(norm(name),[])
    if not pool:
        pool=index['aliases'].get(norm(name),[])
        if not pool:
            close=difflib.get_close_matches(norm(name),index['normalized_names'],n=5,cutoff=.55)
            for close_name in close: pool.extend(index['normalized'].get(close_name,[]))
    scored=[]
    for p in pool:
        pn=p.get('name') or p.get('port'); aliases=' '.join(str(p.get(k,'')) for k in ('aliases','provides','replaces','conflicts'))
        score=0; reason='heuristic'
        if pn==name: score,reason=1.0,'exact name'
        elif norm(pn)==norm(name): score,reason=.96,'normalized name'
        elif norm(name) in [norm(a) for a in re.split(r'[,\s]+',aliases) if a]: score,reason=.92,'alias/provides/replaces'
        else:
            heuristic=heuristic_score(name,pn,item.get('kind','formula'))
            if not heuristic: continue
            score,reason=heuristic
        if score>=.55: scored.append({'port':pn,'confidence':round(score,3),'reason':reason})
    return sorted(scored,key=lambda x:x['confidence'],reverse=True)[:5]

def make_plan(items,ports=None,overrides=None,definitions=None,progress=None):
    ports = ports or []
    definitions = definitions or {}
    index={'exact':{},'normalized':{},'aliases':{},'names':[],'normalized_names':[],'by_name':{}}
    for port in ports:
        name=port.get('name') or port.get('port')
        if not name: continue
        index['names'].append(name); index['normalized_names'].append(norm(name)); index['by_name'][name]=port
        index['exact'].setdefault(name,[]).append(port); index['normalized'].setdefault(norm(name),[]).append(port)
        for value in re.split(r'[,\s]+',' '.join(str(port.get(k,'')) for k in ('aliases','provides','replaces','conflicts'))):
            if value: index['aliases'].setdefault(norm(value),[]).append(port)
    rows=[]
    for number,item in enumerate(items,1):
        key=(item['kind'],item['name'])
        definition=definitions.get(key)
        if definition is not None and item['name'] not in (overrides or {}):
            choices=definition.get('candidates',[])
            source='definitions'
        else:
            choices=candidates(item,ports,overrides,index=index)
            source='curated override' if item['name'] in (overrides or {}) else 'local catalog'
        row={'kind':item['kind'],'homebrew':item['name'],'candidates':choices,'source':source}
        if progress: progress(number,len(items),item['name'])
        rows.append(row)
    return rows

def write_preview_csv(plan, path):
    with open(path,'w',newline='') as output:
        writer=csv.writer(output)
        writer.writerow(['kind','homebrew','recommended_port','confidence','reason','alternatives','review_status'])
        for row in plan:
            choices=row.get('candidates',[])
            recommended=choices[0] if choices else {}
            confident=bool(choices and choices[0].get('confidence',0)>=.8 and (len(choices)==1 or choices[0].get('confidence',0)-choices[1].get('confidence',0)>=.08))
            writer.writerow([row.get('kind',''),row.get('homebrew',''),recommended.get('port',''),recommended.get('confidence',''),recommended.get('reason',''),'; '.join(c.get('port','') for c in choices[1:]),'recommended' if confident else 'needs-review'])

def install(plan, yes=False, run=subprocess.run, log=None):
    results=[]
    for row in plan:
        cs=row['candidates']; chosen=cs[0] if cs and cs[0]['confidence']>=.8 and (len(cs)==1 or cs[0]['confidence']-cs[1]['confidence']>=.08) else None
        if not chosen: results.append({**row,'status':'needs-review'}); continue
        cmd=['sudo','port','install',chosen['port']]
        if not yes: results.append({**row,'status':'dry-run','command':cmd}); continue
        r=run(cmd); results.append({**row,'status':'installed' if r.returncode==0 else 'failed','command':cmd})
    return results

def verify_plan(plan, run=subprocess.run):
    out=[]
    for row in plan:
        port=row.get('port') or (row.get('candidates') or [{}])[0].get('port')
        if not port: out.append({'homebrew':row['homebrew'],'port':None,'verified':False,'reason':'no mapping'}); continue
        r=run(['port','installed',port],capture_output=True,text=True)
        out.append({'homebrew':row['homebrew'],'port':port,'verified':r.returncode==0 and port in r.stdout})
    return out
