"""
stockapi.py
date: 20220629
lvbj07@gmail.com
股票相关api
"""


import json
import re
from urllib.parse import urljoin
import os
from datetime import date
import csv
import requests
from lxml.html import etree


# 参数
STOCK_UPDATE_REPEAT_TIMES = 5


def get_other_data(stock_code):
    """
    从巨潮资讯网获取股票相关信息
    """
    url = f"http://www.cninfo.com.cn/data20/companyOverview/getHeadStripData?scode={stock_code}"
    response = requests.get(url)
    response_obj = json.loads(response.text)
    stock_data = {}
    stock_data["ZongGu"] = response_obj["data"]["records"][0]["F020N"] # 总股本，亿股
    stock_data["LiuTongGu"] = response_obj["data"]["records"][0]["F021N"] # 流通股本，亿股
    stock_data["FuZhaiLv"] = response_obj["data"]["records"][0]["F041N"] # 负债率，%
    stock_data["JingLiRun"] = response_obj["data"]["records"][0]["F102N"] # 净利润，亿
    stock_data["ZhiYaLv"] = response_obj["data"]["records"][0]["F005N"] # 质押率，%
    stock_data["YingShou"] = response_obj["data"]["records"][0]["F089N"] # 营业收入，亿
    stock_data["HuoBi"] = response_obj["data"]["records"][0]["F109N"] # 货币资金，亿
    stock_data["ROE"] = response_obj["data"]["records"][0]["F081N"]
    stock_data["ShangYu"] = response_obj["data"]["records"][0]["F115N"] # 商誉，亿
    stock_data["YingShouKuan"] = response_obj["data"]["records"][0]["F111N"] # 应收款，亿
    return stock_data


def get_market_data(stock_code):
    """
    从腾讯股票接口获取股票的市场信息
    """
    result = {}

    # A股
    if len(stock_code) == 6:
        # 上交所
        if stock_code[0] in "03":
            plate = "sz"
        # 上交所
        elif stock_code[0] == "6":
            plate = "sh"
        # 北交所
        elif stock_code[0] == "8":
            plate = "bj"
    # 港交所
    elif len(stock_code) == 5 and stock_code[0] == "0":
        plate = "hk"
    else:
        return result

    url = f"http://qt.gtimg.cn/q={plate}{stock_code}"

    repeat_times = STOCK_UPDATE_REPEAT_TIMES
    while repeat_times >= 0:
        try:
            response = requests.get(url)
            break
        except requests.exceptions.ReadTimeout as e:
            print(f"timeout while get data for {stock_code}, retry {repeat_times}")
            repeat_times -= 1
        except requests.exceptions.ConnectionError as e:
            print(f"connection error while get data for {stock_code}, retry {repeat_times}")
            repeat_times -= 1
    else:
        return result

    search_obj = re.search('"(.*)"', response.text).group(1).split("~")
    if len(search_obj) > 46:
        result = {"Name": search_obj[1], "Code": search_obj[2],
                "LatestPrice": search_obj[3], "ChangeAmount": search_obj[31],
                "ChangeRate": search_obj[32], "PETTM": search_obj[39],
                "MarketValue": search_obj[45]}
        # 港股 PB 的位置不一样
        if plate == "hk":
            result["PB"] = search_obj[58]
        else:
            result["PB"] = search_obj[46]

    return result


def get_recommend_stock(input_str):
    """
    在巨潮资讯网的搜索框内输入代码/简称/拼音/关键字/高管
    返回推荐的股票信息
    """
    url = f"http://www.cninfo.com.cn/new/information/topSearch/query?keyWord={input_str}&maxNum=10"
    response = requests.post(url)
    json_obj = json.loads(response.text)

    result = []
    if len(json_obj) > 0:
        for obj in json_obj:
            result.append({
                "OrgId": obj["orgId"],
                "Code": obj["code"],
                "Name": obj["zwjc"],
                "Category": obj["category"],
                "Pinyin": obj["pinyin"]})
    return result


