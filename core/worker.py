"""转换工作线程模块"""

import os
import subprocess
import time
from PyQt5.QtCore import QThread, pyqtSignal

from core.progress_parser import ProgressParser, probe_duration
from core.ffmpeg_api import ffmpeg_api


class ConvertWorker(QThread):
    """单个转换任务的工作线程"""

    progress_updated = pyqtSignal(str, float, str)  # task_id, percent, status_text
    log_message = pyqtSignal(str, str)  # task_id, message
    finished = pyqtSignal(str, bool, str)  # task_id, success, message

    def __init__(self, task_id: str, input_file: str, output_file: str, params: dict, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.input_file = input_file
        self.output_file = output_file
        self.params = params
        self._is_cancelled = False
        self._is_paused = False
        self._process = None
        self._parser = ProgressParser()

    def run(self):
        """执行转换任务"""
        try:
            # 获取媒体时长
            duration = probe_duration(self.input_file)
            if duration > 0:
                self._parser.total_seconds = duration
            else:
                self._parser.total_seconds = 0

            self.log_message.emit(self.task_id, f"开始转换: {os.path.basename(self.input_file)}")
            self.log_message.emit(self.task_id, f"输出: {os.path.basename(self.output_file)}")

            # 构建 ffmpeg 命令
            cmd = ffmpeg_api.build_command(
                self.input_file, self.output_file, self.params
            )

            self.log_message.emit(self.task_id, f"命令: {' '.join(cmd)}")

            # 启动 ffmpeg 进程
            # Windows 需显式指定 utf-8 编码，否则含日文/特殊字符的输出会因 GBK 解码失败
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # 实时读取 stderr 获取进度，同时缓存错误输出
            stderr_lines = []
            for line in iter(self._process.stderr.readline, ''):
                stderr_lines.append(line)

                # 检查是否被取消
                if self._is_cancelled:
                    self._process.terminate()
                    self._process.wait()
                    self.finished.emit(self.task_id, False, "任务已取消")
                    return

                # 暂停支持
                while self._is_paused:
                    if self._is_cancelled:
                        self._process.terminate()
                        self._process.wait()
                        self.finished.emit(self.task_id, False, "任务已取消")
                        return
                    time.sleep(0.1)

                # 解析时长（第一次出现时）
                self._parser.parse_duration(line)

                # 解析进度
                progress = self._parser.parse_progress(line)

                if progress['percent'] > 0:
                    # 音频转换可能没有帧率和速度信息
                    speed_str = f" | {progress['speed']}" if progress['speed'] != '0x' else ""
                    fps_str = f" | FPS:{progress['fps']:.0f}" if progress['fps'] > 0 else ""
                    status = f"{progress['percent']:.1f}%{speed_str}{fps_str}"
                    self.progress_updated.emit(
                        self.task_id, progress['percent'], status
                    )

            # 等待进程结束
            self._process.wait()

            if self._is_cancelled:
                self.finished.emit(self.task_id, False, "任务已取消")
                return

            if self._process.returncode == 0:
                # 验证输出文件
                if os.path.isfile(self.output_file):
                    size = os.path.getsize(self.output_file)
                    size_str = self._format_size(size)
                    self.progress_updated.emit(self.task_id, 100.0, "已完成")
                    self.finished.emit(
                        self.task_id, True,
                        f"转换完成! 输出文件: {os.path.basename(self.output_file)} ({size_str})"
                    )
                else:
                    self.finished.emit(self.task_id, False, "输出文件未生成")
            else:
                # 使用已缓存的 stderr
                stderr_output = "".join(stderr_lines)
                error_msg = f"ffmpeg 返回错误码 {self._process.returncode}"
                if stderr_output:
                    lines = stderr_output.strip().split('\n')
                    # 只保留最后几行（最相关的错误信息）
                    error_lines = [l for l in lines if 'Error' in l or 'error' in l or 'Invalid' in l
                                   or 'Cannot' in l or 'failed' in l]
                    if error_lines:
                        error_msg += "\n" + "\n".join(error_lines[-5:])
                    elif len(lines) > 5:
                        error_msg += "\n" + "\n".join(lines[-5:])
                    else:
                        error_msg += "\n" + stderr_output
                self.finished.emit(self.task_id, False, error_msg)

        except FileNotFoundError:
            self.finished.emit(self.task_id, False, "未找到 ffmpeg，请确保已安装 ffmpeg 并添加到环境变量")
        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(self.task_id, False, f"转换出错: {str(e)}")

    def cancel(self):
        """取消任务 - 立即终止 ffmpeg 进程"""
        self._is_cancelled = True
        if self._process:
            try:
                # 1. 关闭 stderr 管道，解除 readline() 阻塞
                if self._process.stderr:
                    self._process.stderr.close()
            except Exception:
                pass
            try:
                # 2. 终止 ffmpeg 进程
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(self._process.pid)],
                        capture_output=True, timeout=5
                    )
                else:
                    self._process.terminate()
                    self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

    def pause(self):
        """暂停任务"""
        self._is_paused = True

    def resume(self):
        """恢复任务"""
        self._is_paused = False

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
