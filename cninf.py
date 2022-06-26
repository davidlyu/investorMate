# import urllib.request
from urllib.parse import urlparse
import re
import json
import time
import requests
from lxml.html import etree
from urllib.error import URLError, HTTPError, ContentTooShortError


class Throttle:
    """Add a delay between donwloads to the same domain"""
    def ___init___(self, delay):
        self.delay = delay
        self.domains = {}

    def wait(self, url):
        domain = urlparse(url).netloc
        last_accessed = self.domains.get(domain)

        if self.delay > 0 and last_accessed is not None:
            sleep_secs = self.delay - (time.time() - last_accessed)
            if sleep_secs > 0:
                time.sleep(sleep_secs)
        self.domains[domain] = time.time()


def download(url, user_agent=None, num_retries=2, charset='utf-8', use_proxy=False):
    print("Downloading: ", url)

    if user_agent is None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0"
    
    if use_proxy:
        proxies = {
            "http": "127.0.0.1:10809",
            "https": "127.0.0.1:10809"
        }

    headers = {'user-agent': user_agent}
    try:
        if use_proxy:
            r = requests.get(url, headers=headers, proxies=proxies)
        else:
            r = requests.get(url, headers=headers)
        html = r.text
    except (requests.ConnectionError, requests.HTTPError, requests.Timeout, requests.TooManyRedirects) as e:
        print("Some exception occured: ", e.reason)
        html = None
        if num_retries > 0:
            if 500 <= r.status_code < 600:
                return download(url, num_retries-1)
    return html


def get_links(html):
    """Return a list of links from html"""
    webpage_regex = re.compile("""<a [^>]+href=["'](.*?)["']""", re.IGNORECASE)
    return webpage_regex.findall(html)


def get_announcements_from_url(url):
    html = download(url)
    titles = []
    if html is not None:
        json_obj = json.loads(html)
        for ann in json_obj["announcements"]:
            title = ann["announcementTitle"]
            title = re.sub(r'</?em>', "", title)
            titles.append(title)
    else:
        print(f"Some exceptions happend in get_announcements_from_url, return empty list (URL: {url})")
    return titles


def get_all_announcements():
    url_tmpl = "http://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=比亚迪&sdate=&edate=&isfulltext=false&sortName=pubdate&sortType=desc&pageNum=%d"
    html = download(url_tmpl % 1)
    titles = []
    if html is not None:
        json_obj = json.loads(html)
        titles = titles + get_announcements_from_url(url_tmpl % 1)
        total_pages = json_obj["totalpages"]
        if total_pages > 1:
            for i in range(2, total_pages+2):
                time.sleep(1)
                titles = titles + get_announcements_from_url(url_tmpl % i)

    return titles
                

if __name__ == "__main__":
    titles = get_all_announcements()
    for title in titles:
        print(title)
        
