"""任务队列界面模块"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton,
    QProgressBar, QLabel, QFrame, QAbstractItemView,
    QMenu, QAction, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon, QPalette

from core.task_manager import TaskManager, TaskStatus, ConvertTask


class TaskQueueView(QWidget):
    """任务队列界面 - 显示和管理转换任务列表"""

    remove_requested = pyqtSignal(str)
    pause_requested = pyqtSignal(str)
    resume_requested = pyqtSignal(str)
    cancel_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题栏
        title_layout = QHBoxLayout()
        title = QLabel("任务队列")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        title_layout.addWidget(title)

        self._info_label = QLabel("总计: 0 | 等待: 0 | 转换中: 0 | 完成: 0 | 失败: 0")
        self._info_label.setStyleSheet("color: #666; font-size: 12px;")
        title_layout.addWidget(self._info_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 工具栏
        toolbar = QHBoxLayout()
        self._start_all_btn = QPushButton("开始全部")
        self._start_all_btn.setEnabled(False)
        self._pause_all_btn = QPushButton("暂停全部")
        self._pause_all_btn.setEnabled(False)
        self._resume_all_btn = QPushButton("恢复全部")
        self._resume_all_btn.setEnabled(False)
        self._cancel_all_btn = QPushButton("取消全部")
        self._cancel_all_btn.setEnabled(False)
        self._clear_completed_btn = QPushButton("清除已完成")

        for btn in [self._start_all_btn, self._pause_all_btn, self._resume_all_btn,
                    self._cancel_all_btn, self._clear_completed_btn]:
            btn.setFixedHeight(28)
            toolbar.addWidget(btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 表头
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["文件名", "输出格式", "进度", "状态", "操作", "任务ID"])
        self._table.setColumnHidden(5, True)  # 隐藏任务 ID 列

        # 表格设置
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.setColumnWidth(4, 120)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._table)

        # 空状态提示 - 容器包裹 + 底部弹性空间，确保顶部对齐
        self._empty_container = QWidget()
        empty_layout = QVBoxLayout(self._empty_container)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        self._empty_label = QLabel('暂无任务\n\n点击"添加文件"或拖拽文件到左侧区域添加转换任务')
        self._empty_label.setAlignment(Qt.AlignHCenter)
        self._empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
        empty_layout.addWidget(self._empty_label)
        empty_layout.addStretch()
        self._empty_container.hide()
        layout.addWidget(self._empty_container)

        # 连接信号
        self._start_all_btn.clicked.connect(lambda: self.parent().parent()._on_start_all() if hasattr(self.parent().parent(), '_on_start_all') else None)
        self._pause_all_btn.clicked.connect(self.pause_all)
        self._resume_all_btn.clicked.connect(self.resume_all)
        self._cancel_all_btn.clicked.connect(self.cancel_all)
        self._clear_completed_btn.clicked.connect(self.clear_completed)

        self._update_empty_state()

    def add_task_row(self, task: ConvertTask):
        """添加任务行"""
        row = self._table.rowCount()
        self._table.insertRow(row)

        # 文件名
        file_name = os.path.basename(task.input_file)
        name_item = QTableWidgetItem(file_name)
        name_item.setToolTip(task.input_file)
        self._table.setItem(row, 0, name_item)

        # 输出格式
        fmt_item = QTableWidgetItem(task.preset.extension.upper())
        fmt_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 1, fmt_item)

        # 进度条
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(2, 1, 2, 1)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setFixedWidth(140)
        progress_bar.setFixedHeight(15)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%p%")
        progress_layout.addWidget(progress_bar)
        progress_layout.addStretch()
        self._table.setCellWidget(row, 2, progress_widget)

        # 状态
        status_item = QTableWidgetItem(task.status.value)
        status_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 3, status_item)

        # 操作按钮
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(1, 0, 1, 3)
        action_layout.setSpacing(2)

        pause_btn = QPushButton("暂停")
        pause_btn.setFixedSize(48, 19)
        pause_btn.setStyleSheet("font-size: 10px; padding: 0px 4px;")
        pause_btn.setProperty("task_id", task.task_id)
        pause_btn.clicked.connect(lambda: self._on_pause_click(task.task_id))

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(48, 19)
        cancel_btn.setStyleSheet("font-size: 10px; padding: 0px 4px;")
        cancel_btn.setProperty("task_id", task.task_id)
        cancel_btn.clicked.connect(lambda: self._on_cancel_click(task.task_id))

        action_layout.addWidget(pause_btn)
        action_layout.addWidget(cancel_btn)
        action_layout.addStretch()
        self._table.setCellWidget(row, 4, action_widget)

        # 任务 ID
        id_item = QTableWidgetItem(task.task_id)
        self._table.setItem(row, 5, id_item)

        self._update_empty_state()

    def remove_task_row(self, task_id: str):
        """移除任务行"""
        for row in range(self._table.rowCount()):
            if self._table.item(row, 5) and self._table.item(row, 5).text() == task_id:
                self._table.removeRow(row)
                break
        self._update_empty_state()

    def update_progress(self, task_id: str, percent: float, status_text: str):
        """更新任务进度"""
        for row in range(self._table.rowCount()):
            if self._table.item(row, 5) and self._table.item(row, 5).text() == task_id:
                # 更新进度条
                progress_widget = self._table.cellWidget(row, 2)
                if progress_widget:
                    progress_bar = progress_widget.findChild(QProgressBar)
                    if progress_bar:
                        progress_bar.setValue(int(percent))
                        progress_bar.setFormat(f"{percent:.1f}%")

                # 更新状态文本
                status_item = self._table.item(row, 3)
                if status_item:
                    status_item.setText(status_text)
                break

    def update_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        for row in range(self._table.rowCount()):
            if self._table.item(row, 5) and self._table.item(row, 5).text() == task_id:
                status_item = self._table.item(row, 3)
                if status_item:
                    # 颜色标记
                    color_map = {
                        TaskStatus.WAITING: QColor("#666"),
                        TaskStatus.CONVERTING: QColor("#1976D2"),
                        TaskStatus.PAUSED: QColor("#F57C00"),
                        TaskStatus.COMPLETED: QColor("#388E3C"),
                        TaskStatus.FAILED: QColor("#D32F2F"),
                        TaskStatus.CANCELLED: QColor("#9E9E9E"),
                    }
                    status_item.setForeground(QBrush(color_map.get(status, QColor("#666"))))
                    status_item.setText(status.value)
                break

    def update_task_info(self, total: int, waiting: int, active: int,
                         completed: int, failed: int):
        """更新统计信息"""
        self._info_label.setText(
            f"总计: {total} | 等待: {waiting} | 转换中: {active} "
            f"| 完成: {completed} | 失败: {failed}"
        )

    def _update_empty_state(self):
        """更新空状态显示"""
        has_tasks = self._table.rowCount() > 0
        self._table.setVisible(has_tasks)
        self._empty_container.setVisible(not has_tasks)

    def _show_context_menu(self, pos):
        """右键菜单"""
        row = self._table.rowAt(pos.y())
        if row < 0:
            return

        task_id_item = self._table.item(row, 5)
        if not task_id_item:
            return
        task_id = task_id_item.text()

        menu = QMenu(self)

        pause_action = menu.addAction("暂停")
        pause_action.triggered.connect(lambda: self.pause_requested.emit(task_id))

        resume_action = menu.addAction("恢复")
        resume_action.triggered.connect(lambda: self.resume_requested.emit(task_id))

        menu.addSeparator()

        move_up_action = menu.addAction("上移")
        move_up_action.triggered.connect(lambda: self.move_up_requested.emit(task_id))

        move_down_action = menu.addAction("下移")
        move_down_action.triggered.connect(lambda: self.move_down_requested.emit(task_id))

        menu.addSeparator()

        cancel_action = menu.addAction("取消")
        cancel_action.triggered.connect(lambda: self.cancel_requested.emit(task_id))

        remove_action = menu.addAction("移除")
        remove_action.triggered.connect(lambda: self.remove_requested.emit(task_id))

        menu.exec_(self._table.viewport().mapToGlobal(pos))

    def _on_pause_click(self, task_id: str):
        self.pause_requested.emit(task_id)

    def _on_cancel_click(self, task_id: str):
        self.cancel_requested.emit(task_id)

    def pause_all(self):
        """暂停全部按钮点击"""
        for row in range(self._table.rowCount()):
            task_id = self._table.item(row, 5).text() if self._table.item(row, 5) else ""
            if task_id:
                self.pause_requested.emit(task_id)

    def resume_all(self):
        """恢复全部按钮点击"""
        for row in range(self._table.rowCount()):
            task_id = self._table.item(row, 5).text() if self._table.item(row, 5) else ""
            if task_id:
                self.resume_requested.emit(task_id)

    def cancel_all(self):
        """取消全部按钮点击"""
        for row in range(self._table.rowCount()):
            task_id = self._table.item(row, 5).text() if self._table.item(row, 5) else ""
            if task_id:
                self.cancel_requested.emit(task_id)

    def clear_completed(self):
        """清除已完成任务"""
        self.parent().parent()._on_clear_completed() if hasattr(self.parent().parent(), '_on_clear_completed') else None

    def set_buttons_enabled(self, has_tasks: bool):
        """设置按钮启用状态"""
        self._start_all_btn.setEnabled(has_tasks)
        self._pause_all_btn.setEnabled(has_tasks)
        self._resume_all_btn.setEnabled(has_tasks)
        self._cancel_all_btn.setEnabled(has_tasks)
