"""Launch the cloned React CRM on loopback. Does not move or sync CRM data."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import re
import time
import urllib.error
import urllib.request
import webbrowser

BASE=Path(__file__).resolve().parent
REPO=BASE/'legacy'/'virtuo-ai-os'
URL='http://127.0.0.1:5178'
NODE=Path(r'C:\nvm4w\nodejs\node.exe')
RUNTIME=BASE/'.react-runtime'


def ready():
    try:
        with urllib.request.urlopen(URL+'/auth',timeout=8) as response:
            return response.status==200 and 'text/html' in response.headers.get('Content-Type','') and b'jarvis' in response.read(200000).lower()
    except (urllib.error.URLError,TimeoutError,OSError):return False


def open_ui(minimized=False):
    for browser in [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')]:
        if browser.is_file():
            args=[str(browser),'--app='+URL]
            if minimized:args.append('--start-minimized')
            subprocess.Popen(args,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return
    webbrowser.open(URL)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--startup',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--serve-only',action='store_true');args=parser.parse_args()
    if args.check:
        print('React CRM auth route ready' if ready() else 'React CRM not responding');return
    if not ready():
        vite=REPO/'node_modules'/'vite'/'bin'/'vite.js'
        if not NODE.is_file() or not vite.is_file():raise RuntimeError('React CRM dependencies are missing. See REACT_INTERFACE_README.md.')
        RUNTIME.mkdir(exist_ok=True)
        env=os.environ.copy()
        config=REPO/'.env'
        if config.is_file():
            for line in config.read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                key,value=line.split('=',1);key=key.strip();value=value.strip()
                if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',key):env[key]=value.strip(chr(34)+chr(39))
        with (RUNTIME/'server.log').open('ab') as output:
            process=subprocess.Popen([str(NODE),str(vite),'--host','127.0.0.1','--port','5178','--strictPort'],cwd=REPO,env=env,stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (RUNTIME/'server.json').write_text(json.dumps({'pid':process.pid,'url':URL,'repository':str(REPO)}),encoding='utf-8')
        deadline=time.monotonic()+240
        while not ready():
            if process.poll() is not None:raise RuntimeError('React CRM server exited. See .react-runtime/server.log.')
            if time.monotonic()>deadline:raise RuntimeError('React CRM did not become ready. See .react-runtime/server.log.')
            time.sleep(1)
    if args.serve_only:
        print("React CRM auth route verified at "+URL+"/auth");return
    open_ui(args.startup)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # No credentials or request bodies in launcher errors.
        if '--serve-only' in sys.argv or '--check' in sys.argv:
            print(str(exc));raise SystemExit(1)
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,str(exc),'JARVIS React CRM launcher',0x10)
