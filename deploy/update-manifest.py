"""Regenerate the deployment payload checksums after editing the skill."""
import hashlib
import json
from pathlib import Path
import subprocess

PACKAGE_VERSION = '1.0.0'
FILES = ('SKILL.md', 'references/komiai-api.md', 'scripts/komiai_image.py', 'scripts/mac_keychain.py')


def main():
    deploy = Path(__file__).resolve().parent
    root = deploy.parent
    destination = deploy / 'manifest.json'
    previous = json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else {}
    try:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = previous.get('source_commit')
    manifest = {
        'package_version': PACKAGE_VERSION,
        'source_repository': 'https://github.com/phxD/komiai-imagegen',
        'source_commit': commit,
        'files': {name: hashlib.sha256((root / 'skills/komiai-imagegen' / name).read_bytes()).hexdigest() for name in FILES},
    }
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
