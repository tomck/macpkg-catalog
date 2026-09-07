import argparse,json,sqlite3
from pathlib import Path
from .core import write_sqlite, key
from .pipeline import generate, load_snapshot
from .sources import fetch, fetch_analytics, fetch_live_snapshot
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    for n in ("lookup","relations"):
        x=s.add_parser(n); x.add_argument("manager"); x.add_argument("type"); x.add_argument("name"); x.add_argument("--snapshot",default="dist/catalog.sqlite")
    x=s.add_parser("search"); x.add_argument("text"); x.add_argument("--snapshot",default="dist/catalog.sqlite")
    x=s.add_parser("popularity"); x.add_argument("manager"); x.add_argument("type"); x.add_argument("name"); x.add_argument("--snapshot",default="dist/catalog.json")
    x=s.add_parser("export"); x.add_argument("--output",required=True); x.add_argument("--format",choices=["sqlite"],required=True); x.add_argument("--snapshot",default="dist/catalog.json")
    x=s.add_parser("generate"); x.add_argument("--output",default="dist"); x.add_argument("--refresh",action="store_true"); x.add_argument("--input")
    x=s.add_parser("fetch-live"); x.add_argument("--output",default="snapshots/catalog.json")
    a=p.parse_args()
    if a.cmd=="fetch-live":
        output=Path(a.output); output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(fetch_live_snapshot(),indent=2)+"\n")
        print(f"Wrote {output}"); return
    if a.cmd=="generate":
        if a.refresh: p.error("Full-source refresh is not implemented yet; use --input")
        if not a.input: p.error("Offline generation requires --input")
        generate(a.input,a.output); return
    snapshot_kind={"lookup":"packages","relations":"relations","search":"packages","popularity":"popularity"}.get(a.cmd)
    data=load_snapshot(a.snapshot,snapshot_kind)
    if a.cmd=="export":
        write_sqlite(data["packages"],data["relations"],a.output)
        with sqlite3.connect(a.output) as c:
            c.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
            c.executemany("INSERT INTO metadata VALUES(?,?)", [(k,json.dumps(v)) for k,v in data.items() if k not in {"packages","relations"}])
        return
    if a.cmd=="popularity": result=[r for r in data.get("popularity",[]) if key(r)==(a.manager,a.type,a.name)]
    elif a.cmd=="lookup": result=[r for r in data["packages"] if key(r)==(a.manager,a.type,a.name)]
    elif a.cmd=="relations": result=[r for r in data["relations"] if key(r["source"])==(a.manager,a.type,a.name)]
    else: result=[r for r in data["packages"] if a.text.casefold() in (r["native_name"]+" "+r.get("description","")).casefold()]
    print(json.dumps({"catalog_version":data.get("catalog_version"),"results":result},indent=2))
