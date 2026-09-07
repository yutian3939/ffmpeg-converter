"""FFmpeg 格式转换器 - 程序入口"""

import sys
import os


def main():
    """主函数"""
    # 确保当前目录在 sys.path 中
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFont
    from PyQt5.QtCore import Qt

    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("FFmpeg 格式转换器")
    app.setApplicationVersion("1.0.0")

    # 设置默认字体
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    # 设置应用图标（如果存在）
    icon_path = os.path.join(script_dir, 'resources', 'icons', 'app.png')
    if os.path.isfile(icon_path):
        from PyQt5.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    # 创建并显示主窗口
    from app.mainwindow import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
