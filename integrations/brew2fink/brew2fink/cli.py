import argparse,json,shutil,sys
from .catalog import fetch,DEFAULT_CACHE,DEFAULT_URL
from .core import inventory,plan,write_csv,install

def main():
    parser=argparse.ArgumentParser(prog="brew2fink"); sub=parser.add_subparsers(dest="command",required=True)
    item=sub.add_parser("prepare"); item.add_argument("--inventory-output",default="brew-inventory.json"); item.add_argument("--plan-output",default="migration-plan.json"); item.add_argument("--preview-output",default="migration-preview.csv"); item.add_argument("--catalog",default=DEFAULT_CACHE); item.add_argument("--catalog-url",default=DEFAULT_URL); item.add_argument("--refresh-catalog",action="store_true")
    item=sub.add_parser("migrate"); item.add_argument("--plan",required=True); item.add_argument("--install",action="store_true"); item.add_argument("--yes",action="store_true")
    args=parser.parse_args()
    if args.command=="prepare":
        if not shutil.which("fink"): print("Fink is not installed; review the plan, then install Fink before migrating.",file=sys.stderr)
        items=inventory(); open(args.inventory_output,"w").write(json.dumps(items,indent=2)+"\n")
        rows=plan(items,fetch(args.catalog,args.refresh_catalog,args.catalog_url,progress=lambda x:print(x,file=sys.stderr)))
        open(args.plan_output,"w").write(json.dumps(rows,indent=2)+"\n"); write_csv(rows,args.preview_output)
        print(f"Prepared {len(rows)} packages. Review {args.preview_output} before installing.")
    else:
        rows=json.load(open(args.plan)); apply=args.install and (args.yes or input("Apply reviewed Fink migration? [y/N] ").lower() in ("y","yes")); print(json.dumps(install(rows,apply),indent=2))
