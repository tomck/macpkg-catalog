import csv,json,shutil,subprocess
from pathlib import Path

def inventory(run=subprocess.run):
    data=json.loads(run(["brew","info","--json=v2","--installed"],capture_output=True,text=True,check=True).stdout)
    rows=[]
    for formula in data.get("formulae",[]):
        if any(x.get("installed_on_request") for x in formula.get("installed",[])):
            rows.append({"kind":"formula","name":formula.get("name") or formula.get("full_name")})
    rows.extend({"kind":"cask","name":c.get("token") or c.get("name")} for c in data.get("casks",[]))
    return rows

def plan(items,catalog):
    return [{"kind":item["kind"],"homebrew":item["name"],"candidates":catalog.get((item["kind"],item["name"]),[])} for item in items]

def write_csv(rows,path):
    with open(path,"w",newline="") as stream:
        writer=csv.writer(stream); writer.writerow(["kind","homebrew","recommended_fink","confidence","reason","review_status"])
        for row in rows:
            choice=(row["candidates"] or [{}])[0]
            writer.writerow([row["kind"],row["homebrew"],choice.get("package",""),choice.get("confidence",""),choice.get("reason",""),"recommended" if choice.get("status")=="automatic" else "needs-review"])

def install(rows,apply=False,run=subprocess.run):
    result=[]
    for row in rows:
        choice=(row["candidates"] or [{}])[0]
        safe=choice.get("status")=="automatic" and choice.get("confidence",0)>=.9 and choice.get("package")
        if not safe: result.append({**row,"status":"needs-review"}); continue
        command=["fink","install",choice["package"]]
        if not apply: result.append({**row,"status":"dry-run","command":command}); continue
        outcome=run(command); result.append({**row,"status":"installed" if outcome.returncode==0 else "failed","command":command})
    return result
