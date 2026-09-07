import json,tempfile,unittest
from brew2port.core import *
from brew2port.definitions import build_definitions, load_definitions
from brew2port.macports import select_asset
class TestCore(unittest.TestCase):
 def test_normalized_and_override(self):
  ports=[{'name':'muse_code'},{'name':'wget'}]
  self.assertEqual(candidates({'name':'muse-code','kind':'formula'},ports)[0]['port'],'muse_code')
  self.assertEqual(candidates({'name':'foo','kind':'formula'},ports,{'foo':None}),[])
 def test_heuristic_rejects_unrelated_names(self):
  ports=[{'name':'qmail-spamcontrol'},{'name':'dnscontrol'},{'name':'gsmartcontrol'}]
  self.assertEqual(candidates({'name':'macs-fan-control','kind':'cask'},ports),[])
  self.assertEqual(candidates({'name':'azcopy','kind':'formula'},[{'name':'R-DNAcopy'}]),[])
 def test_plan(self): self.assertEqual(make_plan([{'name':'wget','kind':'formula'}],[{'name':'wget'}])[0]['candidates'][0]['confidence'],1.0)
 def test_install_defaults_to_dry_run(self):
  result=install([{'homebrew':'wget','candidates':[{'port':'wget','confidence':1.0}]}]); self.assertEqual(result[0]['status'],'dry-run')
 def test_load_json(self):
  with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
   json.dump([{'name':'x'}],f); f.flush(); self.assertEqual(load_ports(f.name)[0]['name'],'x')
 def test_fetch_paginated_api(self):
  class Response:
   def __init__(self,data): self.data=json.dumps(data).encode()
   def __enter__(self): return self
   def __exit__(self,*args): pass
   def read(self): return self.data
  pages=[Response({'results':[{'name':'wget'}],'next':'page2'}),Response({'results':[{'name':'muse_code'}],'next':None})]
  def opener(request): return pages.pop(0)
  self.assertEqual([p['name'] for p in fetch_macports_ports(opener=opener)],['wget','muse_code'])
 def test_select_macos_asset(self):
  asset=select_asset(('15.7',15,'x86_64'),[{'name':'MacPorts-2.12.3-15-Sequoia.pkg'}])
  self.assertEqual(asset['name'],'MacPorts-2.12.3-15-Sequoia.pkg')
 def test_local_macports_ports(self):
  import brew2port.core as core
  old=core.shutil.which; core.shutil.which=lambda name:'/opt/local/bin/port' if name=='port' else old(name)
  try:
   def run(*args,**kwargs): return type('R',(),{'returncode':0,'stdout':'wget\nfoo-bar\n'})()
   self.assertEqual([p['name'] for p in local_macports_ports(run)],['foo-bar','wget'])
  finally: core.shutil.which=old
 def test_update_macports(self):
  import brew2port.core as core
  old=core.shutil.which; core.shutil.which=lambda name:'/opt/local/bin/port'
  try:
   result=update_macports(lambda *args,**kwargs:type('R',(),{'returncode':0})())
   self.assertEqual(result['status'],'updated')
  finally: core.shutil.which=old
 def test_preview_csv(self):
  with tempfile.NamedTemporaryFile(mode='w+',suffix='.csv') as f:
   write_preview_csv([{'kind':'formula','homebrew':'muse-code','candidates':[{'port':'muse_code','confidence':.96,'reason':'normalized name'}]}],f.name)
   f.seek(0); self.assertIn('muse_code',f.read())
 def test_plan_uses_published_definition(self):
  defs={("formula","muse-code"):{'candidates':[{'port':'muse_code','confidence':1.0,'reason':'curated'}]}}
  plan=make_plan([{'name':'muse-code','kind':'formula'}],[],definitions=defs)
  self.assertEqual(plan[0]['source'],'definitions')
  self.assertEqual(plan[0]['candidates'][0]['port'],'muse_code')
 def test_build_definitions_keeps_trusted_matches_only(self):
  data=build_definitions([{'name':'wget'},{'name':'unknown'}],[],[{'name':'wget'}])
  self.assertEqual(data['mapping_count'],1)
  self.assertEqual(data['mappings'][0]['homebrew'],'wget')
 def test_load_definitions_alias(self):
  with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
   json.dump({'mappings':[{'kind':'formula','homebrew':'muse-code','aliases':['muse']} ]},f); f.flush()
   self.assertIn(('formula','muse'),load_definitions(f.name))
