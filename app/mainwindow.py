"""主窗口模块"""

import os
import sys
from core.ffmpeg_api import get_settings_path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QStatusBar, QMenuBar, QMenu,
    QAction, QApplication, QFrame, QInputDialog, QSpinBox,
    QDialog, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, QUrl, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent

from core.task_manager import TaskManager, TaskStatus, ConvertTask
from core.ffmpeg_api import ffmpeg_api
from app.config_panel import ConfigPanel
from app.queue_view import TaskQueueView
from app.presets import FormatPreset


class MainWindow(QMainWindow):
    """应用程序主窗口"""

    def __init__(self):
        super().__init__()
        self._task_manager = TaskManager(max_concurrent=2)
        self._files: list[str] = []
        self._last_input_dir = self._load_last_input_dir()
        self._setup_ui()
        self._connect_signals()
        self._check_ffmpeg()

    @staticmethod
    def _load_last_input_dir() -> str:
        """从 settings.json 加载上次文件导入路径"""
        import json
        path = get_settings_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('last_input_dir', '')
        except Exception:
            return ''

    def _save_last_input_dir(self, dir_path: str):
        """保存上次文件导入路径到 settings.json"""
        import json
        path = get_settings_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['last_input_dir'] = dir_path
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _restore_splitter(self):
        """恢复分割线位置"""
        import json
        path = get_settings_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            sizes = data.get('splitter_sizes')
            if sizes and len(sizes) == 2:
                self._splitter.setSizes(sizes)
            else:
                self._splitter.setSizes([395, 585])
        except Exception:
            self._splitter.setSizes([395, 585])

    def _save_splitter(self):
        """保存分割线位置"""
        import json
        sizes = self._splitter.sizes()
        path = get_settings_path()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['splitter_sizes'] = sizes
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _setup_ui(self):
        """初始化 UI"""
        self.setWindowTitle("FFmpeg 格式转换器")
        self.setMinimumSize(900, 580)
        self.resize(1000, 660)

        # 设置接受拖放
        self.setAcceptDrops(True)

        # 加载样式表
        self._load_stylesheet()

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ---- 上方工具栏 ----
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(6)

        self._add_files_btn = QPushButton("+ 添加文件")
        self._add_files_btn.setFixedHeight(32)
        self._add_folder_btn = QPushButton("+ 添加文件夹")
        self._add_folder_btn.setFixedHeight(32)
        self._remove_file_btn = QPushButton("移除选中")
        self._remove_file_btn.setFixedHeight(32)
        self._clear_files_btn = QPushButton("清空列表")
        self._clear_files_btn.setFixedHeight(32)

        for btn in [self._add_files_btn, self._add_folder_btn,
                    self._remove_file_btn, self._clear_files_btn]:
            toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()

        # 并发数控制
        toolbar_layout.addWidget(QLabel("并行数:"))
        self._concurrent_spin = QSpinBox()
        self._concurrent_spin.setRange(1, 8)
        self._concurrent_spin.setValue(2)
        self._concurrent_spin.setFixedWidth(60)
        self._concurrent_spin.setFixedHeight(28)
        toolbar_layout.addWidget(self._concurrent_spin)

        main_layout.addLayout(toolbar_layout)

        # ---- 主内容区域：左右分栏 ----
        self._splitter = QSplitter(Qt.Horizontal)

        # 左侧面板：文件列表 + 参数配置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(6)

        # 文件列表
        file_frame = QFrame()
        file_frame.setFrameShape(QFrame.StyledPanel)
        file_layout = QVBoxLayout(file_frame)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(2)

        file_title = QLabel("待转换文件")
        file_title_font = QFont()
        file_title_font.setPointSize(12)
        file_title_font.setBold(True)
        file_title.setFont(file_title_font)
        file_layout.addWidget(file_title)

        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setAcceptDrops(True)
        self._file_list.setDragDropMode(QListWidget.NoDragDrop)
        # 空提示容器 - 始终替代 file_list 占据空间，但 hint 顶部对齐
        self._empty_hint_container = QWidget()
        hint_layout = QVBoxLayout(self._empty_hint_container)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        self._empty_hint = QLabel("拖放文件到此处\n或点击上方按钮添加")
        self._empty_hint.setAlignment(Qt.AlignHCenter)
        self._empty_hint.setStyleSheet("color: #999; font-size: 13px; padding: 30px;")
        hint_layout.addWidget(self._empty_hint)
        hint_layout.addStretch()
        file_layout.addWidget(self._empty_hint_container)
        file_layout.addWidget(self._file_list)
        self._file_list.hide()

        left_layout.addWidget(file_frame)

        # 参数配置面板
        self._config_panel = ConfigPanel()
        left_layout.addWidget(self._config_panel)

        # 添加任务按钮
        self._add_queue_btn = QPushButton("▶ 添加到队列并转换")
        self._add_queue_btn.setFixedHeight(36)
        self._add_queue_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        left_layout.addWidget(self._add_queue_btn)

        self._splitter.addWidget(left_panel)

        # 右侧面板：任务队列
        self._queue_view = TaskQueueView(self)
        self._splitter.addWidget(self._queue_view)

        # 设置分栏比例
        self._restore_splitter()

        # 菜单栏（需在 _queue_view 创建之后）
        self._create_menu_bar()

        main_layout.addWidget(self._splitter)

        # ---- 状态栏 ----
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("就绪")
        self._status_bar.addWidget(self._status_label)
        self._ffmpeg_status = QLabel("")
        self._status_bar.addPermanentWidget(self._ffmpeg_status)

        # 连接信号
        self._add_files_btn.clicked.connect(self._on_add_files)
        self._add_folder_btn.clicked.connect(self._on_add_folder)
        self._remove_file_btn.clicked.connect(self._on_remove_file)
        self._clear_files_btn.clicked.connect(self._on_clear_files)
        self._add_queue_btn.clicked.connect(self._on_add_to_queue)
        self._concurrent_spin.valueChanged.connect(self._on_concurrent_changed)
        self._file_list.model().rowsInserted.connect(self._update_empty_hint)
        self._file_list.model().rowsRemoved.connect(self._update_empty_hint)

        self._update_empty_hint()

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        add_files_action = QAction("添加文件...", self)
        add_files_action.setShortcut("Ctrl+O")
        add_files_action.triggered.connect(self._on_add_files)
        file_menu.addAction(add_files_action)

        add_folder_action = QAction("添加文件夹...", self)
        add_folder_action.setShortcut("Ctrl+Shift+O")
        add_folder_action.triggered.connect(self._on_add_folder)
        file_menu.addAction(add_folder_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 任务菜单
        task_menu = menubar.addMenu("任务(&T)")

        start_all_action = QAction("开始全部", self)
        start_all_action.setShortcut("Ctrl+Enter")
        start_all_action.triggered.connect(self._on_start_all)
        task_menu.addAction(start_all_action)

        pause_all_action = QAction("暂停全部", self)
        pause_all_action.triggered.connect(self._queue_view.pause_all)
        task_menu.addAction(pause_all_action)

        task_menu.addSeparator()

        clear_completed_action = QAction("清除已完成", self)
        clear_completed_action.triggered.connect(self._on_clear_completed)
        task_menu.addAction(clear_completed_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        check_ffmpeg_action = QAction("检测 ffmpeg", self)
        check_ffmpeg_action.triggered.connect(self._check_ffmpeg)
        help_menu.addAction(check_ffmpeg_action)

    def _load_stylesheet(self):
        """加载 QSS 样式表"""
        qss_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'resources', 'styles.qss')
        if os.path.isfile(qss_path):
            try:
                with open(qss_path, 'r', encoding='utf-8') as f:
                    style = f.read()
                self.setStyleSheet(style)
            except Exception:
                pass

    def _connect_signals(self):
        """连接信号"""
        # 任务管理器信号 -> 队列视图
        self._task_manager.task_added.connect(self._on_task_added)
        self._task_manager.task_removed.connect(self._on_task_removed)
        self._task_manager.task_progress_updated.connect(self._on_task_progress)
        self._task_manager.task_status_changed.connect(self._on_task_status_changed)
        self._task_manager.all_tasks_completed.connect(self._on_all_completed)

        # 队列视图信号 -> 任务管理器
        self._queue_view.remove_requested.connect(self._task_manager.remove_task)
        self._queue_view.pause_requested.connect(self._task_manager.pause_task)
        self._queue_view.resume_requested.connect(self._task_manager.resume_task)
        self._queue_view.cancel_requested.connect(self._task_manager.cancel_task)
        self._queue_view.move_up_requested.connect(self._task_manager.move_up)
        self._queue_view.move_down_requested.connect(self._task_manager.move_down)

    def _check_ffmpeg(self):
        """检查 ffmpeg 是否可用"""
        if ffmpeg_api.is_available():
            version = ffmpeg_api.get_version()
            self._ffmpeg_status.setText(f"✓ {version}")
            self._ffmpeg_status.setStyleSheet("color: #388E3C;")
            self._status_label.setText("ffmpeg 已就绪")
        else:
            self._ffmpeg_status.setText("✗ ffmpeg 未找到")
            self._ffmpeg_status.setStyleSheet("color: #D32F2F;")
            self._status_label.setText("警告: 未找到 ffmpeg，请安装 ffmpeg 并添加到 PATH 环境变量")
            QMessageBox.warning(
                self, "ffmpeg 未找到",
                "未找到 ffmpeg。\n\n"
                "请安装 ffmpeg:\n"
                "1. 从 https://ffmpeg.org/download.html 下载\n"
                "2. 将 ffmpeg.exe 所在目录添加到 PATH 环境变量\n"
                "3. 重启程序\n\n"
                "或者将 ffmpeg 可执行文件放入 resources/ffmpeg/ 目录"
            )

    def _on_add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择媒体文件", self._last_input_dir,
            "媒体文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v "
            "*.mp3 *.flac *.wav *.aac *.ogg *.opus *.wma);;所有文件 (*)"
        )
        if files:
            self._last_input_dir = os.path.dirname(files[0])
            self._save_last_input_dir(self._last_input_dir)
        for f in files:
            if f not in self._files:
                self._files.append(f)
                item = QListWidgetItem(os.path.basename(f))
                item.setToolTip(f)
                item.setData(Qt.UserRole, f)
                self._file_list.addItem(item)

    def _on_add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", self._last_input_dir)
        if folder:
            self._last_input_dir = folder
            self._save_last_input_dir(folder)
            media_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                          '.webm', '.m4v', '.mp3', '.flac', '.wav',
                          '.aac', '.ogg', '.opus', '.wma'}
            count = 0
            for root, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in media_exts:
                        full_path = os.path.join(root, f)
                        if full_path not in self._files:
                            self._files.append(full_path)
                            item = QListWidgetItem(os.path.basename(full_path))
                            item.setToolTip(full_path)
                            item.setData(Qt.UserRole, full_path)
                            self._file_list.addItem(item)
                            count += 1
            if count > 0:
                self._status_label.setText(f"已添加 {count} 个文件")
            else:
                QMessageBox.information(self, "提示", "文件夹中没有找到支持的媒体文件")

    def _on_remove_file(self):
        """移除选中的文件"""
        for item in self._file_list.selectedItems():
            file_path = item.data(Qt.UserRole)
            if file_path in self._files:
                self._files.remove(file_path)
            self._file_list.takeItem(self._file_list.row(item))

    def _on_clear_files(self):
        """清空文件列表"""
        self._files.clear()
        self._file_list.clear()

    def _update_empty_hint(self):
        """更新空文件列表提示"""
        has_files = self._file_list.count() > 0
        self._file_list.setVisible(has_files)
        self._empty_hint_container.setVisible(not has_files)
        self._add_queue_btn.setEnabled(has_files and ffmpeg_api.is_available())

    def _on_concurrent_changed(self, value: int):
        """并行数变更"""
        self._task_manager.max_concurrent = value

    def _on_add_to_queue(self):
        """将文件添加到任务队列并开始转换"""
        if not self._files:
            return

        if not ffmpeg_api.is_available():
            QMessageBox.warning(self, "错误", "未找到 ffmpeg，无法进行转换")
            return

        preset = self._config_panel.get_current_preset()

        # 获取输出目录
        output_dir = os.path.dirname(self._files[0])
        dir_dialog = QFileDialog.getExistingDirectory(
            self, "选择输出目录", output_dir
        )
        if not dir_dialog:
            return

        tasks = []
        for file_path in self._files:
            task = ConvertTask(file_path, dir_dialog, preset.copy())
            tasks.append(task)

        self._task_manager.add_tasks(tasks)
        self._task_manager.start_all()

        self._status_label.setText(f"已添加 {len(tasks)} 个转换任务")
        self._queue_view.set_buttons_enabled(True)

    def _on_start_all(self):
        """开始所有任务"""
        self._task_manager.start_all()

    def _on_clear_completed(self):
        """清除已完成的任务"""
        self._task_manager.clear_completed()

    def _on_task_added(self, task):
        """任务添加回调"""
        self._queue_view.add_task_row(task)
        self._update_stats()

    def _on_task_removed(self, task_id):
        """任务移除回调"""
        self._queue_view.remove_task_row(task_id)
        self._update_stats()

    def _on_task_progress(self, task_id, percent, status_text):
        """任务进度更新回调"""
        self._queue_view.update_progress(task_id, percent, status_text)

    def _on_task_status_changed(self, task_id, status):
        """任务状态变化回调"""
        self._queue_view.update_status(task_id, status)
        self._update_stats()
        if status == TaskStatus.COMPLETED:
            self._status_label.setText("任务转换完成")
        elif status == TaskStatus.FAILED:
            self._status_label.setText("任务转换失败")
        elif status == TaskStatus.CANCELLED:
            self._status_label.setText("任务已取消")

    def _on_all_completed(self):
        """所有任务完成回调"""
        self._status_label.setText("所有任务已完成")
        QMessageBox.information(self, "完成", "所有转换任务已完成!")

    def _update_stats(self):
        """更新统计信息"""
        tasks = self._task_manager.get_tasks()
        waiting = self._task_manager.get_waiting_count()
        active = self._task_manager.get_active_count()
        completed = self._task_manager.get_completed_count()
        failed = self._task_manager.get_failed_count()

        self._queue_view.update_task_info(
            len(tasks), waiting, active, completed, failed
        )

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 FFmpeg 格式转换器",
            "<h3>FFmpeg 格式转换器 v1.0</h3>"
            "<p>基于 PyQt5 和 ffmpeg 的可视化格式转换工具</p>"
            "<p>支持多种音视频格式的相互转换</p>"
            "<hr>"
            f"<p>ffmpeg 状态: {'✓ 可用' if ffmpeg_api.is_available() else '✗ 未找到'}</p>"
            f"<p>{ffmpeg_api.get_version()}</p>"
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖放进入"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """拖放释放"""
        saved_dir = ''
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                if file_path not in self._files:
                    self._files.append(file_path)
                    item = QListWidgetItem(os.path.basename(file_path))
                    item.setToolTip(file_path)
                    item.setData(Qt.UserRole, file_path)
                    self._file_list.addItem(item)
                    if not saved_dir:
                        saved_dir = os.path.dirname(file_path)
            elif os.path.isdir(file_path):
                if not saved_dir:
                    saved_dir = file_path
                # 如果是文件夹，递归添加
                media_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                              '.webm', '.m4v', '.mp3', '.flac', '.wav',
                              '.aac', '.ogg', '.opus', '.wma'}
                for root, dirs, files in os.walk(file_path):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in media_exts:
                            full_path = os.path.join(root, f)
                            if full_path not in self._files:
                                self._files.append(full_path)
                                item = QListWidgetItem(os.path.basename(full_path))
                                item.setToolTip(full_path)
                                item.setData(Qt.UserRole, full_path)
                                self._file_list.addItem(item)
        if saved_dir:
            self._last_input_dir = saved_dir
            self._save_last_input_dir(saved_dir)

    def closeEvent(self, event):
        """关闭窗口事件"""
        active_count = self._task_manager.get_active_count()
        if active_count > 0:
            reply = QMessageBox.question(
                self, "确认退出",
                f"还有 {active_count} 个任务正在转换，确定要退出吗?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self._task_manager.cancel_all()
        self._save_splitter()
        event.accept()
