#!/bin/bash
set -Eeuo pipefail
umask 077
bundle_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
log_dir="$HOME/.agents/komiai-install-logs"
mkdir -p "$log_dir"
exec > >(tee -a "$log_dir/bootstrap-mac.log") 2>&1
finish() {
  result=$?
  if [ "$result" -ne 0 ]; then
    echo "安装未完成。请将 $log_dir/bootstrap-mac.log 发给管理员排查。"
  fi
  if [ -t 0 ]; then read -r -p "按回车关闭窗口。" ignored || true; fi
}
trap finish EXIT
if [ "$(uname -s)" != Darwin ]; then echo "请在 Mac 上运行此入口。"; exit 1; fi
echo "KomiAI 安装：首次需要联网下载 Python，请稍候。"
task_uv="$HOME/.local/bin/uv"
if [ ! -x "$task_uv" ]; then
  temp_dir="$(mktemp -d)"
  /usr/bin/curl --fail --show-error --location --retry 2 --connect-timeout 20 --max-time 180 --proto '=https' --tlsv1.2 https://astral.sh/uv/0.13.9/install.sh -o "$temp_dir/install-uv.sh"
  UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 /bin/sh "$temp_dir/install-uv.sh"
  rm -rf -- "$temp_dir"
fi
"$task_uv" --no-config python install 3.12
task_python="$("$task_uv" --no-config python find --managed-python 3.12)"
"$task_python" "$bundle_dir/setup.py" --uv "$task_uv"
