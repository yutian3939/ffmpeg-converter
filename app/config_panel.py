"""参数配置面板模块"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QPushButton, QFormLayout,
    QTabWidget, QGridLayout, QSlider, QFrame,
    QScrollArea, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from app.presets import FormatPreset, preset_manager


class ConfigPanel(QWidget):
    """参数配置面板 - 提供可视化的转换参数配置"""

    preset_changed = pyqtSignal(object)  # FormatPreset

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_preset: FormatPreset = FormatPreset()
        self._preset_combo = None
        self._setup_ui()
        self._connect_signals()
        self._load_presets()
        self._populate_controls()

    def _setup_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # 标题
        title = QLabel("参数配置")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # 预设选择区域
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设:"))
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(180)
        preset_layout.addWidget(self._preset_combo)

        self._save_preset_btn = QPushButton("保存预设")
        self._save_preset_btn.setFixedWidth(80)
        self._del_preset_btn = QPushButton("删除")
        self._del_preset_btn.setFixedWidth(60)
        preset_layout.addWidget(self._save_preset_btn)
        preset_layout.addWidget(self._del_preset_btn)
        preset_layout.addStretch()
        main_layout.addLayout(preset_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self._format_combo = QComboBox()
        formats = [
            ("MP4 (.mp4)", ".mp4"),
            ("MKV (.mkv)", ".mkv"),
            ("AVI (.avi)", ".avi"),
            ("MOV (.mov)", ".mov"),
            ("WebM (.webm)", ".webm"),
            ("GIF (.gif)", ".gif"),
            ("MP3 (.mp3)", ".mp3"),
            ("FLAC (.flac)", ".flac"),
            ("WAV (.wav)", ".wav"),
            ("AAC (.aac)", ".aac"),
            ("OGG (.ogg)", ".ogg"),
            ("OPUS (.opus)", ".opus"),
        ]
        for name, _ in formats:
            self._format_combo.addItem(name)
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        # 硬件加速（独立于预设，始终保留上次选择）
        hwaccel_layout = QHBoxLayout()
        hwaccel_layout.addWidget(QLabel("硬件加速:"))
        self._hwaccel_combo = QComboBox()
        self._hwaccel_combo.addItems(["无", "Intel QSV", "NVIDIA NVENC", "AMD AMF", "VideoToolbox"])
        hwaccel_layout.addWidget(self._hwaccel_combo)
        hwaccel_layout.addStretch()
        main_layout.addLayout(hwaccel_layout)

        # 选项卡：视频/音频/高级
        self._tab_widget = QTabWidget()
        main_layout.addWidget(self._tab_widget)

        # ---- 视频参数选项卡 ----
        video_widget = QWidget()
        video_layout = QVBoxLayout(video_widget)
        video_layout.setSpacing(3)
        video_layout.setContentsMargins(2, 2, 2, 2)

        # 视频编码器
        vcodec_layout = QHBoxLayout()
        vcodec_layout.addWidget(QLabel("视频编码器:"))
        self._vcodec_combo = QComboBox()
        video_codecs = [
            ("H.264 (libx264)", "libx264"),
            ("H.265/HEVC (libx265)", "libx265"),
            ("VP9 (libvpx-vp9)", "libvpx-vp9"),
            ("VP8 (libvpx)", "libvpx"),
            ("AV1 (libaom-av1)", "libaom-av1"),
            ("无视频流", "none"),
        ]
        for name, codec in video_codecs:
            self._vcodec_combo.addItem(name, codec)
        vcodec_layout.addWidget(self._vcodec_combo)
        vcodec_layout.addStretch()
        video_layout.addLayout(vcodec_layout)

        # 视频码率
        vbitrate_layout = QHBoxLayout()
        vbitrate_layout.addWidget(QLabel("视频码率:"))
        self._vbitrate_combo = QComboBox()
        bitrates = ["自动", "500k", "1000k", "1500k", "2000k", "2500k",
                     "3000k", "4000k", "5000k", "8000k", "10000k", "15000k", "20000k"]
        self._vbitrate_combo.addItems(bitrates)
        self._vbitrate_combo.setCurrentText("2000k")
        vbitrate_layout.addWidget(self._vbitrate_combo)
        vbitrate_layout.addSpacing(6)
        self._vbitrate_mode_combo = QComboBox()
        self._vbitrate_mode_combo.addItems(["VBR (可变码率)", "CBR (固定码率)"])
        vbitrate_layout.addWidget(self._vbitrate_mode_combo)
        vbitrate_layout.addStretch()
        video_layout.addLayout(vbitrate_layout)

        # 分辨率
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("分辨率:"))
        self._resolution_combo = QComboBox()
        resolutions = [
            "原始", "3840×2160 (4K)", "2560×1440 (2K)",
            "1920×1080 (1080p)", "1280×720 (720p)",
            "854×480 (480p)", "640×360 (360p)", "自定义"
        ]
        self._resolution_combo.addItems(resolutions)
        resolution_layout.addWidget(self._resolution_combo)
        resolution_layout.addStretch()
        video_layout.addLayout(resolution_layout)

        # 自定义分辨率
        custom_res_layout = QHBoxLayout()
        custom_res_layout.addWidget(QLabel("宽:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(16, 7680)
        self._width_spin.setValue(1920)
        self._width_spin.setEnabled(False)
        custom_res_layout.addWidget(self._width_spin)
        custom_res_layout.addSpacing(6)
        custom_res_layout.addWidget(QLabel("高:"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(16, 4320)
        self._height_spin.setValue(1080)
        self._height_spin.setEnabled(False)
        custom_res_layout.addWidget(self._height_spin)
        custom_res_layout.addStretch()
        video_layout.addLayout(custom_res_layout)

        # 帧率
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率 (fps):"))
        self._fps_combo = QComboBox()
        fps_options = ["original", "10", "15", "24", "25", "30", "48", "50", "60", "120"]
        self._fps_combo.addItems(fps_options)
        fps_layout.addWidget(self._fps_combo)
        fps_layout.addStretch()
        video_layout.addLayout(fps_layout)

        video_layout.addStretch()
        self._tab_widget.addTab(video_widget, "视频")

        # ---- 音频参数选项卡 ----
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)
        audio_layout.setSpacing(3)
        audio_layout.setContentsMargins(2, 2, 2, 2)

        # 音频编码器
        acodec_layout = QHBoxLayout()
        acodec_layout.addWidget(QLabel("音频编码器:"))
        self._acodec_combo = QComboBox()
        audio_codecs = [
            ("AAC (aac)", "aac"),
            ("MP3 (libmp3lame)", "libmp3lame"),
            ("FLAC (flac)", "flac"),
            ("Opus (libopus)", "libopus"),
            ("Vorbis (libvorbis)", "libvorbis"),
            ("PCM (pcm_s16le)", "pcm_s16le"),
            ("无音频流", "none"),
            ("复制原音频", "copy"),
        ]
        for name, codec in audio_codecs:
            self._acodec_combo.addItem(name, codec)
        acodec_layout.addWidget(self._acodec_combo)
        acodec_layout.addStretch()
        audio_layout.addLayout(acodec_layout)

        # 音频码率
        abitrate_layout = QHBoxLayout()
        abitrate_layout.addWidget(QLabel("音频码率:"))
        self._abitrate_combo = QComboBox()
        abitrates = ["32k", "64k", "96k", "128k", "160k", "192k", "256k", "320k"]
        self._abitrate_combo.addItems(abitrates)
        self._abitrate_combo.setCurrentText("192k")
        abitrate_layout.addWidget(self._abitrate_combo)
        abitrate_layout.addStretch()
        audio_layout.addLayout(abitrate_layout)

        # 采样率
        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("采样率:"))
        self._sample_combo = QComboBox()
        self._sample_combo.addItems(["22050", "44100", "48000", "96000"])
        self._sample_combo.setCurrentText("44100")
        sample_layout.addWidget(self._sample_combo)
        sample_layout.addStretch()
        audio_layout.addLayout(sample_layout)

        # 声道数
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("声道数:"))
        self._channel_combo = QComboBox()
        self._channel_combo.addItems(["1 (单声道)", "2 (立体声)", "6 (5.1环绕)"])
        self._channel_combo.setCurrentIndex(1)
        channel_layout.addWidget(self._channel_combo)
        channel_layout.addStretch()
        audio_layout.addLayout(channel_layout)

        audio_layout.addStretch()
        self._tab_widget.addTab(audio_widget, "音频")

        # ---- 高级参数选项卡 ----
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setSpacing(3)
        advanced_layout.setContentsMargins(2, 2, 2, 2)

        # 裁剪 - 开始时间
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开始时间 (HH:MM:SS):"))
        self._start_time_input = QLineEdit()
        self._start_time_input.setPlaceholderText("例如: 00:01:30")
        start_layout.addWidget(self._start_time_input)
        start_layout.addStretch()
        advanced_layout.addLayout(start_layout)

        # 裁剪 - 持续时间
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("持续时间 (秒):"))
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(0, 99999)
        self._duration_spin.setValue(0)
        self._duration_spin.setSuffix(" 秒")
        self._duration_spin.setSpecialValueText("全部")
        duration_layout.addWidget(self._duration_spin)
        duration_layout.addStretch()
        advanced_layout.addLayout(duration_layout)

        # 附加参数
        extra_layout = QVBoxLayout()
        extra_layout.addWidget(QLabel("附加 ffmpeg 参数:"))
        self._extra_args_input = QLineEdit()
        self._extra_args_input.setPlaceholderText("例如: -preset fast -tune film")
        extra_layout.addWidget(self._extra_args_input)
        advanced_layout.addLayout(extra_layout)

        advanced_layout.addStretch()
        self._tab_widget.addTab(advanced_widget, "高级")

        main_layout.addStretch()

    def _connect_signals(self):
        """连接信号"""
        self._preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self._save_preset_btn.clicked.connect(self._on_save_preset)
        self._del_preset_btn.clicked.connect(self._on_delete_preset)
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)
        self._vcodec_combo.currentIndexChanged.connect(self._on_any_param_changed)
        self._vbitrate_combo.currentTextChanged.connect(self._on_any_param_changed)
        self._vbitrate_mode_combo.currentIndexChanged.connect(self._on_any_param_changed)
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self._width_spin.valueChanged.connect(self._on_any_param_changed)
        self._height_spin.valueChanged.connect(self._on_any_param_changed)
        self._fps_combo.currentTextChanged.connect(self._on_any_param_changed)
        self._acodec_combo.currentIndexChanged.connect(self._on_any_param_changed)
        self._abitrate_combo.currentTextChanged.connect(self._on_any_param_changed)
        self._sample_combo.currentTextChanged.connect(self._on_any_param_changed)
        self._channel_combo.currentIndexChanged.connect(self._on_any_param_changed)
        self._hwaccel_combo.currentIndexChanged.connect(self._on_any_param_changed)
        self._start_time_input.textChanged.connect(self._on_any_param_changed)
        self._duration_spin.valueChanged.connect(self._on_any_param_changed)
        self._extra_args_input.textChanged.connect(self._on_any_param_changed)

    def _load_presets(self):
        """加载预设列表，恢复上次选择"""
        from app.presets import preset_manager
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        for name in preset_manager.get_preset_names():
            self._preset_combo.addItem(name)
        # 恢复上次选择的预设
        last = preset_manager.last_preset
        idx = self._preset_combo.findText(last)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        elif self._preset_combo.count() > 0:
            self._preset_combo.setCurrentIndex(0)
        self._preset_combo.blockSignals(False)

        # 1. 应用预设参数（不保存，避免覆盖 last_hwaccel）
        current_name = self._preset_combo.currentText()
        preset = preset_manager.get_preset(current_name) if current_name else None
        if preset:
            self._apply_preset(preset)

        # 2. 覆盖硬件加速为上次保存的值
        self._restore_hwaccel()

        # 3. 统一保存最终状态
        preset_manager.last_preset = self._preset_combo.currentText()
        preset_manager.last_hwaccel = self._get_current_hwaccel()
        preset_manager.save_user_presets()

    def _restore_hwaccel(self):
        """恢复上次的硬件加速设置"""
        from app.presets import preset_manager
        hwaccel_rev = {
            "none": "无", "qsv": "Intel QSV", "cuda": "NVIDIA NVENC",
            "amf": "AMD AMF", "videotoolbox": "VideoToolbox",
        }
        hw_text = hwaccel_rev.get(preset_manager.last_hwaccel, "无")
        idx = self._hwaccel_combo.findText(hw_text)
        if idx >= 0:
            self._hwaccel_combo.blockSignals(True)
            self._hwaccel_combo.setCurrentIndex(idx)
            self._hwaccel_combo.blockSignals(False)

    def _get_current_hwaccel(self) -> str:
        """获取当前硬件加速设置的内部值"""
        hwaccel_map = {
            "无": "none", "Intel QSV": "qsv", "NVIDIA NVENC": "cuda",
            "AMD AMF": "amf", "VideoToolbox": "videotoolbox",
        }
        return hwaccel_map.get(self._hwaccel_combo.currentText(), "none")

    def _on_preset_selected(self, name: str):
        """预设选择变化"""
        if not name:
            return
        preset = preset_manager.get_preset(name)
        if preset:
            self._apply_preset(preset)
            # 更新 _current_preset（_blockAll 期间信号被抑制，_update_preset 不会自动触发）
            self._update_preset()
            # 保存上次选择的预设（不覆盖硬件加速）
            preset_manager.last_preset = name
            preset_manager.save_user_presets()

    def _on_format_changed(self, index: int):
        """输出格式变更时自动设置对应编码器"""
        format_ext_map = {
            0: (".mp4", "libx264", "aac"),
            1: (".mkv", "libx264", "aac"),
            2: (".avi", "libx264", "mp3"),
            3: (".mov", "libx264", "aac"),
            4: (".webm", "libvpx-vp9", "libopus"),
            5: (".gif", "gif", "none"),
            6: (".mp3", "none", "libmp3lame"),
            7: (".flac", "none", "flac"),
            8: (".wav", "none", "pcm_s16le"),
            9: (".aac", "none", "aac"),
            10: (".ogg", "none", "libvorbis"),
            11: (".opus", "none", "libopus"),
        }
        if index in format_ext_map:
            ext, vcodec, acodec = format_ext_map[index]
            self._set_codecs_from_format(ext, vcodec, acodec)
            self._update_preset()
            self._on_any_param_changed()

    def _set_codecs_from_format(self, ext: str, vcodec: str, acodec: str):
        """根据格式设置编码器"""
        # 设置视频编码器
        for i in range(self._vcodec_combo.count()):
            if self._vcodec_combo.itemData(i) == vcodec:
                self._vcodec_combo.setCurrentIndex(i)
                break

        # 设置音频编码器
        for i in range(self._acodec_combo.count()):
            if self._acodec_combo.itemData(i) == acodec:
                self._acodec_combo.setCurrentIndex(i)
                break

    def _on_resolution_changed(self, index: int):
        """分辨率选择变化"""
        enable_custom = (self._resolution_combo.currentText() == "自定义")
        self._width_spin.setEnabled(enable_custom)
        self._height_spin.setEnabled(enable_custom)
        self._on_any_param_changed()

    def _on_any_param_changed(self):
        """任意参数变化"""
        self._update_preset()
        # 硬件加速变化时立即保存
        current_hw = self._get_current_hwaccel()
        if current_hw != preset_manager.last_hwaccel:
            preset_manager.last_hwaccel = current_hw
            preset_manager.save_user_presets()

    def _on_save_preset(self):
        """保存当前配置为预设"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "保存预设", "请输入预设名称:",
            text=self._current_preset.name
        )
        if ok and name.strip():
            preset = self._build_preset_from_ui()
            preset.name = name.strip()
            preset_manager.add_preset(preset)
            # 刷新下拉列表
            current = self._preset_combo.currentText()
            self._load_presets()
            # 选中刚保存的
            idx = self._preset_combo.findText(name.strip())
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)

    def _on_delete_preset(self):
        """删除预设"""
        name = self._preset_combo.currentText()
        builtin = preset_manager.get_builtin_names()
        if name in builtin:
            QMessageBox.information(self, "提示", "内置预设无法删除")
            return
        if name:
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除预设 \"{name}\" 吗?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                preset_manager.remove_preset(name)
                self._load_presets()

    def _build_preset_from_ui(self) -> FormatPreset:
        """从 UI 控件构建预设对象"""
        # 视频编码器
        vcodec = self._vcodec_combo.currentData() or self._vcodec_combo.currentText()

        # 视频码率
        vbitrate_text = self._vbitrate_combo.currentText()
        vbitrate = "" if vbitrate_text == "自动" else vbitrate_text
        vbitrate_mode = "cbr" if self._vbitrate_mode_combo.currentIndex() == 1 else "vbr"

        # 分辨率
        resolution_text = self._resolution_combo.currentText()
        width, height = 0, 0
        if resolution_text == "自定义":
            width = self._width_spin.value()
            height = self._height_spin.value()
        elif "×" in resolution_text:
            parts = resolution_text.split("×")
            try:
                width = int(parts[0].strip())
                height_val = parts[1].split(" ")[0].strip() if " " in parts[1] else parts[1].strip()
                height = int(height_val)
            except (ValueError, IndexError):
                pass

        # 帧率
        framerate = self._fps_combo.currentText()

        # 音频编码器
        acodec = self._acodec_combo.currentData() or self._acodec_combo.currentText()

        # 音频码率
        abitrate = self._abitrate_combo.currentText()

        # 采样率
        try:
            sample_rate = int(self._sample_combo.currentText())
        except ValueError:
            sample_rate = 44100

        # 声道数
        channel_map = {0: 1, 1: 2, 2: 6}
        channels = channel_map.get(self._channel_combo.currentIndex(), 2)

        # 硬件加速
        hwaccel_map = {
            "无": "none",
            "Intel QSV": "qsv",
            "NVIDIA NVENC": "cuda",
            "AMD AMF": "amf",
            "VideoToolbox": "videotoolbox",
        }
        hwaccel = hwaccel_map.get(self._hwaccel_combo.currentText(), "none")

        # 裁剪
        start_time = self._start_time_input.text().strip()
        duration = str(self._duration_spin.value()) if self._duration_spin.value() > 0 else ""

        # 附加参数
        extra = self._extra_args_input.text().strip()
        additional_args = extra.split() if extra else []

        # 扩展名
        ext = self._format_combo.currentText().split("(")[-1].rstrip(")") if "(" in self._format_combo.currentText() else ".mp4"

        preset = FormatPreset(
            name=self._preset_combo.currentText(),
            extension=ext,
            video_codec=vcodec,
            video_bitrate=vbitrate,
            video_bitrate_mode=vbitrate_mode,
            width=width,
            height=height,
            framerate=framerate,
            audio_codec=acodec,
            audio_bitrate=abitrate,
            sample_rate=sample_rate,
            channels=channels,
            hwaccel=hwaccel,
            start_time=start_time,
            duration=duration,
            additional_args=additional_args,
        )
        return preset

    def _apply_preset(self, preset: FormatPreset):
        """应用预设到 UI 控件"""
        self._block_all(True)

        # 格式
        ext = preset.extension
        for i in range(self._format_combo.count()):
            if ext in self._format_combo.itemText(i):
                self._format_combo.setCurrentIndex(i)
                break

        # 视频编码器
        for i in range(self._vcodec_combo.count()):
            if self._vcodec_combo.itemData(i) == preset.video_codec:
                self._vcodec_combo.setCurrentIndex(i)
                break

        # 视频码率
        if preset.video_bitrate:
            idx = self._vbitrate_combo.findText(preset.video_bitrate)
            if idx >= 0:
                self._vbitrate_combo.setCurrentIndex(idx)
        else:
            self._vbitrate_combo.setCurrentText("自动")

        # VBR/CBR
        self._vbitrate_mode_combo.setCurrentIndex(
            1 if preset.video_bitrate_mode == 'cbr' else 0
        )

        # 分辨率
        resolution_text = "原始"
        if preset.width > 0 and preset.height > 0:
            res_str = f"{preset.width}×{preset.height}"
            found = False
            for i in range(self._resolution_combo.count()):
                if res_str in self._resolution_combo.itemText(i):
                    self._resolution_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self._resolution_combo.setCurrentText("自定义")
                self._width_spin.setValue(preset.width)
                self._height_spin.setValue(preset.height)
        else:
            self._resolution_combo.setCurrentText("原始")

        # 帧率
        fps_idx = self._fps_combo.findText(str(preset.framerate))
        if fps_idx >= 0:
            self._fps_combo.setCurrentIndex(fps_idx)
        else:
            self._fps_combo.setCurrentText("original")

        # 音频编码器
        for i in range(self._acodec_combo.count()):
            if self._acodec_combo.itemData(i) == preset.audio_codec:
                self._acodec_combo.setCurrentIndex(i)
                break

        # 音频码率
        if preset.audio_bitrate:
            abitrate_idx = self._abitrate_combo.findText(preset.audio_bitrate)
            if abitrate_idx >= 0:
                self._abitrate_combo.setCurrentIndex(abitrate_idx)

        # 采样率
        sample_idx = self._sample_combo.findText(str(preset.sample_rate))
        if sample_idx >= 0:
            self._sample_combo.setCurrentIndex(sample_idx)

        # 声道数
        ch_map = {1: 0, 2: 1, 6: 2}
        self._channel_combo.setCurrentIndex(ch_map.get(preset.channels, 1))

        # 裁剪
        self._start_time_input.setText(preset.start_time)
        if preset.duration:
            try:
                self._duration_spin.setValue(int(preset.duration))
            except ValueError:
                self._duration_spin.setValue(0)
        else:
            self._duration_spin.setValue(0)

        # 附加参数
        self._extra_args_input.setText(' '.join(preset.additional_args))

        self._block_all(False)

    def _block_all(self, block: bool):
        """批量阻塞/恢复信号"""
        for w in [self._format_combo, self._vcodec_combo, self._vbitrate_combo,
                  self._vbitrate_mode_combo, self._resolution_combo, self._width_spin,
                  self._height_spin, self._fps_combo, self._acodec_combo,
                  self._abitrate_combo, self._sample_combo, self._channel_combo,
                  self._hwaccel_combo, self._start_time_input, self._duration_spin,
                  self._extra_args_input]:
            w.blockSignals(block)

    def _update_preset(self):
        """更新当前预设并发射信号"""
        self._current_preset = self._build_preset_from_ui()
        self.preset_changed.emit(self._current_preset)

    def _populate_controls(self):
        """初始化控件默认值"""
        self._update_preset()

    def get_current_preset(self) -> FormatPreset:
        """获取当前配置的预设"""
        return self._current_preset
