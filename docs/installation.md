# 安装与部署

## 选择安装位置

| 使用范围 | 目标目录 |
| --- | --- |
| Windows 个人使用 | `%USERPROFILE%\.agents\skills\komiai-imagegen\` |
| macOS 个人使用 | `~/.agents/skills/komiai-imagegen/` |
| 团队项目 | `<项目>/.agents/skills/komiai-imagegen/` |

Codex 会从这些技能目录发现 `SKILL.md`。Windows 和 macOS 均需 Python 3.10 或以上。Windows 的密码输入框需要 Python 的 Tkinter 支持。 [Codex 技能查找规则](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

## 从 GitHub 链接导入

将下面这句话发给 Codex，即可从指定版本导入。

> 用 `$skill-installer` 从 https://github.com/phxD/komiai-imagegen/tree/v0.6.0/skills/komiai-imagegen 安装 KomiAI 生图 Skill。安装到我的个人 `.agents/skills/` 目录。

安装私有仓库需要当前 GitHub 账号拥有访问权限。若 Codex 所用的 Git 环境没有该仓库的访问权限，可以在已登录 GitHub 的浏览器中下载 ZIP。

## 从 ZIP 安装

1. 下载 [最新 ZIP](https://github.com/phxD/komiai-imagegen/releases/latest/download/komiai-imagegen.zip)。需要复现特定版本时，下载 [v0.6.0 的 ZIP](https://github.com/phxD/komiai-imagegen/releases/download/v0.6.0/komiai-imagegen.zip)。
2. 解压并复制整层 `komiai-imagegen` 文件夹到所选的 `.agents/skills/`。安装后，`komiai-imagegen/SKILL.md` 与 `komiai-imagegen/scripts/` 应处于同一层。
3. 用 Codex 打开项目并开始新聊天。若技能列表未刷新，重新打开 Codex，再输入 `$komiai-imagegen`。

## 团队项目部署

在项目仓库中提交 `.agents/skills/komiai-imagegen/`。成员拉取该版本并用 Codex 打开项目后，即可调用同一版本。团队成员第一次用到 Key 时在本机弹窗里填写。Windows 凭据管理器和 macOS 钥匙串按用户管理各自的 Key。

## 更新与卸载

- **更新时**，下载目标版本并整体替换安装位置里的 `komiai-imagegen` 文件夹。v0.6.0 可继续读取 v0.5 保存的 Key。
- **卸载时**，删除对应的 `komiai-imagegen` 文件夹。若需要重走首次提示，也可在系统凭据工具中删除该 Skill 的条目。相关条目名和步骤见 [凭据排错](troubleshooting.md#重新测试首次弹窗)。
