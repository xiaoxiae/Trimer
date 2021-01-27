import sys
from abc import ABC, abstractmethod
from math import sin, pi, acos, degrees
from random import random, uniform

from PyQt5.QtCore import QTimer, QTime, Qt, QDate, QDir, QUrl, QPointF, QSize, QRect
from PyQt5.QtGui import QFont, QPainter, QBrush, QPen, QColor
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox
from PyQt5.QtWidgets import QVBoxLayout, QLabel


def smoothen_curve(x: float):
    """f(x) with a smoother beginning and end."""
    # TODO: move to utilities?
    return (sin((x - 1 / 2) * pi) + 1) / 2


class Drawable(ABC):
    """Something that has a draw function that takes a painter to be painted. Also contains some convenience methods
    for drawing the thing and saving it to an SVG."""

    @abstractmethod
    def draw(self, painter: QPainter, width: int, height: int):
        """Draw the drawable onto a painter, given its size."""
        pass

    def save(self, path: str, width: int, height: int):
        """Save the drawable to the specified file, given its size."""
        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRect(0, 0, width, height))

        painter = QPainter(generator)
        self.draw(painter, width, height)
        painter.end()


class Plant(ABC):
    @abstractmethod
    def generate(self):
        """Generate the parameters necessary for displaying the plant grow."""
        pass


class Tree(Drawable, Plant):
    """A simple tree class that all trees originate from."""
    age = 0
    maxAge = None

    def generate(self):
        # so we don't go from 0 to 1, but from 0.5 to 1
        self.age_coefficient = (self.maxAge + 1) / 2

        # to somewhat randomize the width and the height of the tree stuff
        self.width_coefficient = uniform(0.9, 1.1)
        self.height_coefficient = uniform(0.9, 1.1)

        # how many branches should it have? always at least one, larger ones have two
        branch_count = round(uniform(1, 2 * self.age_coefficient))

        # positions of branches up the tree, + their orientations (where they're turned towards)
        self.branches = [(uniform(self.width_coefficient * 0.45, self.width_coefficient * 0.55),
                          (((i - 1 / 2) * 2) if branch_count == 2 else (-1 if random() < 0.5 else 1)) * acos(
                              uniform(0.4, 0.6))) for i in
                         range(branch_count)]

        self.base_width = lambda width: width / 15 * self.width_coefficient * self.age_coefficient
        self.base_height = lambda height: height / 1.7 * self.height_coefficient * self.age_coefficient

        self.branch_width = lambda width: width / 18 * self.width_coefficient * self.age_coefficient
        self.branch_height = lambda height: height / 2.7 * self.height_coefficient * self.age_coefficient

    def set_current_age(self, age: float):
        """Set the current age of the tree (normalized from 0 to 1). Changes the way it is drawn."""
        self.age = age

    def change_max_age(self, maxAge: float):
        """Change the tree's max age, re-generating it in the process."""
        self.maxAge = maxAge
        self.generate()

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setBrush(QBrush(QColor(77, 51, 0)))

        # main branch
        painter.drawPolygon(QPointF(-self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(0, self.base_height(height) * smoothen_curve(self.age)))

        # other branches
        for h, rotation in self.branches:
            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            # grow branches slower than the other parts
            adjusted_age = self.age ** 2

            painter.drawPolygon(QPointF(-self.branch_width(width) * smoothen_curve(adjusted_age) * (1 - h), 0),
                                QPointF(self.branch_width(width) * smoothen_curve(adjusted_age) * (1 - h), 0),
                                QPointF(0, self.branch_height(height) * smoothen_curve(adjusted_age) * (1 - h)))

            painter.restore()

    def draw(self, painter: QPainter, width: int, height: int):
        if self.maxAge is None:
            return

        painter.translate(width / 2, height)
        painter.scale(1, -1)

        self._draw(painter, width, height)


class GreenTree(Tree):

    def generate(self):
        super().generate()

        self.green_width = lambda width: width / 3 * self.width_coefficient * self.age_coefficient
        self.green_height = lambda height: height / 1.2 * self.height_coefficient * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(0, 119, 0)))
        offset = self.base_height(height * 0.3 * smoothen_curve(self.age))
        painter.drawPolygon(QPointF(-self.green_width(width) * smoothen_curve(self.age), offset),
                            QPointF(self.green_width(width) * smoothen_curve(self.age), offset),
                            QPointF(0, min(self.green_height(height) * smoothen_curve(self.age) + offset,
                                           height * 0.95)))

        super()._draw(painter, width, height)


