"""
filename: createdb.py
author: lvbj
email: lvbj07@gmail.com
创建数据库
"""

import sys
from PyQt6.QtSql import QSqlDatabase, QSqlQuery


class AnnouncementDatabase:
    """
    create announcements database 
    """
    def __init__(self):
        super().__init__()

        self.create_connection()
        self.create_announcements_table()
        self.create_stock_table()

    def create_connection(self):
        """create connection to the database."""
        database = QSqlDatabase.addDatabase("QSQLITE") 
        database.setDatabaseName("files/announcements.db")
        if not database.open():
            print("Unable to open data source file.")
            sys.exit(1)
        self.query = QSqlQuery()

    def create_announcements_table(self):
        """
        create table announcements if it is not exists.
        """
        self.query.exec("""CREATE TABLE IF NOT EXISTS announcements (
            ann_id INTEGER PRIMARY KEY UNIQUE NOT NULL,
            code VARCHAR(6) NOT NULL,
            name NVARCHAR(10) NOT NULL,
            title NTEXT NOT NULL,
            ann_date DATE NOT NULL,
            url NTEXT,
            state VARCHAR(10) NOT NULL);""")

    def create_stock_table(self):
        """
        create user selected stock table if it is not exists.
        """
        self.query.exec("""
            CREATE TABLE IF NOT EXISTS stocks (
                code VARCHAR(6) PRIMARY KEY UNIQUE NOT NULL,
                name NVARCHAR(10) NOT NULL,
                category NVARCHAR(5));
        """)

    def insert_announcement(self, ann_id, code, name, title, ann_date, url, state, reverse=True):
        """
        insert an announcement record to table
        """
        self.query.prepare("""INSERT OR IGNORE INTO announcements (
            ann_id, code, name, title, ann_date, url, state)
            VALUES (?, ?, ?, ?, ?, ?, ?);""")

        self.query.addBindValue(ann_id)
        self.query.addBindValue(code)
        self.query.addBindValue(name)
        self.query.addBindValue(title)
        self.query.addBindValue(ann_date)
        self.query.addBindValue(url)
        self.query.addBindValue(state)
        self.query.exec()

    def insert_stock(self, code, name, category):
        """insert a stock record to table"""

        sql = """
            INSERT OR IGNORE INTO stocks (
                code, name, category)
                VALUES (?, ?, ?);
        """
        self.query.prepare(sql)
        self.query.addBindValue(code)
        self.query.addBindValue(name)
        self.query.addBindValue(category)
        self.query.exec()

    def delete_stock(self, code):
        """delete stock"""
        self.query.exec(f"DELETE FROM stocks WHERE code = '{code}';")

    def query_announcements(self, reverse=True):
        """query announcements"""
        announcements = []
        if reverse:
            self.query.exec("""
                SELECT * FROM  announcements
                WHERE state = 'READ' OR state = 'UNREAD' 
                ORDER BY ann_date DESC;""")
        else:
            self.query.exec("""
                SELECT * FROM  announcements
                WHERE state = 'READ' OR state = 'UNREAD' 
                ORDER BY ann_date;""")

        while self.query.next():
            ann = {
                "AnnouncementId": str(self.query.value(0)),
                "Code": str(self.query.value(1)),
                "Name": str(self.query.value(2)),
                "AnnouncementTitle": str(self.query.value(3)),
                "AnnouncementDate": str(self.query.value(4)),
                "AnnouncementUrl": str(self.query.value(5)),
                "AnnouncementState": str(self.query.value(6))}
            announcements.append(ann)

        return announcements

    def query_stocks(self):
        """query stocks"""
        stocks_code = []
        self.query.exec("SELECT code FROM stocks;")

        while self.query.next():
            stocks_code.append(str(self.query.value(0)))
        
        return stocks_code

    def update_announcement_state(self, ann_id, state):
        """update a specified announcement"""
        sql = f"""UPDATE announcements SET state = '{state}' WHERE ann_id = {ann_id};"""
        if self.query.exec(sql):
            print("update successfully")


if __name__ == "__main__":
    db = AnnouncementDatabase()
    # db.insert_stock("601166", "兴业银行", "A股")
    # db.insert_announcement(2, "601166", "迈瑞医疗", "迈瑞医疗年报", "2022-03-31", "http://baidu.com", "UNREAD")
    # db.insert_announcement(3, "601167", "伊利股份", "迈瑞医疗年报", "2022-03-31", "http://baidu.com", "UNREAD")
    # db.insert_announcement(4, "601168", "比亚迪", "迈瑞医疗年报", "2022-03-31", "http://baidu.com", "UNREAD")
    # db.insert_announcement(5, "601169", "招商银行", "迈瑞医疗年报", "2022-03-31", "http://baidu.com", "READ")
    # db.insert_announcement(6, "600905", "三峡能源", "中国三峡新能源（集团）股份有限公司关于回购注销限制性股票调整2021年度利润分配预案的公告", "2022-05-26", "http://static.cninfo.com.cn/finalpage/2022-05-26/1213501451.PDF", "UNREAD")
