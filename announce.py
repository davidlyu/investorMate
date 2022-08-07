"""
announce.py
"""
from ctypes import resize
import os
import sys
import time
import json
import re
from urllib.parse import urljoin
from venv import create
import webbrowser
# from jmespath import search
import requests
from PyQt6.QtWidgets import (QApplication, QStackedWidget, QTableWidget, QTextBrowser, QVBoxLayout, QWidget, QLabel,
        QProgressBar, QLineEdit, QPushButton, QTextEdit, QStackedLayout, QRadioButton, QTableWidgetItem,
        QComboBox, QFileDialog, QGridLayout, QListWidget, QListWidgetItem, QHBoxLayout, QAbstractItemView,
        QMenu)
from PyQt6.QtCore import pyqtSignal, QThread, QPoint, Qt
from PyQt6.QtGui import QFont, QAction, QColor, QPixmap
import stockapi
import createdb
from test import StockSearchWidget


# 参数
STOCK_UPDATE_INTERVAL = 10

# 导入 QSS 函数
def load_style_from_qss(f):
    """
    从 qss 文件导入样式
    参数：
        f - qss 文件名
    返回：
        样式字符串
    """
    file_obj = open(f)
    lines = file_obj.readlines()
    file_obj.close()
    res = ''
    for line in lines:
        res += line
    return res


announcement_db = createdb.AnnouncementDatabase()


class DownloadWorker(QThread):
    """
    Create worker thead for running tasks like updating
    the prograss bar, download stock announcements
    """
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


class UpdateStockWorker(QThread):
    """
    Create worker thread for updating stock data
    """
    stock_data_ready_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.update_database()

        self.start_update = False

    def stopRunning(self):
        self.stop_update = False
        self.terminate()
        self.wait()

    def update_database(self):
        self.codes = announcement_db.query_stocks()

    def run(self):
        interval = STOCK_UPDATE_INTERVAL
        self.start_update = True

        while self.start_update:
            stocks_data = []
            for code in self.codes:
                data = stockapi.get_market_data(code)
                if data != {}:
                    stocks_data.append(data)
            self.stock_data_ready_signal.emit(stocks_data)
            time.sleep(interval)


