# KomiAI 图片任务

## 团队安装

把整个 `komiai-imagegen` 文件夹放进团队项目的 `.agents/skills/`，用 Codex 打开该项目。也可以放到个人目录的 `.agents/skills/` 供多个项目使用。技能列表未刷新时重启 Codex。参考 [Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)。

安装后可直接在 Codex 输入「`$komiai-imagegen` 生成一张 1024×1024 的极简白底咖啡杯产品图」。首次运行缺少 Key 时，在本机弹窗里输入并点「保存」。Skill 会继续生成图片，后续调用自动读取已保存的 Key。改图时先附上素材，再描述要改的地方。

- **Windows** 使用当前用户的凭据管理器，条目名为 `KomiAI.CodexImageGen/api.komiai.cn`。本机密码窗口需要 Python 自带的 Tkinter。 [微软凭据管理器文档](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw)
- **macOS** 使用当前用户的钥匙串，服务名为 `KomiAI.CodexImageGen/api.komiai.cn`，账户名为 `KOMIAI_API_KEY`。保存和后续调用建议用同一个 Python。若系统显示钥匙串权限提示，由用户决定是否授权。 [Apple 钥匙串文档](https://developer.apple.com/documentation/security/secitemcopymatching(_:_:)) · [macOS 隐藏输入对话框](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/PromptforText.html)

已有环境变量 `KOMIAI_API_KEY` 时优先使用它。在 Windows 上，可以在「编辑账户的环境变量」中添加变量，然后退出并重新打开 Codex。macOS 上，在启动 Codex 或脚本的环境中注入同名变量。需要更换已保存的 Key 时，可在 Codex 输入「`$komiai-imagegen` 更新我的 Key」。

## 接口

平台 API 域名为 `https://api.komiai.cn`。上传、提交和查询使用 `Authorization: Bearer <KOMIAI_API_KEY>`。

| 操作 | 请求 | 结果 |
| --- | --- | --- |
| 文生图 | `POST /tasks/v1/openai/gpt-image-2.5-sunburst-count/text-to-image`，JSON | `data.id` |
| 参考图编辑 | `POST /tasks/v1/openai/gpt-image-2.5-sunburst-count/image-edit`，JSON | `data.id` |
| 上传本地参考图或遮罩 | `POST /tasks/v1/upload`，multipart 字段 `file` | `data.downloadUrl` |
| 查询任务 | `GET /tasks/v1/status/{id}` | `data.status`，完成时有 `data.outputs` |

脚本以异步模式提交，每 4 秒查询一次。`created`、`submitted`、`queued`、`processing` 会继续等待，`completed` 会下载图片，`failed` 和 `canceled` 会停止。平台用 `request_id` 检查同一会员下的重复提交。重复请求会被拒绝，文档未说明会返回第一次提交的任务 ID。

续查使用提交响应的 `data.id` 原值。文档示例使用 `task_` 前缀，实际接口也返回类似 `202611171231_example123` 的 ID。

## 参数

| 命令选项 | 接口字段或行为 | 取值 |
| --- | --- | --- |
| `--prompt-file` | `prompt` | UTF-8 文本文件 |
| `--size` | `size` | `auto`、`1024x1024`、`1536x1024`、`1024x1536`、`2048x2048`、`2048x1152`、`3840x2160`、`2160x3840` |
| `--quality` | `quality` | `auto`、`low`、`medium`、`high` |
| `--n` | `n` | `1` 至 `10`，默认 `1` |
| `--background` | `background` | `auto`、`transparent`、`opaque` |
| `--output-format` | `output_format` | `png`、`jpeg`、`webp`，默认 `png` |
| `--output-compression` | `output_compression` | `0` 至 `100`，用于 JPEG 或 WebP |
| `--moderation` | `moderation` | `auto`、`low` |
| `--reference` / `--reference-file` | `reference_image` | 编辑专用。按顺序传入 1 至 16 张。支持 URL、已有 `file_id` 或本地文件 |
| `--mask` / `--mask-file` | `mask` | 编辑专用。传一个 URL、已有 `file_id` 或本地文件 |
| `--input-fidelity` | `input_fidelity` | 编辑专用。`low` 或 `high` |
| `--request-id` | `request_id` | 调用方自定义去重 ID。省略时由脚本生成 |
| `--out-dir` | 本地目标目录 | 默认 `outputs/komiai` |
| `--timeout` | 等待任务的秒数 | 默认 `600`，超时后可继续查询原任务 |
| `--no-ask-key` | 禁用本机密码输入框 | 用于已注入 Key 的无人值守调用 |

## 调用示例

在以下示例中，将脚本路径换成安装后的位置。先把本次提示词写入 `prompt.txt`。Windows 用 `python`，macOS 通常用 `python3`。

```text
python scripts/komiai_image.py generate --prompt-file prompt.txt --size 2048x1152 --out-dir outputs/komiai
python scripts/komiai_image.py edit --prompt-file prompt.txt --reference-file product.png --input-fidelity high --out-dir outputs/komiai
python scripts/komiai_image.py resume --task-id task_a1b2c3d4 --out-dir outputs/komiai
```

来源：[文生图](https://www.komiai.cn/help/api-reference/detail?id=394)、[图片编辑](https://www.komiai.cn/help/api-reference/detail?id=393)、[临时文件上传](https://www.komiai.cn/help/api-reference/endpoints/upload-file)。