def get_latest_announcement(code, size=30, category="Report"):
    """
    在巨潮资讯网根据股票代码查询获得公告
    category:
        Report, return regular reports
        Announcement, return latest Announcements
        Relation, return investor relation activities records
    """
    announcements = []
    # 利用get_recommend_stock获得org_id
    rec = get_recommend_stock(code)
    if len(rec) > 0:
        org_id = rec[0]["OrgId"]

        stock_category = rec[0]["Category"]
        code = rec[0]["Code"]

        if stock_category == "港股":
            column = "hke"
            plate = "hke"
        elif stock_category == "A股":
            if code[0] in "03":  # 深交所
                column = "szse"
                plate = "sz"
            elif code[0] == "6":  # 上交所
                column = "sse"
                plate = "sh"
            elif code[0] == "8":  # 北交所
                column = "bj"
                plate = "bj;third"

        data = {
            "stock": f"{code},{org_id}",
            "tabName": "fulltext",
            "pageSize": f"{size}",
            "pageNum": "1",
            "column": column,
            "plate": plate,
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true"}

        if category == "Report":
            data["category"] = "category_ndbg_szsh;category_sf_szsh;"
            data["tabName"] = "fulltext"
        elif category == "Relation":
            data["category"] == ""
            data["tabName"] = "relation"
        else:
            data["category"] = ""
            data["tabName"] = ""

        url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        try:
            response = requests.post(url, data=data)
        except requests.exceptions.ConnectionError as e:
            print(f"ConnectionError occurred: {e}")
            return announcements

        json_obj = json.loads(response.text)
        if json_obj["announcements"] != None:
            for obj in json_obj["announcements"]:
                announce = {
                    "Code": obj["secCode"],
                    "Name": obj["secName"],
                    "OrgId": obj["orgId"],
                    "AnnouncementId": obj["announcementId"],
                    "AnnouncementTitle": obj["announcementTitle"],
                    "AnnouncementTimestamp": obj["announcementTime"],
                    "AnnouncementDate": date.fromtimestamp(int(obj["announcementTime"])/1000).isoformat(),
                    "AnnouncementUrl": urljoin("http://static.cninfo.com.cn", obj["adjunctUrl"])}
                announcements.append(announce)
    return announcements


def get_latest_announcement2(code, size=1):
    """
    在巨潮资讯网根据股票代码查询获得公告
    category:
        Report, return regular reports
        Announcement, return latest Announcements
        Relation, return investor relation activities records
    """
    announcements = []
    # 利用get_recommend_stock获得org_id
    rec = get_recommend_stock(code)
    if len(rec) > 0:
        name = rec[0]["Name"]
        for i in range(size):
            url = "http://www.cninfo.com.cn/new/fulltextSearch/full?"
            url += f"searchkey={name}&sdate=&edate=&isfulltext=false&"
            url += f"sortName=pubdate&sortType=desc&pageNum={i+1}"
            try:
                response = requests.get(url)
            except requests.exceptions.ConnectionError as e:
                print(f"ConnectionError occurred: {e}")
                return announcements

            json_obj = json.loads(response.text)
            if json_obj["announcements"] != None:
                for obj in json_obj["announcements"]:
                    announce = {
                        "Code": obj["secCode"],
                        "Name": obj["secName"],
                        "OrgId": obj["orgId"],
                        "AnnouncementId": obj["announcementId"],
                        "AnnouncementTimestamp": obj["announcementTime"],
                        "AnnouncementDate": date.fromtimestamp(int(obj["announcementTime"])/1000).isoformat(),
                        "AnnouncementUrl": urljoin("http://static.cninfo.com.cn", obj["adjunctUrl"])}

                    title = obj["announcementTitle"]
                    title = re.sub(r'</?em>', "", title)
                    announce["AnnouncementTitle"] = title

                    announcements.append(announce)
    return announcements

def get_financial_statement(code, category):
    """
    从网易财经获取股票的财务报表
    code:
        给定股票代码
    category:
        报表的类别
        zcfzb - 资产负债表
        lrb   - 利润表
        xjllb - 现金流量表
    return:
        一个二维列表，第一行是报告日期，第一列是会计科目
    """

    # 首先查看本地缓存有没有财务报表，如果有直接读取本地文件，如果没有，从网易财经获取
    cache_directory = "cache/"

    # 获取给定code, category最新财报日期
    url = f"http://quotes.money.163.com/f10/{category}_{code}.html"
    response = requests.get(url)
    tree = etree.HTML(response.text)
    xpath = '//div[@class="col_r"]/table/tr[1]/th[1]'
    latest_date = tree.xpath(xpath)[0].text

    # 生成文件名
    file_name = f"{code}_{category}_{latest_date}.csv"

    # 如果本地不存在，从网络获取，保存在本地
    full_path = os.path.join(cache_directory, file_name)
    if not os.path.exists(full_path):
        url = f"http://quotes.money.163.com/service/{category}_{code}.html"
        response = requests.get(url)
        result = []
        for line in response.text.split("\n"):
            items = [item for item in line.split(",") if item.strip(" ").strip("\t").strip("\r") != ""]
            if items != []:
                result.append(items)
        with open(full_path, "w") as csv_f:
            csv_f.write("\n".join([",".join(line) for line in result]))

    # 从本地读取，返回
    with open(full_path, "r") as csv_f:
        statement = list(csv.reader(csv_f))
    return statement


def get_study_reports(code: str) -> list:
    """
    获取个股研究报告
    code: 个股代码，A股为6位数字的字符串
    return: 个股研报的列表，每个元素为字典，代表一个研报
    """
    res = []
    if len(code) == 6:
        url = f"https://data.eastmoney.com/report/{code}.html"
        res_obj = requests.get(url)
        res_obj.encoding = "utf-8"
        search_res = re.search("initdata = (.*);", res_obj.text)
        print(search_res)
        json_str = search_res.group(1)
        json_obj = json.loads(json_str)
        res = json_obj["data"]

        for report_obj in res:
            pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{report_obj['infoCode']}_1.pdf"
            report_obj["pdfUrl"] = pdf_url
    return res


if __name__ == "__main__":
    #res = get_latest_announcement("002594")
    # sta = get_financial_statement("601166", "zcfzb")
    # for row in sta:
    #     print(row)
    # print(get_latest_announcement2("00700"))
    # for a in get_latest_announcement2("00700"):
    #     print(a)
    reports = get_study_reports("002594")
    for report in reports:
        print(report)
