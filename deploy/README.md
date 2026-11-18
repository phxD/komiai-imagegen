# KomiAI 设计团队部署

适用于已经安装并登录 Codex 的 Mac、Windows 同事。无需手动准备 Python 或复制 skill。

## 发给同事的这一段

复制以下内容到 Codex 新对话：

> 请读取 https://github.com/phxD/komiai-imagegen/blob/main/deploy/README.md ，按文档为我的电脑安装 KomiAI 生图工具。自动识别 macOS 或 Windows，配置 Python 独立环境并安装个人 skill。Key 只在本机密码窗口输入；只检查环境，不提交生图任务。

Codex 执行部署时可能需要你允许下载和写入个人目录。首次使用的 KomiAI Key 在本机隐藏输入窗口填写，不要发送到对话或群里。

## 给执行安装的 Codex

1. 读取本目录下的脚本，获取完整仓库内容到本机临时目录。优先使用 Git；没有 Git 时使用 GitHub 仓库 ZIP，不必单独安装 Git。不要只下载单个部署脚本，因为安装器需要同一版本的 `deploy/manifest.json` 和 `skills/komiai-imagegen/`。使用 ZIP 时，入口为 https://github.com/phxD/komiai-imagegen/archive/refs/heads/main.zip 。
2. 识别操作系统。macOS 在仓库根目录运行 `bash deploy/Install-Mac.command`；Windows 在仓库根目录运行 `powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\deploy\install-windows.ps1`。Windows 的执行策略参数只作用于本次进程；受管电脑上的组织策略仍以本机实际限制为准。
3. 脚本使用官方 uv 安装入口和 Python 3.12，为当前用户创建独立环境、校验并安装本仓库 skill、配置本机解释器路径。无需安装 Homebrew、修改系统 Python 或设置全局 PATH。
4. 已有可读取的 Key 会继续使用；缺少 Key 时，安装器调用 skill 自带的本机密码窗口，保存到 macOS 钥匙串或 Windows 凭据管理器。用户取消时保留已安装环境，状态记录为 `installed_key_pending`，如实报告尚未配置 Key。
5. 只检查 Python、标准库、脚本入口以及 Key 能否读取，不提交实际出图请求。检查当前用户目录下 `.agents/komiai-install-logs/latest.json`：`ready` 表示环境与凭据读取检查通过；`installed_key_pending` 表示环境就绪但 Key 待配置；`failed` 表示需要根据日志排查。`ready` 不代表已验证平台权限、额度或真实出图。
6. 安装后告知用户：在 Codex 新对话输入 `$komiai-imagegen` 和图片需求。若当前会话没有刷新技能列表，可读取已安装的 `SKILL.md` 使用；不要声称在未读取安装结果时已经安装成功。

若下载、写入或系统凭据访问被当前会话拒绝，遵守实际权限，不要改用其他执行通道绕过。解释被限制的具体步骤，并在可以授权时使用正常权限流程；否则请用户在本机运行同一份脚本，再读取结果继续验收。不要读取、输出或收集用户的 Key。

## 手动双击入口

从 GitHub 下载完整仓库 ZIP 并解压：

- **Mac**：双击 `deploy/Install-Mac.command`。首次若被 macOS 拦截，按本机允许的方式右键选择“打开”。
- **Windows**：双击 `deploy/Install-Windows.cmd`。必须先完整解压；不要在 ZIP 预览窗口里运行。

首次安装需联网访问 `astral.sh` 和 GitHub。实际生图使用 `api.komiai.cn`。安装脚本不携带任何团队成员的 Key，也不自动验证账户额度或产生出图费用。

## 更新、备份与排错

再次运行安装器会部署该次获取的仓库版本，并复用正常的独立 Python 环境。若要升级，请先重新获取仓库版本。覆盖现有 skill 前会保留旧目录；文件替换失败时恢复旧版。

| 内容 | 当前用户目录内的路径 |
| --- | --- |
| Skill | `.agents/skills/komiai-imagegen/` |
| 独立环境 | `.agents/komiai-runtime/python312/` |
| 旧版备份 | `.agents/komiai-backups/` |
| 结果和日志 | `.agents/komiai-install-logs/` |

Mac 当前用户目录通常为 `~`；Windows 为 `%USERPROFILE%`。日志及 `latest.json` 不记录 Key。下载或安装失败时，保留日志再重试；没有收到完成结果时不要声称安装成功。

## 维护者

Skill 文件清单在 `manifest.json`，安装前校验 SHA-256。修改 `skills/komiai-imagegen/` 后，运行 `python3 deploy/update-manifest.py` 更新清单，并将二者一起提交。部署器版本在该脚本中的 `PACKAGE_VERSION` 管理；更新运行方式时同时更新说明。

运行部署测试：`python3.12 -m unittest discover -s deploy/tests -v`。测试使用临时用户目录，不读取真实 Key，不生成收费图片。存在 uv 时还会测试独立环境的创建与复用。

Mac 上已验证真实 skill 的 Python 环境、钥匙串存取及 1024×1024 出图；团队部署逻辑另做隔离测试。Windows 入口已完成代码检查，尚待真实 Windows 电脑端到端试装。批量发放前请先选一位 Windows 同事验收。
