import argparse,json,shutil,sys
from .catalog import fetch,DEFAULT_CACHE,DEFAULT_URL
from .core import inventory,plan,write_csv,install,update_fink,verify

def main():
    parser=argparse.ArgumentParser(prog="brew2fink"); parser.add_argument("--update-fink",action="store_true"); sub=parser.add_subparsers(dest="command")
    sub.add_parser("inventory").add_argument("--output",default="brew-inventory.json")
    item=sub.add_parser("prepare"); item.add_argument("--inventory-output",default="brew-inventory.json"); item.add_argument("--plan-output",default="migration-plan.json"); item.add_argument("--preview-output",default="migration-preview.csv"); item.add_argument("--catalog",default=DEFAULT_CACHE); item.add_argument("--catalog-url",default=DEFAULT_URL); item.add_argument("--refresh-catalog",action="store_true")
    item=sub.add_parser("plan"); item.add_argument("--inventory",required=True); item.add_argument("--output",default="migration-plan.json"); item.add_argument("--catalog",default=DEFAULT_CACHE); item.add_argument("--catalog-url",default=DEFAULT_URL); item.add_argument("--refresh-catalog",action="store_true")
    item=sub.add_parser("migrate"); item.add_argument("--plan",required=True); item.add_argument("--install",action="store_true"); item.add_argument("--yes",action="store_true")
    item=sub.add_parser("verify"); item.add_argument("--plan",required=True)
    sub.add_parser("update-fink")
    args=parser.parse_args()
    if args.command is None:
        if args.update_fink: print(json.dumps(update_fink(),indent=2)); return
        print("""brew2fink — Homebrew to Fink migration assistant

Safe workflow:

  1. Inventory explicitly installed Homebrew packages:
       brew2fink inventory --output brew-inventory.json

  2. Prepare a one-stop dry-run plan and review CSV:
       brew2fink prepare
     This downloads and caches the published macpkg-catalog relationships.
     It never installs Fink packages.

  3. Review migration-preview.csv, then perform the reviewed installation:
       brew2fink migrate --plan migration-plan.json --install
     Add --yes only for unattended execution.

  4. Refresh an existing Fink installation independently:
       brew2fink update-fink

  5. Verify installed Fink packages:
       brew2fink verify --plan migration-plan.json

Near-hits and ambiguous mappings always require review. Homebrew packages are
never removed automatically.
"""); return
    if args.command=="prepare":
        if not shutil.which("fink"): print("Fink is not installed; review the plan, then install Fink before migrating.",file=sys.stderr)
        items=inventory(); open(args.inventory_output,"w").write(json.dumps(items,indent=2)+"\n")
        rows=plan(items,fetch(args.catalog,args.refresh_catalog,args.catalog_url,progress=lambda x:print(x,file=sys.stderr)))
        open(args.plan_output,"w").write(json.dumps(rows,indent=2)+"\n"); write_csv(rows,args.preview_output)
        print(f"Prepared {len(rows)} packages. Review {args.preview_output} before installing.")
    elif args.command=="inventory":
        data=inventory(); open(args.output,"w").write(json.dumps(data,indent=2)+"\n"); print(f"Wrote {args.output}")
    elif args.command=="plan":
        items=json.load(open(args.inventory)); rows=plan(items,fetch(args.catalog,args.refresh_catalog,args.catalog_url,progress=lambda x:print(x,file=sys.stderr))); open(args.output,"w").write(json.dumps(rows,indent=2)+"\n"); write_csv(rows,args.output.replace(".json",".csv")); print(f"Wrote {args.output}")
    elif args.command=="verify":
        print(json.dumps(verify(json.load(open(args.plan))),indent=2))
    elif args.command=="update-fink":
        print(json.dumps(update_fink(),indent=2))
    else:
        rows=json.load(open(args.plan)); apply=args.install and (args.yes or input("Apply reviewed Fink migration? [y/N] ").lower() in ("y","yes")); print(json.dumps(install(rows,apply),indent=2))