class Canvas(QWidget):
    """A widget that takes a drawable object and constantly draws it."""

    def __init__(self, obj: Drawable, parent=None, ):
        super(Canvas, self).__init__(parent)
        self.object = obj
        self.setFixedSize(300, 300)
        self.setContentsMargins(20, 20, 20, 20)

    def save(self, path: str):
        """Save the drawable object to the specified file."""
        self.object.save(path, self.width(), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setClipRect(0, 0, self.width(), self.height())

        self.object.draw(painter, self.width(), self.height())

        painter.end()


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.DEFAULT_STUDY_TIME = 45
        self.DEFAULT_BREAK_TIME = 15

        self.MAX_PLANT_AGE = 90  # maximum number of minutes to make the plant optimal in size

        self.MAX_TIME = 180
        self.STEP = 5

        self.INITIAL_TEXT = "Start!"

        self.STUDY_TEXT = "Study"
        self.BREAK_TEXT = "Break"

        self.PAUSE_TEXT = "Pause"
        self.CONTINUE_TEXT = "Continue"

        v_layout = QVBoxLayout()
        font = QFont('Arial', 120, QFont.Bold)

        self.timeLabel = QLabel(self)
        self.timeLabel.setAlignment(Qt.AlignCenter)
        self.timeLabel.setFont(font)
        self.timeLabel.setText(self.INITIAL_TEXT)

        self.plant = GreenTree()

        self.canvas = Canvas(self.plant)
        self.canvas.hide()

        h_layout = QHBoxLayout()

        h_layout.addWidget(self.timeLabel)
        h_layout.addWidget(self.canvas)

        v_layout.addLayout(h_layout)

        h_layout = QHBoxLayout()

        self.study_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_STUDY_TIME,
                                           singleStep=self.STEP)
        self.break_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_BREAK_TIME,
                                           singleStep=self.STEP)

        self.study_button = QPushButton(self, text=self.STUDY_TEXT, clicked=self.start)
        self.break_button = QPushButton(self, text=self.BREAK_TEXT, clicked=self.start_break)

        self.pause_button = QPushButton(self, text=self.PAUSE_TEXT, clicked=self.toggle_pause)
        self.pause_button.setDisabled(True)

        h_layout.addWidget(self.study_time_spinbox)
        h_layout.addWidget(self.break_time_spinbox)
        h_layout.addWidget(self.study_button)
        h_layout.addWidget(self.break_button)
        h_layout.addWidget(self.pause_button)

        v_layout.addLayout(h_layout)

        self.setLayout(v_layout)

        self.study_timer = QTimer(self)
        self.study_timer.timeout.connect(self.decrease_remaining_time)
        self.study_timer_frequency = 1 / 60 * 1000
        self.study_timer.setInterval(int(self.study_timer_frequency))

        self.player = QMediaPlayer()

    def start_break(self):
        self.start(do_break=True)

    def start(self, do_break=False):
        """The function called after pressing the start button. Starts the timer, plant growth,..."""
        self.study_button.setDisabled(not do_break)
        self.break_button.setDisabled(True)

        self.pause_button.setDisabled(False)
        self.pause_button.setText(self.PAUSE_TEXT)

        # set, whether we finished studying and are having a break
        # this is initially false, since we just started the session
        self.study_done = do_break

        # the total time to study for (spinboxes are minutes)
        self.leftover_time = (self.study_time_spinbox if not do_break else self.break_time_spinbox).value() * 60
        self.total_time = self.leftover_time


        # don't start showing canvas and growing the plant when we're not studying
        if not do_break:
            self.canvas.show()

            self.plant.change_max_age(min(1, (self.total_time / 60) / self.MAX_PLANT_AGE))

        self.study_timer.stop()  # it could be running - we could be currently in a break
        self.study_timer.start()

    def toggle_pause(self):
        # stop the timer, if it's running
        if self.study_timer.isActive():
            self.study_timer.stop()
            self.pause_button.setText(self.CONTINUE_TEXT)

        # if not, resume
        else:
            self.study_timer.start()
            self.pause_button.setText(self.PAUSE_TEXT)

    def update_time_label(self, time):
        """Update the text of the time label, given some time in seconds."""
        hours = int(time // 3600)
        minutes = int((time // 60) % 60)
        seconds = int(time % 60)

        # smooth timer: hide minutes/hours if there are none
        if hours == 0:
            if minutes == 0:
                self.timeLabel.setText(str(seconds))
            else:
                self.timeLabel.setText(str(minutes) + QTime(0, 0, seconds).toString(":ss"))
        else:
            self.timeLabel.setText(str(hours) + QTime(0, minutes, seconds).toString(":mm:ss"))

    def play_sound(self, name: str):
        """Play a file, relative to the current directory."""
        path = QDir.current().absoluteFilePath(name)
        url = QUrl.fromLocalFile(path)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()

    def decrease_remaining_time(self):
        """Decrease the remaining time by the timer frequency. Updates clock/plant growth."""
        self.update_time_label(self.leftover_time)
        self.leftover_time -= self.study_timer_frequency / 1000

        if self.leftover_time <= 0:
            if self.study_done:
                self.study_timer.stop()

                self.break_button.setDisabled(False)
                self.pause_button.setDisabled(True)

                self.play_sound("break.m4a")

                self.timeLabel.setText(self.INITIAL_TEXT)
                self.canvas.hide()
            else:
                self.leftover_time = self.break_time_spinbox.value() * 60
                self.study_done = True

                self.study_button.setDisabled(False)

                with open("trimer.log", "a") as f:
                    name = QDate.currentDate().toString(Qt.ISODate) + "|" + QTime.currentTime().toString(
                        "hh:mm:ss")

                    f.write(name + " - finished studying for " + str(self.total_time // 60) + " minutes." + "\n")

                    self.canvas.save(name + ".svg")

                self.play_sound("study.m4a")
        else:
            # if there is leftover time and we haven't finished studying, grow the plant
            if not self.study_done:
                self.plant.set_current_age(1 - (self.leftover_time / self.total_time))
                self.canvas.update()


app = QApplication(sys.argv)
window = Window()
window.show()
app.exit(app.exec_())
