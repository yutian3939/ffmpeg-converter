# FFmpeg 格式转换器

一个基于 **PyQt5** 和 **FFmpeg** 的可视化音视频格式转换工具。支持批量添加文件 / 文件夹、预设与自定义参数、硬件加速、任务队列并发转换、进度实时显示等功能。

## 功能特性

- **批量转换**：支持同时添加多个文件，也可递归导入整个文件夹
- **拖放支持**：直接将文件 / 文件夹拖入窗口即可加入列表
- **丰富预设**：内置 15 种常用预设（MP4 / MKV / WebM / AVI / MOV / GIF、MP3 / FLAC / WAV / AAC、720p / 1080p / 4K 等），也支持保存 / 删除自定义预设
- **灵活参数**：
  - 视频：编码器（H.264 / H.265 / VP9 / VP8 / AV1）、码率（VBR / CBR）、分辨率（含自定义）、帧率
  - 音频：编码器（AAC / MP3 / FLAC / Opus / Vorbis / PCM / 复制原音频）、码率、采样率、声道数
  - 高级：按开始时间 / 时长裁剪、附加 ffmpeg 参数
- **硬件加速**：支持 Intel QSV、NVIDIA NVENC、AMD AMF、Apple VideoToolbox
- **任务队列**：可设置 1–8 路并发，支持暂停 / 恢复 / 取消、调整任务顺序、清除已完成任务
- **进度反馈**：实时显示转换进度百分比、速度、FPS；完成后提示输出文件大小
- **智能查找 ffmpeg**：优先使用内置 ffmpeg（`resources/ffmpeg/`），其次查找系统 PATH
- **状态记忆**：上次使用的预设、硬件加速、输入目录、窗口布局等自动保存到 `settings.json`

## 环境要求

- Python 3.8+
- PyQt5 >= 5.15
- ffmpeg（可执行文件，含 `ffmpeg.exe` / `ffprobe.exe`）
- 操作系统：Windows（已内置对 macOS / Linux 的兼容处理）

## 安装与运行

### 1. 准备 ffmpeg

任选一种方式：

- 将 `ffmpeg.exe`、`ffprobe.exe` 放入项目 `resources/ffmpeg/` 目录（程序优先使用，推荐）
- 或从 [ffmpeg 官网](https://ffmpeg.org/download.html) 下载并配置到系统 PATH 环境变量

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动程序

开发环境运行（首次需先创建虚拟环境 `venv` 并安装依赖）：

```bash
python main.py
```

Windows 下也可直接双击 `start.bat`（会自动使用 `venv` 中的 Python 启动）。

> 提示：打包为 exe 后无需安装 Python 或 ffmpeg，可直接运行。

## 打包为独立 exe

项目根目录需存在 `resources/ffmpeg/ffmpeg.exe` 与 `resources/ffmpeg/ffprobe.exe`，然后执行：

```bash
python build.py
```

打包完成后，在 `dist/` 目录生成单文件 `FFmpegConverter.exe`，拷贝到其他电脑即可直接运行（无需安装 Python 或 ffmpeg）。

## 使用说明

1. 通过「+ 添加文件」「+ 添加文件夹」按钮或直接拖放，将媒体文件加入列表
2. 在左侧「参数配置」面板选择预设，或按需调整视频 / 音频 / 高级参数
3. 点击「添加到队列并转换」，选择输出目录
4. 在右侧「任务队列」中查看进度，可对任务进行暂停、恢复、取消、上下移动等操作
5. 所有任务完成后程序会弹出提示

常用快捷键：

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+O` | 添加文件 |
| `Ctrl+Shift+O` | 添加文件夹 |
| `Ctrl+Enter` | 开始全部任务 |
| `Ctrl+Q` | 退出程序 |

转换后的文件以 `原文件名_converted.扩展名` 保存在所选输出目录中，不会覆盖源文件。

## 支持的格式

**视频输出**：MP4、MKV、AVI、MOV、WebM、GIF

**音频输出**：MP3、FLAC、WAV、AAC、OGG、OPUS

**输入**：`mp4 mkv avi mov wmv flv webm m4v mp3 flac wav aac ogg opus wma` 等常见音视频文件

## 项目结构

```
ffmpeg-converter/
├── main.py               # 程序入口
├── requirements.txt      # Python 依赖
├── settings.json         # 用户设置（预设、并发数、窗口布局等）
├── build.py              # PyInstaller 打包脚本
├── FFmpegConverter.spec  # PyInstaller 配置
├── start.bat             # Windows 启动脚本
├── app/                  # 界面层
│   ├── mainwindow.py     # 主窗口
│   ├── config_panel.py   # 参数配置面板
│   ├── queue_view.py     # 任务队列视图
│   └── presets.py        # 格式预设管理
├── core/                 # 核心逻辑层
│   ├── ffmpeg_api.py     # ffmpeg 命令封装
│   ├── worker.py         # 转换工作线程
│   ├── task_manager.py   # 任务调度器
│   └── progress_parser.py# ffmpeg 进度解析
└── resources/            # 资源文件
    ├── styles.qss        # QSS 样式表
    ├── ffmpeg/           # 内置 ffmpeg / ffprobe
    └── icons/            # 应用图标（可选）
```

## 技术架构

- **UI 层**（`app/`）：基于 PyQt5 构建，主窗口负责文件导入与信号交互，配置面板通过 `FormatPreset` 对象承载所有转换参数
- **核心层**（`core/`）：
  - `task_manager.py` 维护任务队列，按并发上限调度任务，控制暂停 / 取消 / 优先级
  - 每个任务由独立 `worker.py` 线程执行，调用 `ffmpeg_api.py` 构建命令行
  - `progress_parser.py` 解析 ffmpeg 输出的进度信息
- 任务并发上限可在界面「并行数」中调节（1–8）
