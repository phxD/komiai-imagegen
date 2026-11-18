"""Install the bundled KomiAI skill for the current macOS or Windows user."""

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime


REQUIRED = {
    'SKILL.md', 'scripts/komiai_image.py', 'scripts/mac_keychain.py',
    'references/komiai-api.md',
}


def check_bundle(bundle):
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    if set(manifest['files']) != REQUIRED:
        raise RuntimeError('安装包文件清单不完整，请重新获取完整安装包。')
    payload = bundle.parent / 'skills' / 'komiai-imagegen'
    for relative, digest in manifest['files'].items():
        path = payload / relative
        parts = PurePosixPath(relative)
        if parts.is_absolute() or '..' in parts.parts or path.is_symlink():
            raise RuntimeError('安装包路径检查失败。')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'安装包文件损坏：{relative}。请重新解压。')
    return manifest


def run_checked(command, log):
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    for output in (result.stdout, result.stderr):
        if output.strip():
            log.info(output.strip())
    if result.returncode:
        raise RuntimeError(f'环境检查失败（退出码 {result.returncode}），详情见日志。')
    return result


def runtime_python(runtime, platform):
    return runtime / ('Scripts/python.exe' if platform == 'win32' else 'bin/python')


def prepare_runtime(home, uv, platform, log):
    runtime = home / '.agents' / 'komiai-runtime' / 'python312'
    interpreter = runtime_python(runtime, platform)
    check = 'import sys, ssl, ctypes; assert sys.version_info[:2] == (3, 12); print(sys.version)'
    if interpreter.is_file():
        result = subprocess.run([str(interpreter), '-c', check], capture_output=True)
        if result.returncode:
            raise RuntimeError(f'已有环境需要修复，请将此路径交给管理员检查：{runtime}')
    elif runtime.exists():
        raise RuntimeError(f'发现不完整环境，请将此路径交给管理员检查：{runtime}')
    else:
        runtime.parent.mkdir(parents=True, exist_ok=True)
        run_checked([str(uv), '--no-config', 'venv', '--python', sys.executable, str(runtime)], log)
    run_checked([str(interpreter), '-c', check], log)
    if platform == 'win32':
        run_checked([str(interpreter), '-c', 'import tkinter; t=tkinter.Tcl(); print("Tk/Tcl:", t.eval("info patchlevel"))'], log)
    return interpreter


def install_payload(bundle, home, interpreter, manifest):
    skill_root = home / '.agents' / 'skills'
    skill_root.mkdir(parents=True, exist_ok=True)
    target = skill_root / 'komiai-imagegen'
    if target.is_symlink():
        raise RuntimeError('目标 skill 是符号链接，请先由管理员确认安装位置。')
    if target.exists():
        header = (target / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[1]
        if not any(line.strip().strip('"\'') == 'komiai-imagegen'
                   for line in [s.partition(':')[2].strip() for s in header.splitlines() if s.startswith('name:')]):
            raise RuntimeError('目标目录存在其他内容，已停止覆盖。')
    stage = Path(tempfile.mkdtemp(prefix='komiai-install-', dir=skill_root))
    staged_skill = stage / 'komiai-imagegen'
    backup = None
    try:
        staged_skill.mkdir()
        for relative in manifest['files']:
            destination = staged_skill / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundle.parent / 'skills' / 'komiai-imagegen' / relative, destination)
        skill_md = staged_skill / 'SKILL.md'
        content = skill_md.read_text(encoding='utf-8')
        heading = '# KomiAI 生图\n'
        if content.count(heading) != 1:
            raise RuntimeError('无法定位 skill 运行说明。')
        note = ('\n## 本机 Python 环境\n\n'
                f'此电脑已安装独立运行环境。所有子命令必须使用 `{interpreter}` '
                '作为 Python 解释器；脚本使用本 Skill 中 `scripts/komiai_image.py` 的实际路径。'
                '在 Windows PowerShell 中运行带引号的解释器路径时，使用调用运算符 `&`。'
                '从用户项目目录运行，保持用户要求的输出目录。\n')
        skill_md.write_text(content.replace(heading, heading + note, 1), encoding='utf-8')
        (staged_skill / 'team-install.json').write_text(json.dumps({
            'package_version': manifest['package_version'],
            'source_commit': manifest['source_commit'],
            'python': str(interpreter),
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        if target.exists():
            backup_root = home / '.agents' / 'komiai-backups'
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
            target.rename(backup)
        try:
            staged_skill.rename(target)
        except BaseException:
            if backup is not None and not target.exists():
                backup.rename(target)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return target, backup


def configure_credentials(interpreter, target, log):
    code = ('import sys; sys.path.insert(0, sys.argv[1]); '
            'from komiai_image import get_api_key; get_api_key(False); print("credential_ready")')
    check = [str(interpreter), '-c', code, str(target / 'scripts')]
    if subprocess.run(check, capture_output=True).returncode == 0:
        log.info('已找到可读取的 KomiAI Key。')
        return True
    log.info('请在本机弹出的密码窗口填写自己的 KomiAI Key；取消可稍后配置。')
    result = subprocess.run([str(interpreter), str(target / 'scripts' / 'komiai_image.py'), 'configure-key'])
    if result.returncode != 0:
        log.info('环境已安装，Key 尚未配置。首次生图时会再次提示。')
        return False
    if subprocess.run(check, capture_output=True).returncode != 0:
        raise RuntimeError('Key 保存后无法读取。请保留日志并联系管理员。')
    log.info('Key 保存和读取检查通过；尚未提交生图任务。')
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description='KomiAI designer installation')
    parser.add_argument('--uv', type=Path, required=True)
    args = parser.parse_args(argv)
    if sys.platform not in ('darwin', 'win32') or sys.version_info[:2] != (3, 12):
        parser.error('此安装器需要 macOS / Windows 和 Python 3.12。')
    home = Path.home()
    log_root = home / '.agents' / 'komiai-install-logs'
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / ('install-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.log')
    log = logging.getLogger('komiai-team-installer')
    log.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    log.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    log.addHandler(console_handler)
    state = {'status': 'failed', 'log': str(log_path)}
    try:
        log.info('KomiAI 设计师安装：环境检查不会产生生图费用。')
        bundle = Path(__file__).resolve().parent
        manifest = check_bundle(bundle)
        interpreter = prepare_runtime(home, args.uv, sys.platform, log)
        # Verify the bundled application before replacing any installed version.
        run_checked([str(interpreter), str(bundle.parent / 'skills/komiai-imagegen/scripts/komiai_image.py'), '--help'], log)
        target, backup = install_payload(bundle, home, interpreter, manifest)
        log.info('Skill 已安装：%s', target)
        if backup:
            log.info('旧版备份：%s', backup)
        ready = configure_credentials(interpreter, target, log)
        state.update(status='ready' if ready else 'installed_key_pending',
                     skill=str(target), python=str(interpreter),
                     package_version=manifest['package_version'], credential_ready=ready)
        log.info('安装完成。请在 Codex 新对话中输入 $komiai-imagegen 和图片需求。')
        log.info('提示：安装检查未验证 Key 的平台权限或额度；首次实际出图会使用 KomiAI 额度。')
        return 0
    except (Exception, KeyboardInterrupt) as error:
        log.error('安装未完成：%s', error or '用户已中断。')
        return 1
    finally:
        (log_root / 'latest.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        log.info('排错日志：%s', log_path)
        file_handler.close()
        log.removeHandler(file_handler)
        log.removeHandler(console_handler)
        console_handler.close()


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
