# 常见问题

## Codex 找不到 Skill

确认文件夹放在个人或项目的 `.agents/skills/` 下。入口文件的完整相对路径应是 `.agents/skills/komiai-imagegen/SKILL.md`。如果下载的是 GitHub 源码归档，从归档的 `skills/` 中复制整个 `komiai-imagegen` 文件夹。重新打开 Codex，再在新聊天输入 `$komiai-imagegen`。

## 缺少 Key 或密码窗口打不开

- 首次调用缺少 Key 时，密码窗口会出现在本机桌面。找到标题为「KomiAI API Key」的窗口，输入后点「保存」。
- Windows 需要当前本机用户能访问自己的凭据管理器，密码窗口还需要 Python 的 Tkinter 支持。
- macOS 使用系统隐藏输入窗口。若系统询问当前 Python 是否可以读取钥匙串，由用户在系统窗口中决定。
- 无桌面会话，或运行环境无法打开窗口时，可把 `KOMIAI_API_KEY` 注入运行环境。Key 只应填写在本机密码框、系统凭据工具或目标运行环境的密钥设置中。

## 更换 Key 或收到 401

在 Codex 输入「`$komiai-imagegen` 更新我的 Key」，或运行 `configure-key`。该操作会替换系统凭据中该 Skill 的 Key。若运行环境还配置了 `KOMIAI_API_KEY`，同步修改那个配置，因为环境变量优先。

## 任务等待超时或结果下载失败

保留任务 ID 和原输出目录，用同一个账号执行 `resume`。遇到提交结果不明且只有请求编号时，先核对 KomiAI 的调用记录。提交使用相同的 `request_id` 时，KomiAI 可能返回重复请求，并且该响应未必包含原任务 ID。

## 重新测试首次弹窗

在 Windows 凭据管理器或 macOS 钥匙串中查找 `KomiAI.CodexImageGen/api.komiai.cn`。macOS 条目的账户名为 `KOMIAI_API_KEY`。删除这一条保存的凭据后，确认测试会话没有注入 `KOMIAI_API_KEY`，再运行一次生图。

## 验证范围

Windows 已完成 KomiAI 实际出图和本机凭据读取验证。首次弹窗后保存并继续、下一次自动复用已通过模拟测试。macOS 的隐藏输入、钥匙串读取、保存和更换也已通过模拟测试，仍需在实际 Mac 上确认系统授权及端到端出图。
