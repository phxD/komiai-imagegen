# 使用手册

## 文生图

> `$komiai-imagegen` 生成一张 2048×1152 的横版极简咖啡主题海报，右侧预留标题空间，不要添加文字。

可以直接描述尺寸、数量、背景、格式和画面上的原文。默认生成 1 张 PNG。生成多张可说「给我 3 张构图不同的候选图」。

## 参考图编辑

先附上本地图片，再说明要改的位置和应保留的内容。

> `$komiai-imagegen` 把这张杯子的背景替换成纯白，保留杯身颜色、杯把和原有商标，输出 PNG。

可以传入 1 至 16 张参考图。若附有遮罩图，请注明它用于局部编辑。编辑请求中的本地图会先上传到 KomiAI。

## 续查或下载已有任务

> `$komiai-imagegen` 继续查询任务 `task_a1b2c3d4`，完成后保存图片。

使用首次提交后返回的任务 ID。有些任务 ID 以 `task_` 开头，也有日期加后缀的形式。用原账号和原输出目录执行续查。提交结果不明时，先记录请求编号，再核对任务。

## 直接运行脚本

示例从技能文件夹内运行。先创建 UTF-8 格式的 `prompt.txt`。Windows 用 `python`，macOS 将命令中的 `python` 改为 `python3`。

```text
python scripts/komiai_image.py generate --prompt-file prompt.txt --size 1024x1024
python scripts/komiai_image.py edit --prompt-file prompt.txt --reference-file product.png
python scripts/komiai_image.py resume --task-id task_a1b2c3d4
```

默认以当前工作目录为基准，将结果放入 `outputs/komiai/`。需要自定义路径时使用 `--out-dir`。完整参数、可选尺寸和支持的输出格式见 [接口参考](../skills/komiai-imagegen/references/komiai-api.md)。
