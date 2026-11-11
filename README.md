# 碎隙流光 / Shattered Reflection

程序化生成 Minecraft 镜面马赛克 PBR 材质包的 Python 工具。

支持多版本 × 多分辨率批量生成，自动处理 `pack_format`、LabPBR 法线/高光贴图。

## 用途

- 勾选多个游戏版本和分辨率（64X / 128X / 256X），批量生成材质包
- 生成赛博半金属高光、斜面 POM 法线、LabPBR 1.3 所需贴图
- 自动从对应版本客户端 jar 抓取 `pack_format`，兼容 1.21.9+ 的 `min_format`/`max_format`
- 单个包直接输出 zip；多个包输出带时间戳的文件夹，按版本分目录

## 需要的库

    pip install customtkinter Pillow numpy requests urllib3

PyTorch 需要安装 **CUDA 版本**，请根据自己的显卡和 CUDA 环境去 PyTorch 官网查找对应的安装命令。

可选：选择「7z极速压缩」时需要安装 7-Zip。

## 运行

双击 `镜面马赛克材质多批生成器.py`，或：

    python 镜面马赛克材质多批生成器.py

## 许可证

- 生成器源码：MIT
- 生成的材质包内容：CC BY-NC-SA 4.0

## 批次大小调整

256X 分辨率下，默认 `batch_size = 64` 的显存峰值约 11 GiB（实测 RTX 5060 Ti 16GB 占用约 13.4 GB / 16.3 GB，其中约 1.8 GB 为系统基线）。

- **16GB 及以上显卡**：可以保持默认 64
- **12GB 及以下显卡**：建议在代码中搜索 `batch_size = 64`（位于 `process_one_pack` 函数内），把 64 调小到 `32` 或 `16`

如果不调整，显存不足时会自动回退到逐张处理，功能正常但速度会明显变慢。

## 致谢

本项目的代码完全由 DeepSeek 生成，作者仅提供思路与需求。
本 README 同样由 AI 生成。
