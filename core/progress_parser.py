"""ffmpeg 进度解析模块"""

import re
import subprocess
import json


class ProgressParser:
    """解析 ffmpeg stderr 输出中的进度信息"""

    TIME_RE = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')
    SPEED_RE = re.compile(r'speed=\s*([\d.]+)x')
    FRAME_RE = re.compile(r'frame=\s*(\d+)')
    FPS_RE = re.compile(r'fps=\s*([\d.]+)')
    BITRATE_RE = re.compile(r'bitrate=\s*([\d.]+)kbits/s')
    SIZE_RE = re.compile(r'size=\s*(\d+)(kB|MB)')
    DURATION_RE = re.compile(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)')

    def __init__(self):
        self.total_seconds = 0
        self.current_seconds = 0
        self.speed = 0
        self.fps = 0
        self.frame = 0
        self.bitrate = 0
        self.output_size = 0
        self.percent = 0

    def parse_duration(self, line: str) -> float:
        """从 ffmpeg 输出中解析视频总时长"""
        match = self.DURATION_RE.search(line)
        if match:
            h, m, s, ms = map(int, match.groups())
            self.total_seconds = h * 3600 + m * 60 + s + ms / 100
            return self.total_seconds
        return 0

    def parse_progress(self, line: str) -> dict:
        """解析进度行，返回进度信息字典"""
        result = {
            'percent': 0,
            'current_seconds': 0,
            'speed': '0x',
            'fps': 0,
            'frame': 0,
            'bitrate': 0,
            'output_size': '',
        }

        time_match = self.TIME_RE.search(line)
        if time_match:
            h, m, s, ms = map(int, time_match.groups())
            self.current_seconds = h * 3600 + m * 60 + s + ms / 100
            result['current_seconds'] = self.current_seconds

            if self.total_seconds > 0:
                self.percent = min(99.9, (self.current_seconds / self.total_seconds) * 100)
                result['percent'] = self.percent

        speed_match = self.SPEED_RE.search(line)
        if speed_match:
            self.speed = speed_match.group(1)
            result['speed'] = f"{self.speed}x"

        frame_match = self.FRAME_RE.search(line)
        if frame_match:
            self.frame = int(frame_match.group(1))
            result['frame'] = self.frame

        fps_match = self.FPS_RE.search(line)
        if fps_match:
            self.fps = float(fps_match.group(1))
            result['fps'] = self.fps

        bitrate_match = self.BITRATE_RE.search(line)
        if bitrate_match:
            self.bitrate = float(bitrate_match.group(1))
            result['bitrate'] = self.bitrate

        size_match = self.SIZE_RE.search(line)
        if size_match:
            val = int(size_match.group(1))
            unit = size_match.group(2)
            self.output_size = f"{val} {unit}"
            result['output_size'] = self.output_size

        return result

    def reset(self):
        """重置解析器状态"""
        self.total_seconds = 0
        self.current_seconds = 0
        self.speed = 0
        self.fps = 0
        self.frame = 0
        self.bitrate = 0
        self.output_size = 0
        self.percent = 0


def probe_duration(file_path: str) -> float:
    """使用 ffprobe 获取媒体文件时长（秒）"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration_str = data.get('format', {}).get('duration', '0')
            return float(duration_str)
    except Exception:
        pass
    return 0


def probe_media_info(file_path: str) -> dict:
    """获取媒体的完整信息"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}
