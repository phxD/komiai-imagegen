---
name: "komiai-imagegen"
description: "使用 KomiAI（可米）中转的 gpt-image-2.5-sunburst-count 生成图片、用参考图改图、用遮罩局部重绘，或继续查询已有的 KomiAI 生图任务。适用于用户指定 KomiAI、可米生图、此模型或本 Skill 的请求。"
---

# KomiAI 生图

用 [scripts/komiai_image.py](scripts/komiai_image.py) 提交任务、轮询和保存图片。Windows 和 macOS 都需要 Python 3.10+。macOS 通常使用 `python3`。

## 按输入选择命令

- **文生图**用 `generate`。将提示词保存为 UTF-8 文件，通过 `--prompt-file` 传入。保留用户指定的画内文字、风格和限制。
- **参考图编辑**用 `edit`。用 `--reference-file` 传本地图片，用 `--reference` 传平台可访问的 URL 或已有 `file_id`。按用户指定的顺序重复传参。提示词交代每张图的用途、要改的位置和要保留的细节。用户提供遮罩时，用 `--mask-file` 或 `--mask`。
- **继续查询**用 `resume --task-id <task_id>`。使用同一个 KomiAI 账号和原输出目录，继续等待或重新下载结果。

默认生成 1 张 PNG，尺寸和画质由平台自动选择。按用户要求传入 `--size`、`--quality`、`--n` 等选项。透明背景用 `--background transparent` 和 PNG 或 WebP。完整参数和调用示例见 [references/komiai-api.md](references/komiai-api.md)。

## 运行和交付

从用户项目目录运行脚本，脚本路径使用本 Skill 下的实际路径。提交新任务会把提示词和本次选用的素材发给 KomiAI。仅传入本次任务指定的图片。默认将结果保存到当前项目的 `outputs/komiai`，用户指定目录时用 `--out-dir`。

首次使用时直接执行 `generate`、`edit` 或 `resume`。脚本优先读取 `KOMIAI_API_KEY`，随后查找系统中已保存的 Key。缺少 Key 时自动弹出密码输入框。点「保存」后写入 Windows 凭据管理器或 macOS 钥匙串，当前进程继续原任务，后续调用自动读取。

若脚本显示 `awaiting_key` 且仍在运行，提示用户查看本机窗口并等待原进程。用户取消时结束本次请求。若当前执行进程无法访问系统凭据，从可访问当前用户凭据的本机环境重试。也可以使用[本地环境变量](references/komiai-api.md#团队安装)。用户主动要求更换已保存的 Key 时，运行 `configure-key`。

从脚本输出记录 `task_id`，继续观察已有进程直到任务完成或报错。任务已受理但等待超时时，用原 ID 继续查询。提交后若连接中断且没有得到任务 ID，保留 `request_id` 并报告状态不明，先核对平台上的任务再决定是否重新提交。

检查保存的图片，向用户展示可预览的结果，提供本地文件路径和任务 ID。若生图失败，说明脚本返回的原因和已有的任务 ID。
