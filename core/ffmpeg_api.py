"""ffmpeg 命令封装模块"""

import os
import sys
import shutil
import subprocess
import platform
from typing import Optional


def _resource_base() -> str:
    """获取资源根目录（支持 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS  # type: ignore
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_settings_path() -> str:
    """获取可写的 settings.json 路径（打包后存到 AppData，开发环境存到项目根目录）"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                               'FFmpegConverter')
        os.makedirs(app_dir, exist_ok=True)
        settings_path = os.path.join(app_dir, 'settings.json')
        # 首次运行时从包内复制默认配置
        if not os.path.isfile(settings_path):
            src = os.path.join(_resource_base(), 'settings.json')
            if os.path.isfile(src):
                import shutil
                shutil.copy2(src, settings_path)
        return settings_path
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'settings.json')


class FFmpegAPI:
    """ffmpeg 命令行封装"""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()

    def _find_ffmpeg(self) -> Optional[str]:
        """查找 ffmpeg 可执行文件路径"""
        # 1. 检查嵌入式 ffmpeg
        embedded = os.path.join(_resource_base(), 'resources', 'ffmpeg')
        if platform.system() == 'Windows':
            embedded_exe = os.path.join(embedded, 'ffmpeg.exe')
        else:
            embedded_exe = os.path.join(embedded, 'ffmpeg')

        if os.path.isfile(embedded_exe):
            return embedded_exe

        # 2. 检查环境变量
        path = shutil.which('ffmpeg')
        if path:
            return path

        return None

    def _find_ffprobe(self) -> Optional[str]:
        """查找 ffprobe 可执行文件路径"""
        embedded = os.path.join(_resource_base(), 'resources', 'ffmpeg')
        if platform.system() == 'Windows':
            embedded_exe = os.path.join(embedded, 'ffprobe.exe')
        else:
            embedded_exe = os.path.join(embedded, 'ffprobe')

        if os.path.isfile(embedded_exe):
            return embedded_exe

        path = shutil.which('ffprobe')
        if path:
            return path

        return None

    def is_available(self) -> bool:
        """检查 ffmpeg 是否可用"""
        return self.ffmpeg_path is not None

    def get_version(self) -> str:
        """获取 ffmpeg 版本信息"""
        if not self.ffmpeg_path:
            return "未找到 ffmpeg"
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True, text=True, timeout=10
            )
            first_line = result.stdout.split('\n')[0]
            return first_line.strip()
        except Exception:
            return "无法获取版本信息"

    def get_encoders(self) -> dict:
        """获取可用的编码器列表"""
        encoders = {
            'video': [],
            'audio': [],
        }
        if not self.ffmpeg_path:
            return encoders

        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('Encoders'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        codec = parts[1]
                        if line.startswith(' '):
                            if 'V' in parts[0] if len(parts[0]) > 0 else False:
                                encoders['video'].append(codec)
                            elif 'A' in parts[0] if len(parts[0]) > 0 else False:
                                encoders['audio'].append(codec)
        except Exception:
            pass

        return encoders

    def get_hw_accel_methods(self) -> list:
        """检测可用的硬件加速方法"""
        methods = ['none']
        if not self.ffmpeg_path:
            return methods

        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-hwaccels'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Hardware'):
                    methods.append(line.lower())
        except Exception:
            pass

        return methods

    def check_encoder_available(self, encoder: str) -> bool:
        """检查指定编码器是否可用"""
        encoders = self.get_encoders()
        all_encoders = encoders['video'] + encoders['audio']
        return encoder in all_encoders

    def build_command(
        self,
        input_file: str,
        output_file: str,
        params: dict
    ) -> list:
        """构建 ffmpeg 命令行

        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            params: 转换参数字典，包含:
                - video_codec: 视频编码器
                - video_bitrate: 视频码率 (如 '2000k')
                - video_bitrate_mode: 'cbr' 或 'vbr'
                - width: 视频宽度
                - height: 视频高度
                - framerate: 帧率
                - audio_codec: 音频编码器
                - audio_bitrate: 音频码率 (如 '192k')
                - sample_rate: 采样率
                - channels: 声道数
                - hwaccel: 硬件加速方法
                - start_time: 开始时间
                - duration: 持续时长
                - additional_args: 附加参数列表
        """
        cmd = [self.ffmpeg_path, '-y']

        # 硬件加速
        hwaccel = params.get('hwaccel', 'none')
        if hwaccel and hwaccel != 'none':
            cmd.extend(['-hwaccel', hwaccel])

        # 输入文件
        cmd.extend(['-i', input_file])

        # 开始时间 / 持续时长 (裁剪)
        start_time = params.get('start_time')
        if start_time:
            cmd.extend(['-ss', start_time])
        duration = params.get('duration')
        if duration:
            cmd.extend(['-t', duration])

        # 视频参数
        video_codec = params.get('video_codec', 'copy')
        if video_codec == 'none':
            cmd.extend(['-vn'])
        elif video_codec and video_codec != 'copy':
            cmd.extend(['-c:v', video_codec])

            video_bitrate = params.get('video_bitrate')
            if video_bitrate:
                bitrate_mode = params.get('video_bitrate_mode', 'vbr')
                if bitrate_mode == 'cbr':
                    cmd.extend(['-b:v', video_bitrate, '-minrate', video_bitrate, '-maxrate', video_bitrate])
                else:
                    cmd.extend(['-b:v', video_bitrate])

            # 分辨率
            width = params.get('width')
            height = params.get('height')
            if width and height:
                cmd.extend(['-vf', f'scale={width}:{height}'])
            elif height:
                cmd.extend(['-vf', f'scale=-2:{height}'])
            elif width:
                cmd.extend(['-vf', f'scale={width}:-2'])

            # 帧率
            framerate = params.get('framerate')
            if framerate and framerate != 'original':
                try:
                    fps_val = int(framerate)
                    cmd.extend(['-r', str(fps_val)])
                except ValueError:
                    pass
        else:
            cmd.extend(['-c:v', 'copy'])

        # 音频参数
        audio_codec = params.get('audio_codec')
        if audio_codec:
            if audio_codec == 'none':
                cmd.extend(['-an'])
            else:
                cmd.extend(['-c:a', audio_codec])

                audio_bitrate = params.get('audio_bitrate')
                if audio_bitrate:
                    cmd.extend(['-b:a', audio_bitrate])

                sample_rate = params.get('sample_rate')
                if sample_rate:
                    cmd.extend(['-ar', str(sample_rate)])

                channels = params.get('channels')
                if channels:
                    cmd.extend(['-ac', str(channels)])
        else:
            cmd.extend(['-c:a', 'copy'])

        # 附加参数
        additional_args = params.get('additional_args', [])
        if additional_args:
            cmd.extend(additional_args)

        # 输出文件
        cmd.append(output_file)

        return cmd

    def get_supported_formats(self) -> list:
        """获取支持的输出格式列表"""
        return [
            {'name': 'MP4 (H.264)', 'ext': '.mp4', 'type': 'video',
             'video_codec': 'libx264', 'audio_codec': 'aac'},
            {'name': 'MP4 (H.265/HEVC)', 'ext': '.mp4', 'type': 'video',
             'video_codec': 'libx265', 'audio_codec': 'aac'},
            {'name': 'MKV (H.264)', 'ext': '.mkv', 'type': 'video',
             'video_codec': 'libx264', 'audio_codec': 'aac'},
            {'name': 'AVI', 'ext': '.avi', 'type': 'video',
             'video_codec': 'libx264', 'audio_codec': 'mp3'},
            {'name': 'MOV', 'ext': '.mov', 'type': 'video',
             'video_codec': 'libx264', 'audio_codec': 'aac'},
            {'name': 'WebM (VP9)', 'ext': '.webm', 'type': 'video',
             'video_codec': 'libvpx-vp9', 'audio_codec': 'libopus'},
            {'name': 'WebM (VP8)', 'ext': '.webm', 'type': 'video',
             'video_codec': 'libvpx', 'audio_codec': 'libvorbis'},
            {'name': 'GIF 动画', 'ext': '.gif', 'type': 'video',
             'video_codec': 'gif', 'audio_codec': 'none'},
            {'name': 'MP3 音频', 'ext': '.mp3', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'libmp3lame'},
            {'name': 'FLAC 音频', 'ext': '.flac', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'flac'},
            {'name': 'WAV 音频', 'ext': '.wav', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'pcm_s16le'},
            {'name': 'AAC 音频', 'ext': '.aac', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'aac'},
            {'name': 'OGG (Vorbis)', 'ext': '.ogg', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'libvorbis'},
            {'name': 'OPUS 音频', 'ext': '.opus', 'type': 'audio',
             'video_codec': 'none', 'audio_codec': 'libopus'},
        ]


# 全局实例
ffmpeg_api = FFmpegAPI()
