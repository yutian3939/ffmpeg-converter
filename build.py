"""
FFmpeg 格式转换器 - 打包脚本
用法: python build.py
"""

import os
import sys
import shutil
import subprocess
import platform


def main():
    # 确保在项目根目录
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    # 确保 ffmpeg 二进制存在
    ffmpeg_dir = os.path.join(root, 'resources', 'ffmpeg')
    if not os.path.isfile(os.path.join(ffmpeg_dir, 'ffmpeg.exe')):
        print('错误: resources/ffmpeg/ffmpeg.exe 不存在！')
        print('请先下载 ffmpeg 并放入 resources/ffmpeg/ 目录')
        sys.exit(1)

    # 确保 PyInstaller 已安装
    try:
        import PyInstaller
    except ImportError:
        print('正在安装 PyInstaller...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # 设置图标（如果有）
    icon_path = os.path.join(root, 'resources', 'icons', 'app.ico')
    icon_arg = ['--icon', icon_path] if os.path.isfile(icon_path) else []

    # 输出目录名
    dist_name = 'FFmpegConverter'

    # 清理旧的打包输出
    for d in ['build']:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    old_exe = os.path.join(root, 'dist', f'{dist_name}.exe')
    if os.path.isfile(old_exe):
        os.remove(old_exe)
        p = os.path.join(root, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)

    print('开始打包...')
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--windowed',                          # 无控制台窗口
        '--onefile',                           # 单文件
        '--name', dist_name,
        '--add-data', f'resources/styles.qss{os.pathsep}resources/',
        '--add-data', f'resources/ffmpeg/ffmpeg.exe{os.pathsep}resources/ffmpeg/',
        '--add-data', f'resources/ffmpeg/ffprobe.exe{os.pathsep}resources/ffmpeg/',
        '--add-data', f'settings.json{os.pathsep}.',
        '--hidden-import', 'PyQt5.sip',
        *icon_arg,
        '--clean',
        'main.py',
    ]

    # Windows 路径分隔符
    if platform.system() == 'Windows':
        cmd = [c.replace('/', '\\') for c in cmd]

    print(' '.join(cmd))
    subprocess.check_call(cmd)

    # 打包后信息
    exe_path = os.path.join(root, 'dist', f'{dist_name}.exe')
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f'\n打包成功！')
        print(f'输出文件: {exe_path}')
        print(f'文件大小: {size_mb:.1f} MB')
        print(f'\n单个 exe 文件，拷贝到其他电脑即可运行，无需安装 Python 或 ffmpeg。')
    else:
        print(f'\n打包完成，但未找到输出文件 "{exe_path}"')
        print('请检查 build 目录中的日志信息。')

    input('\n按 Enter 键退出...')


if __name__ == '__main__':
    main()
