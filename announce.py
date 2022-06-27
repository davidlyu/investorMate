"""
announce.py
"""
import os
import sys
import time
import json
import re
from urllib.parse import urljoin
import requests
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel,
        QProgressBar, QLineEdit, QPushButton, QTextEdit, 
        QComboBox, QFileDialog, QGridLayout)
from PyQt6.QtCore import pyqtSignal, QThread, QEvent


style_sheet = """
    QProgressBar{
            background-color: #C0C6CA;
            color: #FFFFFF;
            border: 1px solid grey;
            padding: 3px;
            height: 15px;
            text-align: center;
            }

    QProgressBar::chunk{
            background: #538DB8;
            width: 5px;
            margin: 0.5px;
            }
"""


class DownloadWorker(QThread):
    """Create worker thead for running tasks like updating
    the prograss bar, download stock announcements"""
    update_value_signal = pyqtSignal(int)
    update_str_signal = pyqtSignal(str)

    def __init__(self, announcements, directory):
        super().__init__()
        self.announcements = announcements
        self.directory = directory

    def stopRunning(self):
        """Terminate the thread."""
        self.terminate()
        self.wait()

        self.update_value_signal.emit(0)
        self.update_str_signal.emit("下载完成")

    def run(self):
        """The thread begins running from here.
        run() is only called after start()."""
        count = len(self.announcements)
        for i, ann in enumerate(self.announcements):
            announce_title = ann["announcementTitle"]
            sec_name = re.sub("</{0,1}em>", "", ann["secName"])
            progress_str = f"正在下载 {sec_name} {announce_title}"

            response = requests.get(ann["ann_dl_url"])
            file_name = f"{sec_name}：{announce_title}.pdf"
            file_name = os.path.join(self.directory, file_name)
            with open(file_name, "wb") as file:
                file.write(response.content)
            progress_val = int((i + 1) / count * 100)
            self.update_value_signal.emit(progress_val)
            self.update_str_signal.emit(progress_str)
        self.stopRunning()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initializeUI()

    def initializeUI(self):
        self.setMinimumSize(600, 500)
        self.setWindowTitle("股票公告下载")

        self.directory = ""
        self.combo_value = ""

        self.setUpMainWindow()
        self.show()

    def setUpMainWindow(self):
        code_label = QLabel( """<p>输入股票名称:</p>""")
        self.symbol_edit = QComboBox()
        self.symbol_edit.setPlaceholderText("代码/简称/关键字/高管")
        self.symbol_edit.setEditable(True)
        self.symbol_edit.editTextChanged.connect(self.update_symbol_edit)
        self.symbol_edit.activated.connect(self.update_announcement_tedit)

        self.choose_dir_button = QPushButton("选择位置")
        self.choose_dir_button.clicked.connect(self.chooseDirectory)

        # Text edit is for displaying the file names as they
        # are updated
        self.announcement_tedit = QTextEdit()
        self.announcement_tedit.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.stop_button = QPushButton("下载")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.download_announcements)
        self.progress_label = QLabel()

        # Create layout and arrange widgets
        grid = QGridLayout()
        grid.addWidget(code_label, 0, 0)
        grid.addWidget(self.symbol_edit, 1, 0)
        grid.addWidget(self.choose_dir_button, 1, 1)
        grid.addWidget(self.announcement_tedit, 2, 0, 1, 2)
        grid.addWidget(self.progress_bar, 3, 0, 1, 1)
        grid.addWidget(self.stop_button, 3, 1)
        grid.addWidget(self.progress_label, 4, 0, 1, 2)
        self.setLayout(grid)

    def update_symbol_edit(self, input_str):
        """
        根据input_str, 更新combobox的items
        """
        url = f"http://www.cninfo.com.cn/new/information/topSearch/query?keyWord={input_str}&maxNum=10"
        response = requests.post(url)
        json_obj = json.loads(response.text)

        if len(json_obj) > 1:
            self.symbol_edit.clear()
            self.announcement_tedit.setText("")
            for obj in json_obj:
                stock_code = obj["code"]
                stock_name = obj["zwjc"]
                category = obj["category"]
                item = f"{stock_code}\t{category}\t{stock_name}"
                self.symbol_edit.addItem(item)
        elif len(json_obj) == 1:
            self.symbol_edit.clear()
            stock_name = json_obj[0]["zwjc"]
            stock_code = json_obj[0]["code"]
            category = json_obj[0]["category"]
            item = f"{stock_code}\t{category}\t{stock_name}"
            self.symbol_edit.addItem(item)
            self.update_announcement(stock_name)

    def update_announcement_tedit(self):
        text = self.symbol_edit.currentText()
        stock_name = text.split("\t")[2]
        self.symbol_edit.clear()
        self.update_announcement(stock_name)

    def update_announcement(self, input_str):
        """
        获取org_id, code
        """
        url = f"http://www.cninfo.com.cn/new/information/topSearch/query?keyWord={input_str}&maxNum=10"
        response = requests.post(url)
        json_obj = json.loads(response.text)

        if len(json_obj) > 0:
            org_id = json_obj[0]["orgId"]
            stock_code = json_obj[0]["code"]
            stock_name = json_obj[0]["zwjc"]
        else:
            return None

        # 构造请求
        # 判断输入的股票名称是否完整
        response_obj = None
        if input_str == stock_name:
            stock = stock_code + "," + org_id
            tab_name = "fulltext"
            category = "category_ndbg_szsh;category_sf_szsh;"
            search_key = stock_name
            is_hl_title = "true"
            post_data = {"stock": stock,
                    "tabName": tab_name,
                    "pageSize": "30",
                    "pageNum": "1",
                    "column": "szse" if stock_code[0] in "03" else "sse",
                    "category": category,
                    "plate": "sz" if stock_code[0] in "03" else "sh",
                    "seDate": "",
                    "searchKey": search_key,
                    "secid": "",
                    "sortName": "",
                    "sortType": "",
                    "isHLtitle": is_hl_title}
            url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
            response = requests.post(url, data=post_data)
            response_obj = json.loads(response.text)
            announcements = ""
            for ann in response_obj["announcements"]:
                announcements = announcements + ann["announcementTitle"] + "\n"
                ann["ann_dl_url"] = urljoin("http://static.cninfo.com.cn", ann["adjunctUrl"])
            self.announcement_tedit.setText(announcements)
            self.stop_button.setEnabled(True)
        self.response_obj = response_obj

    def download_announcements(self):
        """下载公告pdf文件"""
        worker = DownloadWorker(self.response_obj["announcements"], self.directory)
        worker.update_value_signal.connect(self.updateProgressBar)
        worker.update_str_signal.connect(self.update_progress_label)
        worker.run()
        self.stop_button.setEnabled(False)

    def chooseDirectory(self):
        """Choose file directory."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(
            QFileDialog.FileMode.Directory)
        self.directory = file_dialog.getExistingDirectory(
            self, "Open Directory", "",
            QFileDialog.Option.ShowDirsOnly)

    def updateComboValue(self, text):
        """Change the combo box value. Values represent
        the different file extensions."""
        self.combo_value = text
        print(self.combo_value)

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def update_progress_label(self, progress_str):
        self.progress_label.setText(progress_str)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(style_sheet)
    window = MainWindow()
    sys.exit(app.exec())
