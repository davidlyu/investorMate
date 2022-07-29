import urllib.request
import re
from lxml.html import etree
from urllib.error import URLError, HTTPError, ContentTooShortError


def download(url, user_agent='wswp', num_retries=2, charset='utf-8'):
    print("Downloading: ", url)
    
    handler = urllib.request.ProxyHandler({
        "http": "127.0.0.1:10809",
        "https": "127.0.0.1:10809"
    })
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(url)
    request.add_header('User-agent', user_agent)

    try:
        html = opener.open(request).read().decode(charset)
    except (URLError, HTTPError, ContentTooShortError) as e:
        print("Download error: ", e.reason)
        html = None
        if num_retries > 0:
            if hasattr(e, 'code') and 500 <= e.code < 600:
                return download(url, num_retries-1)
    return html


def get_links(html):
    """Return a list of links from html"""
    webpage_regex = re.compile("""<a [^>]+href=["'](.*?)["']""", re.IGNORECASE)
    return webpage_regex.findall(html)


if __name__ == "__main__":
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0"
    html = download("https://javgg.net/star/", user_agent=ua)

    tree = etree.HTML(html)
    xpath_str = "/html/body/div[2]/div[2]/div[2]/div/div[4]/div[1]/ul/li/a/font/font"
    xpath_str = '//div[@class="category-list-view"]/ul/li/a'
    actresses = tree.xpath(xpath_str)
    
    for actress in actresses:
        print(actress.text)
    print(len(actresses))