# KomiAI 生图 Skill

在 Codex 里调用 KomiAI 的 `gpt-image-2.5-sunburst-count`。支持文生图、参考图编辑、遮罩局部重绘和按任务 ID 续查。Windows 和 macOS 共用同一个安装包。


## 设计团队一键部署（已安装 Codex）

把下面这段发给每位设计师，让他们粘贴到 Codex：

> 请读取 https://github.com/phxD/komiai-imagegen/blob/main/deploy/README.md ，按文档为我的电脑安装 KomiAI 生图工具。自动识别 macOS 或 Windows，配置 Python 独立环境并安装个人 skill。Key 只在本机密码窗口输入；只检查环境，不提交生图任务。

部署入口、权限提示、更新与排错见 [团队部署说明](deploy/README.md)。首次安装需要联网，Key 由每位同事单独配置。

## 下载与安装

需要 Codex、Python 3.10 或以上，以及可用于该模型的 KomiAI API Key。

| 安装方式 | 入口 |
| --- | --- |
| 下载最新版本 | [komiai-imagegen.zip](https://github.com/phxD/komiai-imagegen/releases/latest/download/komiai-imagegen.zip) |
| 固定版本 v0.6.0 | [发布说明和安装包](https://github.com/phxD/komiai-imagegen/releases/tag/v0.6.0) |
| 从 GitHub 目录导入 | [技能目录](https://github.com/phxD/komiai-imagegen/tree/v0.6.0/skills/komiai-imagegen) |

解压 ZIP 后，将整个 `komiai-imagegen` 文件夹放进个人目录或团队项目的 `.agents/skills/`。详细路径、GitHub 链接导入和更新步骤见 [安装与部署](docs/installation.md)。下载私有仓库里的文件时，请使用已获访问权限的 GitHub 账号。

## 第一次使用

在 Codex 里可以直接这样输入。

> `$komiai-imagegen` 生成一张 1024×1024 的白底陶瓷咖啡杯产品图，杯把朝右，杯身无文字。

如果还没有 Key，Skill 会自动打开本机密码输入框。输入后点「保存」，当前任务会继续。后续调用会从 Windows 凭据管理器或 macOS 钥匙串读取保存的 Key。已有 `KOMIAI_API_KEY` 环境变量时会优先使用它。

默认生成 **1 张 PNG**，保存到当前项目的 `outputs/komiai/`。生成、改图和续查的示例见 [使用手册](docs/usage.md)。

## 文档

- [安装、更新与卸载](docs/installation.md)
- [使用示例与脚本命令](docs/usage.md)
- [弹窗、凭据与任务排错](docs/troubleshooting.md)
- [KomiAI 接口与参数](skills/komiai-imagegen/references/komiai-api.md)
- [版本记录](CHANGELOG.md)

已在 Windows 实测 KomiAI 出图与凭据读取。macOS 钥匙串、弹窗和更换 Key 的流程已通过模拟测试，实机验收状态见 [排错文档](docs/troubleshooting.md#验证范围)。
