import sys
from PyQt6.QtWidgets import (QWidget, QLineEdit, QListWidget,
        QTextEdit, QVBoxLayout, QApplication,
        QDockWidget, QMainWindow)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
import stockapi


class StockSearchWidget(QLineEdit):
    """
    用于输入股票信息的控件，根据输入的内容会自动更新提示信息
    """

    # 如果输入的信息能确定唯一的股票，或者用户选择了提示列表的某一项，
    # 触发该事件，该事件带一个字符串参数
    complete = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.initializeUI()

        self.complete.connect(lambda x: print(f"{x} emit"))


    def initializeUI(self):
        self.setPlaceholderText("代码/简称/关键字")
        self.textChanged.connect(self.update_symbol_edit)

        self.dock = QDockWidget("", self)
        self.dock.setFloating(True)
        self.dock.setVisible(False)

        # 去除边框
        # title_bar = self.dock.titleBarWidget()
        temp_title_bar = QWidget()
        self.dock.setTitleBarWidget(temp_title_bar)
        del temp_title_bar

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_list_clicked)
        self.dock.setWidget(self.list_widget)

    def update_position(self):
        self_x = self.mapToGlobal(QPoint(0, 0)).x()
        self_y = self.mapToGlobal(QPoint(0, 0)).y()
        self_h = self.geometry().height()
        self_w = self.geometry().width()

        # 计算dock的位置
        x = self_x
        y = self_y + self_h
        w = self_w
        h = 120
        self.dock.move(x, y)
        self.dock.resize(w, h)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dock.setVisible(False)

        elif event.key() == Qt.Key.Key_Up:
            row = self.list_widget.currentRow()
            count = self.list_widget.count()
            row = (row - 1) % count
            self.list_widget.setCurrentRow(row)

        elif event.key() == Qt.Key.Key_Down:
            row = self.list_widget.currentRow()
            count = self.list_widget.count()
            row = (row + 1) % count
            self.list_widget.setCurrentRow(row)

        elif event.key() == Qt.Key.Key_Return:
            text = self.list_widget.currentItem().text()
            self.complete.emit(text)
            self.setText(text)
            self.dock.setVisible(False)

        else:
            print(event.key())
            super().keyPressEvent(event)

    def on_list_clicked(self, item):
        text = item.text()
        self.complete.emit(text)
        self.setText(text)
        self.dock.setVisible(False)


    def update_symbol_edit(self, text):
        """
        根据input_str, 更新combobox的items
        """
        if len(text) == 0:
            self.dock.setVisible(False)
        else:
            recommends = stockapi.get_recommend_stock(text)
            if len(recommends) == 0:
                self.dock.setVisible(False)
            else:
                self.list_widget.clear()
                for stock in recommends:
                    item_text = f"{stock['Code']}  {stock['Category']}  {stock['Name']}"
                    self.list_widget.addItem(item_text)
                    self.list_widget.setCurrentRow(0)
                    self.update_position()
                    self.dock.setVisible(True)


if __name__ == "__main__":
    pass
