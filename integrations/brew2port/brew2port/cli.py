import argparse,json,urllib.request,logging,sys,subprocess,shutil
from .core import *
from .definitions import (DEFAULT_DEFINITIONS_CACHE, DEFAULT_DEFINITIONS_URL,
                          build_definitions_from_urls, fetch_definitions,
                          load_definitions)
from .macports import setup_macports
from .catalog import fetch_catalog, DEFAULT_CATALOG_CACHE, DEFAULT_CATALOG_URL

def plan_progress(number,total,name):
 width=32; complete=int(width*number/total) if total else width
 bar='='*complete + ' '*(width-complete)
 print(f'\rMatching [{bar}] {number}/{total}: {name[:32]:<32}',end='',file=sys.stderr,flush=True)
 if number==total: print(file=sys.stderr)

def progress_message(message):
 print(message,file=sys.stderr,flush=True)

def local_port_available():
 return bool(shutil.which('port') or __import__('pathlib').Path('/opt/local/bin/port').exists())

def definitions_for(args):
 return fetch_catalog(args.catalog,args.refresh_catalog,args.catalog_url,progress=progress_message)

def main():
 p=argparse.ArgumentParser(prog='brew2port'); p.add_argument('--update-macports',action='store_true',dest='update_macports_global'); s=p.add_subparsers(dest='cmd')
 a=s.add_parser('inventory'); a.add_argument('-o','--output');
 a=s.add_parser('build-index'); a.add_argument('-o','--output',required=True); a.add_argument('--url',default='https://ports.macports.org/api/v1/ports/')
 a=s.add_parser('setup-macports'); a.add_argument('--version'); a.add_argument('--dry-run',action='store_true'); a.add_argument('--skip-update',action='store_true'); a.add_argument('--yes',action='store_true')
 s.add_parser('update-macports')
 a=s.add_parser('build-definitions'); a.add_argument('-o','--output',required=True); a.add_argument('--formulae-url',default='https://formulae.brew.sh/api/formula.json'); a.add_argument('--casks-url',default='https://formulae.brew.sh/api/cask.json'); a.add_argument('--ports'); a.add_argument('--ports-url',default='https://ports.macports.org/api/v1/ports/'); a.add_argument('--cache',default='~/.cache/brew2port/macports-ports.json'); a.add_argument('--refresh-ports',action='store_true'); a.add_argument('--overrides')
 a=s.add_parser('prepare'); a.add_argument('--inventory-output',default='brew-inventory.json'); a.add_argument('--plan-output',default='migration-plan.json'); a.add_argument('--preview-output',default='migration-preview.csv'); a.add_argument('--overrides'); a.add_argument('--cache',default='~/.cache/brew2port/macports-ports.json'); a.add_argument('--ports-url',default='https://ports.macports.org/api/v1/ports/'); a.add_argument('--catalog',default=DEFAULT_CATALOG_CACHE); a.add_argument('--catalog-url',default=DEFAULT_CATALOG_URL); a.add_argument('--refresh-catalog',action='store_true'); a.add_argument('--definitions',default=DEFAULT_DEFINITIONS_CACHE); a.add_argument('--definitions-url',default=DEFAULT_DEFINITIONS_URL); a.add_argument('--refresh-definitions',action='store_true'); a.add_argument('--update-macports',action='store_true'); a.add_argument('--skip-update',action='store_true'); a.add_argument('--yes',action='store_true')
 a=s.add_parser('plan'); a.add_argument('--inventory',required=True); a.add_argument('--ports'); a.add_argument('--ports-url',default='https://ports.macports.org/api/v1/ports/'); a.add_argument('--cache',default='~/.cache/brew2port/macports-ports.json'); a.add_argument('--catalog',default=DEFAULT_CATALOG_CACHE); a.add_argument('--catalog-url',default=DEFAULT_CATALOG_URL); a.add_argument('--refresh-catalog',action='store_true'); a.add_argument('--definitions',default=DEFAULT_DEFINITIONS_CACHE); a.add_argument('--definitions-url',default=DEFAULT_DEFINITIONS_URL); a.add_argument('--refresh-definitions',action='store_true'); a.add_argument('--refresh-ports',action='store_true'); a.add_argument('--update-macports',action='store_true'); a.add_argument('--overrides'); a.add_argument('-o','--output'); a.add_argument('--format',choices=['json','text'],default='json')
 a=s.add_parser('migrate'); a.add_argument('--plan',required=True); a.add_argument('--install',action='store_true'); a.add_argument('--yes',action='store_true'); a.add_argument('-o','--output')
 a=s.add_parser('verify'); a.add_argument('--plan',required=True)
 x=p.parse_args()
 if x.cmd is None and x.update_macports_global:
  print(json.dumps(update_macports(),indent=2)); return
 if x.cmd is None:
  print("""brew2port — Homebrew to MacPorts migration assistant

Safe workflow:

  1. Inventory explicitly installed Homebrew packages:
       brew2port inventory --output brew-inventory.json

  2. brew2port first checks its published definitions database for known mappings.
     Anything not covered there uses MacPorts' local PortIndex automatically when
     `port` is installed. Otherwise it downloads and caches the public catalog.
     Use --update-macports to refresh the local PortIndex first, or --ports FILE
     with plan for an offline/local snapshot.

  3. One-stop preparation (installs/updates MacPorts, inventories Homebrew,
     creates a plan, and writes a CSV review file):
       brew2port prepare
     It does not install migrated ports. After reviewing the CSV, run:
       brew2port migrate --plan migration-plan.json --install

  4. If MacPorts is not installed, bootstrap it explicitly:
       brew2port setup-macports
     To update an existing MacPorts installation independently:
       brew2port update-macports

  5. Generate and review a migration plan:
       brew2port plan --inventory brew-inventory.json \\
         --output migration-plan.json

  6. Preview the migration (dry run):
       brew2port migrate --plan migration-plan.json

  7. Install only after reviewing the preview:
       brew2port migrate --plan migration-plan.json --install

Homebrew packages are never removed automatically.
""")
  return
 if x.cmd=='inventory': data=inventory_from_brew(); out=json.dumps(data,indent=2)
 elif x.cmd=='build-index':
  data=fetch_macports_ports(x.url); out=json.dumps(data,indent=2)
 elif x.cmd=='build-definitions':
  print('Downloading current Homebrew formula and cask metadata...',file=sys.stderr)
  ov=json.load(open(x.overrides)) if x.overrides else {}
  if x.ports:
   print(f'Loading MacPorts catalog from {x.ports}...',file=sys.stderr)
   from .definitions import fetch_json
   formulae=fetch_json(x.formulae_url); casks=fetch_json(x.casks_url); ports=load_ports(x.ports)
   data=__import__('brew2port.definitions',fromlist=['build_definitions']).build_definitions(formulae,casks,ports,ov)
  else:
   print('Downloading/currently refreshing the MacPorts catalog...',file=sys.stderr)
   data=build_definitions_from_urls(x.formulae_url,x.casks_url,x.ports_url,x.cache,x.refresh_ports,ov,progress=progress_message)
  open(x.output,'w').write(json.dumps(data,indent=2)+'\n')
  print(f"Published definitions contain {data['mapping_count']} trusted mappings.",file=sys.stderr)
  out=f'Wrote definitions database to {x.output}'
 elif x.cmd=='setup-macports':
  data=setup_macports(x.version,x.dry_run,x.skip_update,x.yes); out=json.dumps(data,indent=2)
 elif x.cmd=='update-macports':
  data=update_macports(); out=json.dumps(data,indent=2)
 elif x.cmd=='prepare':
  print('Checking for MacPorts...',file=sys.stderr)
  if local_port_available():
   if x.skip_update or not x.update_macports: print('Using the existing MacPorts PortIndex.',file=sys.stderr)
   else: update_macports()
  else:
   print('MacPorts is not installed; bootstrapping it now.',file=sys.stderr)
   setup_macports(skip_update=x.skip_update,yes=x.yes)
  print(f'Writing Homebrew inventory to {x.inventory_output}...',file=sys.stderr)
  items=inventory_from_brew(); open(x.inventory_output,'w').write(json.dumps(items,indent=2)+'\n')
  ov=json.load(open(x.overrides)) if x.overrides else {}
  defs=definitions_for(x)
  known=sum((item['kind'],item['name']) in defs for item in items)
  print(f'Definitions database covers {known} of {len(items)} installed packages.',file=sys.stderr)
  ports=[]
  if known < len(items):
   print('Reading the local MacPorts PortIndex for the remaining packages...',file=sys.stderr)
   ports=local_macports_ports(); print(f'Matching {len(items)-known} packages against {len(ports)} MacPorts ports...',file=sys.stderr)
  else:
   print('All installed packages are covered by the definitions database; local matching is not needed.',file=sys.stderr)
  data=make_plan(items,ports,ov,definitions=defs,progress=plan_progress); open(x.plan_output,'w').write(json.dumps(data,indent=2)+'\n'); write_preview_csv(data,x.preview_output)
  print(f'Wrote migration plan to {x.plan_output} and review CSV to {x.preview_output}.',file=sys.stderr)
  out='Preparation complete. Review '+x.preview_output+' before installing anything.\n\nTo apply the reviewed migration:\n  brew2port migrate --plan '+x.plan_output+' --install\n'
 elif x.cmd=='plan':
  print('Loading Homebrew inventory...',file=sys.stderr)
  items=json.load(open(x.inventory))
  if x.overrides:
   try: ov=json.load(open(x.overrides))
   except FileNotFoundError: p.error(f"overrides file not found: {x.overrides} (omit --overrides or use an absolute path)")
  else: ov={}
  defs=definitions_for(x)
  known=sum((item['kind'],item['name']) in defs for item in items)
  print(f'Definitions database covers {known} of {len(items)} packages.',file=sys.stderr)
  if x.ports:
   print(f'Loading local MacPorts catalog: {x.ports}',file=sys.stderr); ports=load_ports(x.ports)
  elif local_port_available() and known < len(items):
   if x.update_macports:
    print('Updating the local MacPorts PortIndex with port selfupdate...',file=sys.stderr)
    subprocess.run(['sudo','port','selfupdate'],check=True)
   else:
    print("Using MacPorts' local PortIndex (use --update-macports to refresh it).",file=sys.stderr)
   ports=local_macports_ports()
  else:
   if known < len(items):
    ports=cached_macports_ports(x.cache,x.refresh_ports,x.ports_url,progress=progress_message)
   else: ports=[]
  print(f'Matching {len(items)-known} packages not covered by definitions against {len(ports)} MacPorts ports...',file=sys.stderr)
  data=make_plan(items,ports,ov,definitions=defs,progress=plan_progress)
  print(f'Generated migration plan for {len(data)} packages.',file=sys.stderr)
  out=json.dumps(data,indent=2) if x.format=='json' else '\n'.join(f"{r['homebrew']} -> "+(', '.join(f"{c['port']} ({c['confidence']})" for c in r['candidates']) or 'NO MATCH') for r in data)
 elif x.cmd=='migrate':
  install_now=x.install
  if x.install and not x.yes:
   install_now=input('Apply the reviewed migration plan now? [y/N] ').strip().lower() in ('y','yes')
  data=install(json.load(open(x.plan)),install_now); out=json.dumps(data,indent=2)
  if x.install and not install_now: out += "\n\nInstallation cancelled. No packages were changed.\n"
  if not x.install: out += "\n\nDry run complete. No packages were changed.\n\nTo perform the reviewed installation:\n  brew2port migrate --plan " + x.plan + " --install\n"
 else:
  data=json.load(open(x.plan)); out=json.dumps(verify_plan(data),indent=2)
 if getattr(x,'output',None): open(x.output,'w').write(out+'\n')
 else: print(out)