class DownloadReportWidget(QWidget):
    """下载指定股票定期报告界面"""
    def __init__(self):
        super().__init__()
        self.initializeUI()

    def initializeUI(self):
        """initialize ui"""
        self.setUpMainWindow()

    def setUpMainWindow(self):
        """set up mainwindow"""

        self.announcement_tedit = QTextBrowser()
        self.announcement_tedit.setOpenLinks(True)
        self.announcement_tedit.setOpenExternalLinks(True)
        self.announcement_tedit.setReadOnly(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.progress_label = QLabel()

        self.stop_button = QPushButton("下载")
        self.stop_button.setEnabled(False)

        grid = QGridLayout()
        grid.addWidget(self.announcement_tedit, 0, 0, 1, 2)
        grid.addWidget(self.progress_bar, 1, 0)
        grid.addWidget(self.stop_button, 1, 1)
        grid.addWidget(self.progress_label, 2, 0)
        self.setLayout(grid)

    def update_announcement_tedit(self, stock_str):
        """
        update announcements tedit
        """
        code = stock_str.split(" ")[0]
        # self.symbol_edit.clear()

        announcements = stockapi.get_latest_announcement(code)
        html = ""
        for ann in announcements:
            url = ann["AnnouncementUrl"]
            title = ann["AnnouncementTitle"]
            name = ann["Name"]
            html = html + f'<a href="{url}">{name}: {title}</a><p>'
        self.announcement_tedit.insertHtml(html)
        self.stop_button.setEnabled(True)


class SelectedStocksWidget(QWidget):
    """自选股页面"""
    def __init__(self):
        super().__init__()
        self.selected_stocks = announcement_db.query_stocks()
        self.update_stock_worker = UpdateStockWorker()
        self.update_stock_worker.start()
        self.update_stock_worker.stock_data_ready_signal.connect(self.display_stocks_data)
        self.initializeUI()

    def initializeUI(self):
        """initialize ui"""
        self.setUpMainWindow()
        # self.display_stock_data()

    def setUpMainWindow(self):
        """set up main window"""
        self.stocks_table = QTableWidget()
        self.stocks_table.setColumnCount(8)
        self.stocks_table.setRowCount(len(self.selected_stocks))
        self.stocks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stocks_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.stocks_table.verticalHeader().setVisible(False)
        header_labels = ["名称", "代码", "最新", "涨幅", "涨跌", "市盈TTM", "市净", "总市值"]
        self.stocks_table.setHorizontalHeaderLabels(header_labels)

        # Create layout and arrange widgets
        box = QVBoxLayout()
        box.addWidget(self.stocks_table)
        self.setLayout(box)

    def add_stock(self, stock_info):
        # print(stock_info)
        # print(stock_info.split())
        split = stock_info.split()
        code = split[0]
        category = split[1]
        name = split[2]
        # code, category, name = stock_info.split(" ")
        announcement_db.insert_stock(code, name, category)
        self.update_stock_worker.update_database()
        # self.display_stocks_data()

    def contextMenuEvent(self, event):
        delete_action = QAction("删除", self)

        context_menu = QMenu(self)
        context_menu.addAction(delete_action)

        action = context_menu.exec(self.mapToGlobal(event.pos()))

        if action == delete_action:
            # 因为每一行所有的 item 拥有相同的 row，所以 rows 中的列表有重复项，因此需要去重
            rows = [item.row() for item in self.stocks_table.selectedItems()]
            rows = list(set(rows))
            print(rows)

            for row in rows:
                code = self.stocks_table.item(row, 1).text()
                print(code)
                announcement_db.delete_stock(code)
            self.update_stock_worker.update_database()

        # self.display_stocks_data()

    def display_stocks_data(self, stocks_data):
        self.stocks_table.setRowCount(0)
        self.stocks_table.clearContents()

        self.stocks_table.setRowCount(len(stocks_data))

        for i, data in enumerate(stocks_data):
            change_rate = float(data["ChangeRate"])
            if change_rate > 0:
                color = QColor("#ff4343")
            else:
                color = QColor("#07a168")

            item = QTableWidgetItem(data["Name"])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 0, item)

            item = QTableWidgetItem(data["Code"])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 1, item)

            latest_price = float(data["LatestPrice"])
            item = QTableWidgetItem(f"{latest_price:.2f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 2, item)

            item = QTableWidgetItem(f"{change_rate:.2f}%")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 3, item)

            change_amount = float(data["ChangeAmount"])
            item = QTableWidgetItem(f"{change_amount:.2f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 4, item)

            pe_ttm = float(data["PETTM"])
            item = QTableWidgetItem(f"{pe_ttm:.1f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 5, item)

            pb = float(data["PB"])
            item = QTableWidgetItem(f"{pb:.1f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 6, item)

            market_value = float(data["MarketValue"])
            item = QTableWidgetItem(f"{market_value:.0f}亿")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(color)
            self.stocks_table.setItem(i, 7, item)


class LatestAnnouncementWidget(QWidget):
    """获取多只股票的最新公告的界面"""
    def __init__(self):
        super().__init__()
        self.selected_stocks = announcement_db.query_stocks()
        self.initializeUI()

    def initializeUI(self):
        """initialize ui"""
        self.setUpMainWindow()
        self.create_actions()

    def setUpMainWindow(self):
        """set up main window"""
        self.announcements_table = QTableWidget()
        self.announcements_table.setColumnCount(3)
        self.announcements_table.setColumnWidth(0, 20)
        self.announcements_table.setColumnWidth(1, 800)
        self.announcements_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.announcements_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.announcements_table.setHorizontalHeaderLabels(["序号", "公告标题", "公告时间"])
        self.announcements_table.verticalHeader().setVisible(False)
        self.announcements_table.itemClicked.connect(self.read)
        self.announcements_table.itemDoubleClicked.connect(self.open)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_announcements)

        self.display_announcements()

        # Create layout and arrange widgets
        box = QVBoxLayout()
        box.addWidget(self.announcements_table)
        box.addWidget(self.refresh_btn)
        self.setLayout(box)

    def clear_announcements(self):
        """删除所有公告"""
        self.all_announcements = []
        self.announcements_table.setRowCount(0)
        self.announcements_table.clearContents()

    def display_announcements(self):
        """把公告从数据库里读取出来，并显示"""
        self.clear_announcements()
        self.all_announcements = announcement_db.query_announcements()
        self.announcements_table.setRowCount(len(self.all_announcements))

        font = self.announcements_table.font()
        font.setBold(True)
        for i, ann in enumerate(self.all_announcements):
            ann_title = f'{ann["Name"]}: {ann["AnnouncementTitle"]}'
            ann_date = ann["AnnouncementDate"]
            if ann["AnnouncementState"] != "DELETED":
                num_item = QTableWidgetItem(f"{i+1}")
                num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.announcements_table.setItem(i, 0, num_item)
                self.announcements_table.setItem(i, 1, QTableWidgetItem(ann_title))
                self.announcements_table.setItem(i, 2, QTableWidgetItem(ann_date))
                if ann["AnnouncementState"] == "UNREAD":
                    font.setBold(True)
                    self.announcements_table.item(i, 0).setFont(font)
                elif ann["AnnouncementState"] == "READ":
                    font.setBold(False)
                    self.announcements_table.item(i, 0).setFont(font)

    def refresh_announcements(self):
        """从网站抓取数据，并更新数据库"""
        self.all_announcements = []
        for code in self.selected_stocks:
            announcements = stockapi.get_latest_announcement2(code, size=1)
            self.all_announcements = self.all_announcements + announcements

        for ann in self.all_announcements:
            ann_id = ann["AnnouncementId"]
            code = ann["Code"]
            name = ann["Name"]
            title = ann["AnnouncementTitle"]
            ann_date = ann["AnnouncementDate"]
            url = ann["AnnouncementUrl"]
            state = "UNREAD"
            announcement_db.insert_announcement(int(ann_id), code, name, title, ann_date, url, state, reverse=False)

        self.display_announcements()

    def create_actions(self):
        """add actions in the context menu"""
        self.read_act = QAction("标为已读", self)
        self.unread_act = QAction("标为未读", self)
        self.open_act = QAction("打开", self)
        self.delete_act = QAction("删除", self)

        self.read_act.triggered.connect(self.read)
        self.unread_act.triggered.connect(self.unread)
        self.open_act.triggered.connect(self.open)
        self.delete_act.triggered.connect(self.delete)

    def read(self):
        # 首先获取被选中的行号列表，并去重
        rows = [item.row() for item in self.announcements_table.selectedItems()]
        rows = list(set(rows))

        for row in rows:
            ann_id = self.all_announcements[row]["AnnouncementId"]
            state = "READ"
            announcement_db.update_announcement_state(int(ann_id), state)
            font = self.announcements_table.font()
            font.setBold(False)
            self.announcements_table.item(row, 0).setFont(font)

    def unread(self):
        # 首先获取被选中的行号列表，并去重
        rows = [item.row() for item in self.announcements_table.selectedItems()]
        rows = list(set(rows))

        for row in rows:
            ann_id = self.all_announcements[row]["AnnouncementId"]
            state = "UNREAD"
            announcement_db.update_announcement_state(int(ann_id), state)
            font = self.announcements_table.font()
            font.setBold(True)
            self.announcements_table.item(row, 0).setFont(font)

    def delete(self):
        rows = [item.row() for item in self.announcements_table.selectedItems()]
        rows = list(set(rows))
        rows.sort(reverse=True)

        for row in rows:
            print(self.all_announcements[row]["AnnouncementTitle"])
            self.announcements_table.removeRow(row)
            ann_id = self.all_announcements[row]["AnnouncementId"]
            state = "DELETED"
            del self.all_announcements[row]
            announcement_db.update_announcement_state(int(ann_id), state)

    def open(self):
        self.read()
        row = self.announcements_table.currentRow()
        url = self.all_announcements[row]["AnnouncementUrl"]
        print(f"open {url}")
        webbrowser.open(url)

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        context_menu.addAction(self.read_act)
        context_menu.addAction(self.unread_act)
        context_menu.addAction(self.open_act)
        context_menu.addAction(self.delete_act)

        action = context_menu.exec(self.mapToGlobal(event.pos()))


class FinancialStatementWidget(QWidget):
    """获取指定股票财务报表的界面"""
    def __init__(self):
        super().__init__()
        self.category = "zcfzb"
        self.code = ""
        self.initializeUI()

    def initializeUI(self):
        """initialize ui"""
        self.setUpMainWindow()

    def setUpMainWindow(self):
        """set up main window"""
        # code_label = QLabel( """<p>输入股票名称:</p>""")

        # 选择报表类型
        self.balance_rb = QRadioButton("资产负债表")
        self.balance_rb.setChecked(True)
        self.balance_rb.toggled.connect(self.update_category)
        self.income_rb = QRadioButton("利润表")
        self.income_rb.toggled.connect(self.update_category)
        self.cash_rb = QRadioButton("现金流量表")
        self.cash_rb.toggled.connect(self.update_category)
        category_h_box = QHBoxLayout()
        category_h_box.addWidget(self.balance_rb)
        category_h_box.addWidget(self.income_rb)
        category_h_box.addWidget(self.cash_rb)
        category_h_box.addStretch()

        # search_edit = StockSearchWidget()
        # search_edit.complete.connect(self.update_code)
        # 显示财务报表的table
        self.financial_table = QTableWidget()

        box = QVBoxLayout()
        # box.addWidget(code_label)
        # box.addWidget(search_edit)
        box.addLayout(category_h_box)
        box.addWidget(self.financial_table)
        self.setLayout(box)

    def update_category(self):
        """更新报表类型，然后更新报表"""
        if self.balance_rb.isChecked():
            current_category = "zcfzb"
        elif self.income_rb.isChecked():
            current_category = "lrb"
        else:
            current_category = "xjllb"

        if self.category != current_category and self.code != "":
            self.category = current_category
            self.update_financial_statement()

    def update_code(self, stock_str):
        """更新股票代码，然后更新报表"""
        code = stock_str.split(" ")[0]
        if self.code != code:
            self.code = code
            self.update_financial_statement()

    def update_financial_statement(self):
        """获取给定股票的财务报表，并显示"""
        statement = stockapi.get_financial_statement(self.code, self.category)
        horizontal_headers = statement[0][1:]
        vertical_headers = [item[0] for item in statement][1:]
        row = len(vertical_headers)
        column = len(horizontal_headers)
        self.financial_table.setRowCount(row)
        self.financial_table.setColumnCount(column)
        self.financial_table.setVerticalHeaderLabels(vertical_headers)
        self.financial_table.setHorizontalHeaderLabels(horizontal_headers)
        for i, line in enumerate(statement[1:]):
            for j, item in enumerate(line[1:]):
                item_obj = QTableWidgetItem(item)
                self.financial_table.setItem(i, j, item_obj)


class MainWindow(QWidget):
    "股票投资助手程序的主界面"
    def __init__(self):
        super().__init__()

        self.initializeUI()

    def initializeUI(self):
        self.setMinimumSize(1200, 800)
        self.setWindowTitle("股票公告下载")

        # 删除系统自带标题栏
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("MainWindow")

        self.directory = ""
        self.combo_value = ""

        self.setUpMainWindow()
        self.show()

    def setUpMainWindow(self):
        """
        setup main window
        """
        # ============ 标题栏 ===================
        title_bar_box = QHBoxLayout()
        title_bar_box.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(" 股票投资助手")
        title_label.setObjectName("TitleLabel")

        minimize_btn = QPushButton("")
        minimize_btn.setObjectName("MinimizeButton")

        maximize_btn = QPushButton("")
        maximize_btn.setObjectName("MaximizeButton")

        close_btn = QPushButton("")
        close_btn.setObjectName("CloseButton")

        self.stock_search_widget = StockSearchWidget()
        self.stock_search_widget.setFixedWidth(250)
        self.stock_search_widget.complete.connect(self.stock_search_complete)
        title_bar_box.addWidget(title_label)
        title_bar_box.addWidget(self.stock_search_widget)
        title_bar_box.addStretch()
        title_bar_box.addWidget(minimize_btn)
        title_bar_box.addWidget(maximize_btn)
        title_bar_box.addWidget(close_btn)

        title_bar_widget = QWidget()
        title_bar_widget.setObjectName("TitleBar")
        title_bar_widget.setLayout(title_bar_box)

        minimize_btn.clicked.connect(self.minimize_window)
        maximize_btn.clicked.connect(self.maximize_window)
        close_btn.clicked.connect(self.close)

        # ============== 左侧导航栏 =====================
        self.sel = QListWidget()
        self.sel.setMaximumWidth(150)
        self.sel.setObjectName("sel")
        func_list = ["自选股","定期报告", "公告资讯", "财务数据"]
        for item in func_list:
            list_item = QListWidgetItem()
            list_item.setText(item)
            self.sel.addItem(list_item)
        self.sel.currentRowChanged.connect(self.switch_page)

        # =============== 右侧界面 ======================
        self.pages = {
            "SelectedStocks": SelectedStocksWidget(),
            "DownloadReport": DownloadReportWidget(),
            "LatestAnnouncement": LatestAnnouncementWidget(),
            "FinancialStatement": FinancialStatementWidget(),
        }
        self.stack = QStackedLayout()
        for _, widget in self.pages.items():
            self.stack.addWidget(widget)

        # ================== 主界面 =======================
        main_h_box = QHBoxLayout()
        main_h_box.addWidget(self.sel)
        main_h_box.addLayout(self.stack)

        # create the main layout
        main_v_box = QVBoxLayout()
        main_v_box.setContentsMargins(0, 0, 0, 0)
        main_v_box.addWidget(title_bar_widget)
        main_v_box.addLayout(main_h_box)

        self.setLayout(main_v_box)

    # ============ 槽函数 =================
    def stock_search_complete(self, stock_str):
        if self.stack.currentWidget() == self.pages["SelectedStocks"]:
            self.pages["SelectedStocks"].add_stock(stock_str)
        elif self.stack.currentWidget() == self.pages["DownloadReport"]:
            self.pages["DownloadReport"].update_announcement_tedit(stock_str)
        elif self.stack.currentWidget() == self.pages["FinancialStatement"]:
            self.pages["FinancialStatement"].update_code(stock_str)

    def minimize_window(self):
        self.showMinimized()

    def maximize_window(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def switch_page(self, row):
        """slot for switching between tabs"""
        self.stack.setCurrentIndex(row)
        title = self.sel.currentItem().text()
        self.setWindowTitle(f"股票投资助手 - {title}")

    def download_announcements(self):
        """下载公告pdf文件"""
        directory = self.chooseDirectory()
        worker = DownloadWorker(self.response_obj["announcements"], directory)
        worker.update_value_signal.connect(self.updateProgressBar)
        worker.update_str_signal.connect(self.update_progress_label)
        worker.run()
        self.stop_button.setEnabled(False)

    def chooseDirectory(self):
        """Choose file directory."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        return file_dialog.getExistingDirectory(
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

    def closeEvent(self, event):
        sys.exit(app.exec())

    def mousePressEvent(self, a0):
        event_object = self.childAt(a0.pos().x(), a0.pos().y())
        if hasattr(event_object, "objectName"):
            if event_object.objectName() in ["TitleBar", "TitleLabel"]:
                if a0.button() == Qt.MouseButton.LeftButton:
                    self._is_tracking = True
                    self._start_pos = QPoint(a0.pos().x(), a0.pos().y())
    
    def mouseMoveEvent(self, a0):
        if self._start_pos:
            self._end_pos = a0.pos() - self._start_pos
            self.move(self.pos() + self._end_pos)

    def mouseReleaseEvent(self, a0):
        if a0.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = False
            self._start_pos = None
            self._end_pos = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    style_sheet = load_style_from_qss("style.qss")
    app.setStyleSheet(style_sheet)
    window = MainWindow()
    sys.exit(app.exec())
