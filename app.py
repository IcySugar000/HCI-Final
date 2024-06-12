import sys
from enum import Enum
import asyncio

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QLabel
from PyQt5.QtGui import QPainter, QColor, QPixmap, QPalette, QBrush, QMovie
from PyQt5.QtCore import Qt, QTimer

import threading
import time
from functools import partial

from voice2str import Resolver
from chatglm import LLM

class Status(Enum):
    READY = 1
    LISTENING = 2
    PROCESSING = 3

class VoiceAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.initUI()

        self.chat = LLM()
        self.status = Status.READY
        self.history = ""
        
        
    def initUI(self):
        self.setWindowTitle('Voice Assistant')

        self.gif_label = QLabel(self)
        self.set_gif("elem/ready.gif")

        self.updateBackground()
        
        # 创建圆形按钮
        self.recordButton = CircleButton(self)
        self.recordButton.setFixedSize(70, 70)
        self.recordButton.setCheckable(True)
        self.recordButton.pressed.connect(self.start_recording)
        self.recordButton.released.connect(self.end_recording)
        
        # 创建文本显示框
        self.textEdit = QTextEdit(self)
        
        # 布局管理
        layout = QVBoxLayout()
        layout.addWidget(self.gif_label, alignment=Qt.AlignHCenter)
        layout.addWidget(self.textEdit)
        layout.addWidget(self.recordButton, alignment=Qt.AlignHCenter)
        
        container = QWidget()
        container.setLayout(layout)
        
        self.setCentralWidget(container)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateBackground()

    def updateBackground(self):
        oImage = QPixmap("elem/bg.png")
        sImage = oImage.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        palette = self.palette()
        palette.setBrush(QPalette.Window, QBrush(sImage))
        self.setPalette(palette)

    def set_gif(self, gif_path):
        self.movie = QMovie(gif_path)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

    def start_recording(self):
        if self.status != Status.READY:
            return
        print("start")
        self.set_gif("elem/listening.gif")
        self.resolver = Resolver()
        self.resolver.start()
        self.status = Status.LISTENING
        threading.Thread(target=self.listen).start()
    
    def end_recording(self):
        if self.status != Status.LISTENING:
            return
        print("end")
        self.resolver.done = True
        self.status = Status.PROCESSING
        q = self.resolver.get_str()
        if q != "":
            self.set_gif("elem/processing.gif")
            threading.Thread(target=self.processing, args=(q,)).start()
        else:
            self.status=Status.READY

    def listen(self):
        while self.status == Status.LISTENING:
            print("listening")
            time.sleep(0.4)
            text = self.resolver.get_str()
            QTimer.singleShot(0, partial(self.textEdit.setText, self.history + "您:" + text))
        self.history += "您:" +self.resolver.get_str() + '\n'

    def processing(self, q):
        self.recordButton.setDisabled(True)
        response = self.chat.get_reply(q)
        print(response)
        self.history += "VA:" + response + '\n'
        QTimer.singleShot(0, self.finish_processing)

    def finish_processing(self):
        self.status = Status.READY
        self.textEdit.setText(self.history)
        self.recordButton.setDisabled(False)
        self.set_gif('elem/ready.gif')

class CircleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._color = QColor("#FFFF00")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(self.rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._color = QColor("#FF8000")
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._color = QColor("#FFFF00")
            self.update()
        super().mouseReleaseEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VoiceAssistant()
    ex.show()
    sys.exit(app.exec_())