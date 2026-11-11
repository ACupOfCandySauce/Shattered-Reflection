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

普通依赖：

```bash
pip install customtkinter Pillow numpy requests urllib3
```

- `customtkinter`：图形界面
- `Pillow`：图片读取、缩放、保存
- `numpy`：图像数组处理
- `requests`：下载版本列表和客户端 jar
- `urllib3`：关闭 SSL 警告

`tkinter` 是 Python 标准库，Windows 官方安装包默认自带。

PyTorch 需要 **CUDA 版本**：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

CUDA 版本按你的显卡环境选择，参考 https://pytorch.org/get-started/locally/

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

代码编写过程中使用了 DeepSeek 辅助。
