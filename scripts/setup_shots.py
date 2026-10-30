"""Explicit optional installation; normal rendering never installs or downloads packages."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',help='Existing compatible headless Chrome; otherwise download through Remotion')
    args=parser.parse_args();folder=ROOT/'shot_renderer'
    node=os.environ.get('SELF_MEDIA_SHOT_NODE') or shutil.which('node')
    npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
    if not node or not npm:raise SystemExit('Node.js and npm are required; install a supported Node runtime first')
    env=dict(os.environ)
    if args.browser:
        browser=Path(args.browser).resolve()
        if not browser.is_file():raise SystemExit('Browser executable does not exist')
        env['SELF_MEDIA_SHOT_BROWSER']=str(browser)
    subprocess.run([npm,'ci','--no-audit','--no-fund'],cwd=folder,env=env,check=True,timeout=900)
    subprocess.run([node,'browser.mjs'],cwd=folder,env=env,check=True,timeout=600)
    print(json.dumps({'installed':True,'directory':str(folder),'node':node,
        'license':'Remotion separate terms apply; see docs/shot-library.md'},ensure_ascii=False))


if __name__=='__main__':main()
