"""任务调度器模块"""

import uuid
import os
from enum import Enum
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

from core.worker import ConvertWorker
from app.presets import FormatPreset


class TaskStatus(Enum):
    WAITING = '等待中'
    CONVERTING = '转换中'
    PAUSED = '已暂停'
    COMPLETED = '已完成'
    FAILED = '失败'
    CANCELLED = '已取消'


class ConvertTask:
    """单个转换任务"""

    def __init__(self, input_file: str, output_dir: str, preset: FormatPreset):
        self.task_id = str(uuid.uuid4())[:8]
        self.input_file = input_file
        self.output_dir = output_dir
        self.preset = preset
        self.status = TaskStatus.WAITING
        self.progress = 0.0
        self.status_text = '等待中'
        self.error_message = ''
        self.output_file = self._generate_output_path()
        self.priority = 0  # 数值越大优先级越高
        self._worker: Optional[ConvertWorker] = None

    def _generate_output_path(self) -> str:
        """生成输出文件路径"""
        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        ext = self.preset.extension
        output_name = f"{base_name}_converted{ext}"
        return os.path.join(self.output_dir, output_name)

    def get_params(self) -> dict:
        """获取转换参数字典"""
        params = {
            'video_codec': self.preset.video_codec,
            'audio_codec': self.preset.audio_codec,
            'hwaccel': self.preset.hwaccel,
            'additional_args': self.preset.additional_args,
        }

        # 视频参数
        if self.preset.video_bitrate:
            params['video_bitrate'] = self.preset.video_bitrate
            params['video_bitrate_mode'] = self.preset.video_bitrate_mode
        if self.preset.width and self.preset.height:
            params['width'] = self.preset.width
            params['height'] = self.preset.height
        if self.preset.framerate and self.preset.framerate != 'original':
            params['framerate'] = self.preset.framerate
        if self.preset.start_time:
            params['start_time'] = self.preset.start_time
        if self.preset.duration:
            params['duration'] = self.preset.duration

        # 音频参数
        if self.preset.audio_bitrate:
            params['audio_bitrate'] = self.preset.audio_bitrate
        if self.preset.sample_rate:
            params['sample_rate'] = self.preset.sample_rate
        if self.preset.channels:
            params['channels'] = self.preset.channels

        return params


