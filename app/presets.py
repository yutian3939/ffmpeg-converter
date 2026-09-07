"""格式预设管理模块"""

import json
import os
from typing import Optional


class FormatPreset:
    """格式转换预设"""

    def __init__(
        self,
        name: str = "自定义",
        extension: str = ".mp4",
        video_codec: str = "libx264",
        video_bitrate: str = "",
        video_bitrate_mode: str = "vbr",
        width: int = 0,
        height: int = 0,
        framerate: str = "original",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        sample_rate: int = 44100,
        channels: int = 2,
        hwaccel: str = "none",
        start_time: str = "",
        duration: str = "",
        additional_args: list = None,
    ):
        self.name = name
        self.extension = extension
        self.video_codec = video_codec
        self.video_bitrate = video_bitrate
        self.video_bitrate_mode = video_bitrate_mode
        self.width = width
        self.height = height
        self.framerate = framerate
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate
        self.sample_rate = sample_rate
        self.channels = channels
        self.hwaccel = hwaccel
        self.start_time = start_time
        self.duration = duration
        self.additional_args = additional_args or []

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'extension': self.extension,
            'video_codec': self.video_codec,
            'video_bitrate': self.video_bitrate,
            'video_bitrate_mode': self.video_bitrate_mode,
            'width': self.width,
            'height': self.height,
            'framerate': self.framerate,
            'audio_codec': self.audio_codec,
            'audio_bitrate': self.audio_bitrate,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'hwaccel': self.hwaccel,
            'start_time': self.start_time,
            'duration': self.duration,
            'additional_args': self.additional_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FormatPreset':
        return cls(**data)

    def copy(self) -> 'FormatPreset':
        return FormatPreset.from_dict(self.to_dict())

    def is_audio_only(self) -> bool:
        return self.video_codec == 'none'

    def is_video_only(self) -> bool:
        return self.audio_codec == 'none'


class PresetManager:
    """预设管理器 - 管理内置预设和用户自定义预设"""

    def __init__(self, settings_path: str = None):
        if settings_path is None:
            from core.ffmpeg_api import get_settings_path
            settings_path = get_settings_path()
        self.settings_path = settings_path
        self._presets: dict[str, FormatPreset] = {}
        self.last_preset: str = "MP4 (H.264)"
        self.last_hwaccel: str = "none"
        self._load_builtin_presets()
        self._load_user_presets()

    def _load_builtin_presets(self):
        """加载内置预设"""
        builtins = [
            FormatPreset("MP4 (H.264)", ".mp4", "libx264", "2000k", "vbr",
                         0, 0, "original", "aac", "192k", 44100, 2),
            FormatPreset("MP4 (H.265/HEVC)", ".mp4", "libx265", "1500k", "vbr",
                         0, 0, "original", "aac", "192k", 44100, 2),
            FormatPreset("MKV (H.264)", ".mkv", "libx264", "2000k", "vbr",
                         0, 0, "original", "aac", "192k", 44100, 2),
            FormatPreset("WebM (VP9)", ".webm", "libvpx-vp9", "1000k", "vbr",
                         0, 0, "original", "libopus", "128k", 48000, 2),
            FormatPreset("WebM (VP8)", ".webm", "libvpx", "1500k", "vbr",
                         0, 0, "original", "libvorbis", "128k", 44100, 2),
            FormatPreset("AVI", ".avi", "libx264", "2500k", "vbr",
                         0, 0, "original", "mp3", "192k", 44100, 2),
            FormatPreset("MOV", ".mov", "libx264", "2000k", "vbr",
                         0, 0, "original", "aac", "192k", 44100, 2),
            FormatPreset("GIF 动画", ".gif", "gif", "", "vbr",
                         0, 0, "15", "none", "", 0, 0),
            FormatPreset("MP3 音频", ".mp3", "none", "", "vbr",
                         0, 0, "original", "libmp3lame", "192k", 44100, 2),
            FormatPreset("FLAC 音频", ".flac", "none", "", "vbr",
                         0, 0, "original", "flac", "", 44100, 2),
            FormatPreset("WAV 音频", ".wav", "none", "", "vbr",
                         0, 0, "original", "pcm_s16le", "", 44100, 2),
            FormatPreset("AAC 音频", ".aac", "none", "", "vbr",
                         0, 0, "original", "aac", "192k", 44100, 2),
            FormatPreset("720p 高清", ".mp4", "libx264", "2500k", "vbr",
                         1280, 720, "30", "aac", "192k", 44100, 2),
            FormatPreset("1080p 全高清", ".mp4", "libx264", "5000k", "vbr",
                         1920, 1080, "30", "aac", "256k", 48000, 2),
            FormatPreset("4K 超高清", ".mp4", "libx265", "10000k", "vbr",
                         3840, 2160, "30", "aac", "256k", 48000, 2),
        ]
        for p in builtins:
            self._presets[p.name] = p

    def _load_user_presets(self):
        """从 JSON 文件加载用户预设及上次选择"""
        try:
            if os.path.isfile(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                user_presets = data.get('user_presets', [])
                for p_data in user_presets:
                    preset = FormatPreset.from_dict(p_data)
                    self._presets[preset.name] = preset
                # 恢复上次选择的预设和硬件加速
                self.last_preset = data.get('last_preset', 'MP4 (H.264)')
                self.last_hwaccel = data.get('last_hwaccel', 'none')
        except Exception:
            pass

    def save_user_presets(self):
        """保存用户预设及当前选择到 JSON 文件"""
        try:
            existing_data = {}
            if os.path.isfile(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # 只保存用户自定义的预设
            builtin_names = {
                "MP4 (H.264)", "MP4 (H.265/HEVC)", "MKV (H.264)",
                "WebM (VP9)", "WebM (VP8)", "AVI", "MOV",
                "GIF 动画", "MP3 音频", "FLAC 音频", "WAV 音频",
                "AAC 音频", "720p 高清", "1080p 全高清", "4K 超高清",
            }
            user_presets = [
                p.to_dict() for p in self._presets.values()
                if p.name not in builtin_names
            ]
            existing_data['user_presets'] = user_presets
            existing_data['last_preset'] = self.last_preset
            existing_data['last_hwaccel'] = self.last_hwaccel

            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存预设失败: {e}")

    def get_preset(self, name: str) -> Optional[FormatPreset]:
        return self._presets.get(name)

    def get_preset_names(self) -> list[str]:
        return list(self._presets.keys())

    def add_preset(self, preset: FormatPreset):
        self._presets[preset.name] = preset
        self.save_user_presets()

    def remove_preset(self, name: str):
        if name in self._presets:
            del self._presets[name]
            self.save_user_presets()

    def get_builtin_names(self) -> set:
        return {
            "MP4 (H.264)", "MP4 (H.265/HEVC)", "MKV (H.264)",
            "WebM (VP9)", "WebM (VP8)", "AVI", "MOV",
            "GIF 动画", "MP3 音频", "FLAC 音频", "WAV 音频",
            "AAC 音频", "720p 高清", "1080p 全高清", "4K 超高清",
        }


# 全局实例
preset_manager = PresetManager()
