# apps/desktop — ODPlatform 桌面端

基于 PySide6 的推理演示界面。它通过 `QtSignalSink`、`InferHooks` 和
`CancelToken` 调用 `od_platform.inference`，不修改推理引擎。

## 安装

在项目根目录执行：

```powershell
conda activate ODP
python -m pip install -e "./apps/platform[desktop]"
```

## 运行

```powershell
cd C:\Users\DELL\ODPlatform
powershell -ExecutionPolicy Bypass -File .\scripts\run_desktop.ps1
```

如果 `ODP` 中已经安装 PySide6，也可以直接运行
`python apps\desktop\main.py`。启动脚本会在当前解释器没有 PySide6 时，
自动寻找本机另一个已安装 PySide6 的 Python 解释器。

界面中可填写：

- Model：模型权重路径，默认使用 `models/pretrained/yolov8n.pt`
- Source：摄像头编号（如 `0`）、图片、视频文件或图片目录

运行期间点击 `Stop` 可停止推理并释放摄像头。关闭窗口前应等待推理线程退出。