class TaskManager(QObject):
    """任务管理器 - 调度和控制所有转换任务"""

    task_added = pyqtSignal(object)  # ConvertTask
    task_removed = pyqtSignal(str)  # task_id
    task_status_changed = pyqtSignal(str, object)  # task_id, TaskStatus
    task_progress_updated = pyqtSignal(str, float, str)  # task_id, percent, status_text
    all_tasks_completed = pyqtSignal()

    def __init__(self, max_concurrent: int = 2):
        super().__init__()
        self._tasks: list[ConvertTask] = []
        self._active_tasks: dict[str, ConvertTask] = {}
        self._max_concurrent = max_concurrent
        self._is_running = False

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int):
        self._max_concurrent = max(1, min(value, 8))

    def add_task(self, task: ConvertTask):
        """添加任务到队列"""
        self._tasks.append(task)
        self.task_added.emit(task)
        # 如果正在运行，尝试立即启动
        if self._is_running:
            self._try_start_next()

    def add_tasks(self, tasks: list[ConvertTask]):
        """批量添加任务"""
        for task in tasks:
            self._tasks.append(task)
            self.task_added.emit(task)
        if self._is_running:
            self._try_start_next()

    def remove_task(self, task_id: str):
        """从队列移除任务"""
        task = self.get_task(task_id)
        if task:
            if task.status == TaskStatus.CONVERTING:
                task._worker.cancel()
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
            self._tasks = [t for t in self._tasks if t.task_id != task_id]
            self.task_removed.emit(task_id)

    def get_task(self, task_id: str) -> Optional[ConvertTask]:
        """根据 ID 获取任务"""
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_tasks(self) -> list[ConvertTask]:
        """获取所有任务"""
        return self._tasks.copy()

    def get_waiting_count(self) -> int:
        """获取等待中的任务数"""
        return sum(1 for t in self._tasks if t.status == TaskStatus.WAITING)

    def get_active_count(self) -> int:
        """获取正在转换的任务数"""
        return sum(1 for t in self._tasks if t.status == TaskStatus.CONVERTING)

    def get_completed_count(self) -> int:
        """获取已完成的任务数"""
        return sum(1 for t in self._tasks if t.status == TaskStatus.COMPLETED)

    def get_failed_count(self) -> int:
        """获取失败的任务数"""
        return sum(1 for t in self._tasks if t.status == TaskStatus.FAILED)

    def start_all(self):
        """开始所有等待中的任务"""
        self._is_running = True
        self._try_start_next()

    def _try_start_next(self):
        """尝试启动下一个等待任务"""
        while len(self._active_tasks) < self._max_concurrent:
            # 优先启动高优先级任务
            waiting = [t for t in self._tasks
                       if t.status == TaskStatus.WAITING]
            if not waiting:
                # 检查是否所有任务都完成了
                active = [t for t in self._tasks
                          if t.status in (TaskStatus.CONVERTING, TaskStatus.PAUSED)]
                if not active:
                    self._is_running = False
                    self.all_tasks_completed.emit()
                return

            # 按优先级排序
            waiting.sort(key=lambda t: t.priority, reverse=True)
            task = waiting[0]
            self._start_task(task)

    def _start_task(self, task: ConvertTask):
        """启动单个任务"""
        task.status = TaskStatus.CONVERTING
        task.status_text = '正在启动...'
        self._active_tasks[task.task_id] = task
        self.task_status_changed.emit(task.task_id, TaskStatus.CONVERTING)

        worker = ConvertWorker(
            task.task_id,
            task.input_file,
            task.output_file,
            task.get_params()
        )
        task._worker = worker

        worker.progress_updated.connect(self._on_progress_updated)
        worker.log_message.connect(self._on_log_message)
        worker.finished.connect(self._on_task_finished)

        worker.start()

    def _on_progress_updated(self, task_id: str, percent: float, status_text: str):
        """处理进度更新"""
        task = self.get_task(task_id)
        if task:
            task.progress = percent
            task.status_text = status_text
            self.task_progress_updated.emit(task_id, percent, status_text)

    def _on_log_message(self, task_id: str, message: str):
        """处理日志消息"""
        pass  # 可以连接到日志系统

    def _on_task_finished(self, task_id: str, success: bool, message: str):
        """处理任务完成"""
        task = self.get_task(task_id)
        if task:
            # 已被取消/移除的任务，忽略后续 finished 信号
            if task.status in (TaskStatus.CANCELLED,):
                return

            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

            if success:
                task.status = TaskStatus.COMPLETED
                task.progress = 100.0
                task.status_text = '已完成'
            else:
                task.status = TaskStatus.FAILED
                task.error_message = message
                task.status_text = '失败'

            self.task_status_changed.emit(task_id, task.status)

            # 尝试启动下一个任务
            if self._is_running:
                self._try_start_next()

    def pause_task(self, task_id: str):
        """暂停任务"""
        task = self.get_task(task_id)
        if task and task._worker and task.status == TaskStatus.CONVERTING:
            task._worker.pause()
            task.status = TaskStatus.PAUSED
            task.status_text = '已暂停'
            self.task_status_changed.emit(task_id, TaskStatus.PAUSED)

    def resume_task(self, task_id: str):
        """恢复暂停的任务"""
        task = self.get_task(task_id)
        if task and task._worker and task.status == TaskStatus.PAUSED:
            task._worker.resume()
            task.status = TaskStatus.CONVERTING
            task.status_text = '恢复中...'
            self.task_status_changed.emit(task_id, TaskStatus.CONVERTING)

    def cancel_task(self, task_id: str):
        """取消任务"""
        task = self.get_task(task_id)
        if task:
            if task._worker and task.status in (TaskStatus.CONVERTING, TaskStatus.PAUSED):
                task._worker.cancel()
                # 不调用 worker.wait() — 主线程不阻塞，finished 信号会触发清理
                # 但直接标记为 CANCELLED，防止 _on_task_finished 覆盖为 FAILED
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            task.status_text = '已取消'
            self.task_status_changed.emit(task_id, TaskStatus.CANCELLED)

            if self._is_running:
                self._try_start_next()

    def cancel_all(self):
        """取消所有任务"""
        for task in self._tasks:
            if task.status in (TaskStatus.CONVERTING, TaskStatus.PAUSED, TaskStatus.WAITING):
                self.cancel_task(task.task_id)

    def pause_all(self):
        """暂停所有任务"""
        for task in self._tasks:
            if task.status == TaskStatus.CONVERTING:
                self.pause_task(task.task_id)

    def resume_all(self):
        """恢复所有暂停的任务"""
        for task in self._tasks:
            if task.status == TaskStatus.PAUSED:
                self.resume_task(task.task_id)

    def clear_completed(self):
        """清除已完成/失败/取消的任务"""
        done_statuses = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        self._tasks = [t for t in self._tasks if t.status not in done_statuses]

    def move_up(self, task_id: str):
        """上移任务"""
        for i, task in enumerate(self._tasks):
            if task.task_id == task_id and i > 0:
                self._tasks[i], self._tasks[i - 1] = self._tasks[i - 1], self._tasks[i]
                break

    def move_down(self, task_id: str):
        """下移任务"""
        for i, task in enumerate(self._tasks):
            if task.task_id == task_id and i < len(self._tasks) - 1:
                self._tasks[i], self._tasks[i + 1] = self._tasks[i + 1], self._tasks[i]
                break
