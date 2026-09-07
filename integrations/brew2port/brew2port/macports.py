import hashlib, json, platform, shutil, subprocess, tempfile
import urllib.request
from pathlib import Path

RELEASES_URL = 'https://api.github.com/repos/macports/macports-base/releases'
OS_NAMES = {
    26: 'Tahoe', 15: 'Sequoia', 14: 'Sonoma', 13: 'Ventura', 12: 'Monterey',
    11: 'BigSur', 10: 'Catalina',
}

def macos_release(run=subprocess.run):
    result=run(['sw_vers','-productVersion'],capture_output=True,text=True,check=True)
    version=result.stdout.strip()
    return version, int(version.split('.')[0]), platform.machine()

def select_asset(release, assets):
    _, major, _=release
    name=OS_NAMES.get(major)
    if not name: raise RuntimeError('No known MacPorts installer mapping for macOS '+str(major))
    expected=f'-{major}-{name}.pkg'.lower()
    matches=[a for a in assets if a.get('name','').lower().endswith(expected)]
    if not matches:
        raise RuntimeError(f'No MacPorts installer was published for macOS {major} ({name})')
    return matches[0]

def release_info(version=None, opener=urllib.request.urlopen):
    url=RELEASES_URL+'/tags/v'+version if version else RELEASES_URL+'/latest'
    request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'brew2port'})
    with opener(request) as response: return json.loads(response.read().decode())

def download_and_hash(asset, path, opener=urllib.request.urlopen):
    request=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'brew2port'})
    digest=hashlib.sha256()
    with opener(request) as response, open(path,'wb') as output:
        while True:
            chunk=response.read(1024*1024)
            if not chunk: break
            digest.update(chunk); output.write(chunk)
    return digest.hexdigest()

def setup_macports(version=None, dry_run=False, skip_update=False, yes=False,
                   run=subprocess.run, opener=urllib.request.urlopen, input_fn=input):
    if shutil.which('port'):
        return {'status':'already-installed','message':'MacPorts is already installed.'}
    release=macos_release(run); info=release_info(version,opener); asset=select_asset(release,info.get('assets',[]))
    pkg=Path.home()/'.cache'/'brew2port'/'macports'/asset['name']
    command=['sudo','installer','-pkg',str(pkg),'-target','/']
    print(f"MacPorts {info.get('tag_name','').lstrip('v')} installer: {asset['name']}")
    print('This will install MacPorts under /opt/local and require administrator authorization.')
    if dry_run: return {'status':'dry-run','asset':asset['name'],'command':command}
    if not yes and input_fn('Proceed with MacPorts installation? [y/N] ').strip().lower() not in ('y','yes'):
        return {'status':'cancelled'}
    cache=pkg.parent
    cache.mkdir(parents=True,exist_ok=True)
    actual=download_and_hash(asset,pkg,opener)
    expected=(asset.get('digest') or '').removeprefix('sha256:')
    if expected and actual != expected: raise RuntimeError(f'Installer checksum mismatch: expected {expected}, got {actual}')
    signature=run(['pkgutil','--check-signature',str(pkg)],capture_output=True,text=True)
    if signature.returncode != 0: raise RuntimeError('MacPorts installer signature validation failed')
    installed=run(['sudo','installer','-pkg',str(pkg),'-target','/'])
    if installed.returncode != 0: raise RuntimeError(f'MacPorts installer failed with exit code {installed.returncode}')
    port='/opt/local/bin/port'
    check=run([port,'version'],capture_output=True,text=True)
    if check.returncode != 0: raise RuntimeError('MacPorts installed, but /opt/local/bin/port did not verify')
    if not skip_update: run(['sudo',port,'selfupdate'],check=True)
    return {'status':'installed','version':check.stdout.strip(),'installer':str(pkg),'updated':not skip_update}
