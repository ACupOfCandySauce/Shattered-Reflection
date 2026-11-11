# 碎隙流光 / Shattered Reflection

程序化生成 Minecraft 镜面马赛克 PBR 材质包的 Python 工具。

支持多版本 × 多分辨率批量生成，自动处理 `pack_format`、LabPBR 贴图和 Iris/OptiFine 随机变体配置。

## 用途

- 勾选多个游戏版本和分辨率（64X / 128X / 256X），批量生成材质包
- 生成赛博半金属高光、斜面 POM 法线、LabPBR 1.3 所需贴图
- 自动从对应版本客户端 jar 抓取 `pack_format`，兼容 1.21.9+ 的 `min_format`/`max_format`
- 自动生成 Iris/OptiFine 随机变体 `.properties`
- 单个包直接输出 zip；多个包输出带时间戳的文件夹，按版本分目录

## 需要的库

```bash
pip install customtkinter Pillow numpy requests urllib3
```

PyTorch 需要安装 **CUDA 版本**，请根据自己的显卡和 CUDA 环境去 PyTorch 官网查找对应的安装命令。

可选：选择「7z极速压缩」时需要安装 7-Zip。

## 运行

双击 `镜面马赛克材质多批生成器.pyw`，或：

```bash
python 镜面马赛克材质多批生成器.pyw
```

## 许可证

- 生成器源码：MIT
- 生成的材质包内容：CC BY-NC-SA 4.0

## 致谢

本项目的代码完全由 DeepSeek 生成，作者仅提供思路与需求。
本 README 同样由 AI 生成。
