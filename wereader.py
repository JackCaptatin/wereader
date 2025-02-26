import os.path
from collections import defaultdict, namedtuple
from itertools import chain
from operator import attrgetter
import pandas as pd
import requests
import json
class Book:
    def __init__(self, book_id, title, author, cover):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.cover = cover

    def __repr__(self):
        return f"{self.title} by {self.author}"
    
requests.packages.urllib3.disable_warnings()

Book = namedtuple("Book", ["bookId", "title", "author", "cover"])

headers = """
Host: i.weread.qq.com
Connection: keep-alive
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
"""
headers = dict(x.split(": ", 1) for x in headers.splitlines() if x)


def get_bookmarklist(bookId, cookies):
    """获取某本书的笔记返回md文本"""
    url = "https://i.weread.qq.com/book/bookmarklist"
    params = dict(bookId=bookId)
    r = requests.get(url, params=params, headers=headers, cookies=cookies, verify=False)

    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)
    chapters = {c["chapterUid"]: c["title"] for c in data["chapters"]}
    contents = defaultdict(list)

    for item in sorted(data["updated"], key=lambda x: x["chapterUid"]):
        chapter = item["chapterUid"]
        text = item["markText"]
        create_time = item["createTime"]
        start = int(item["range"].split("-")[0])
        contents[chapter].append((start, text))

    chapters_map = {title: level for level, title in get_chapters(int(bookId), cookies)}
    res = ""
    for c in sorted(chapters.keys()):
        title = chapters[c]
        res += "#" * chapters_map[title] + " " + title + "\n"
        for start, text in sorted(contents[c], key=lambda e: e[0]):
            res += "> " + text.strip() + "\n\n"
        res += "\n"

    return res


def get_bestbookmarks(bookId, cookies):
    """获取书籍的热门划线,返回文本"""
    url = "https://i.weread.qq.com/book/bestbookmarks"
    params = dict(bookId=bookId)
    r = requests.get(url, params=params, headers=headers, cookies=cookies, verify=False)
    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)
    chapters = {c["chapterUid"]: c["title"] for c in data["chapters"]}
    contents = defaultdict(list)
    for item in data["items"]:
        chapter = item["chapterUid"]
        text = item["markText"]
        contents[chapter].append(text)

    chapters_map = {title: level for level, title in get_chapters(int(bookId), cookies)}
    res = ""
    for c in chapters:
        title = chapters[c]
        res += "#" * chapters_map[title] + " " + title + "\n"
        for text in contents[c]:
            res += "> " + text.strip() + "\n\n"
        res += "\n"
    return res


def get_chapters(bookId, cookies):
    """获取书的目录"""
    url = "https://i.weread.qq.com/book/chapterInfos"
    data = '{"bookIds":["%d"],"synckeys":[0]}' % bookId

    r = requests.post(url, data=data, headers=headers, cookies=cookies, verify=False)

    if r.ok:
        data = r.json()
        # clipboard.copy(json.dumps(data, indent=4, sort_keys=True))
    else:
        raise Exception(r.text)

    chapters = []
    for item in data["data"][0]["updated"]:
        if "anchors" in item:
            chapters.append((item.get("level", 1), item["title"]))
            for ac in item["anchors"]:
                chapters.append((ac["level"], ac["title"]))

        elif "level" in item:
            chapters.append((item.get("level", 1), item["title"]))

        else:
            chapters.append((1, item["title"]))

    return chapters


def get_bookinfo(bookId, cookies):
    """获取书的详情"""
    url = "https://i.weread.qq.com/book/info"
    params = dict(bookId=bookId)
    r = requests.get(url, params=params, headers=headers, cookies=cookies, verify=False)

    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)
    return data

def get_books_info(cookies):
    """获取书架上的所有书籍详情，并导出到 Excel 文件"""
    books = get_bookshelf(cookies)  # 调用现有的获取书架书籍的函数
    books_info = []

    for book in books:
        try:
            book_details = get_bookinfo(book.book_id, cookies)
            # ✅ 打印 JSON 数据，查看 API 返回的结构
            print(f"📌 获取到的书籍详情（bookId: {book.book_id}）：")
            print(json.dumps(book_details, indent=4, ensure_ascii=False))  # 格式化输出 JSON
            books_info.append({
                "Book ID": book.book_id,
                "Title": book.title,
                "Author": book.author,
                "Cover": book.cover,
                "Details": book_details.get("description", "无简介"),  # 书籍的简介（如果有）
                "Publisher": book_details.get("publisher", "无出版社"),  # 出版社（如果有）
                "Price": book_details.get("price", "无价格"),  # 书籍价格（如果有）
            })
        except Exception as e:
            print(f"获取书籍 {book.title} 的详情失败: {e}")
            continue

    # 将书籍详情导出到 Excel
    export_books_details_to_excel(books_info)

def export_books_details_to_excel(books_info):
    """将书籍详情导出到 Excel 文件"""
    # 使用 pandas 创建 DataFrame
    df = pd.DataFrame(books_info)

    # 导出到 Excel 文件
    df.to_excel("books_details.xlsx", index=False, engine='openpyxl')
    print("书架书籍详情已成功导出到 'books_details.xlsx' 文件。")
    

def get_bookshelf(cookies):
    """获取书架上所有书"""
    url = "https://i.weread.qq.com/shelf/friendCommon"
    userVid = cookies.get("wr_vid")
    params = dict(userVid=userVid)
    r = requests.get(url, params=params, headers=headers, cookies=cookies, verify=False)
    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)
    finishReadBooks = [b for b in data["finishReadBooks"] if 'bookId' in b]
    recentBooks = [b for b in data["recentBooks"] if 'bookId' in b]
    books = set()
    for book in chain(finishReadBooks, recentBooks):
        if not book["bookId"].isdigit():  # 过滤公众号
            continue
        try:
            b = Book(book["bookId"], book["title"], book["author"], book["cover"])
            books.add(b)
        except Exception as e:
            pass

    books = list(books)
    books.sort(key=attrgetter("title"))

    return books


def get_notebooklist(cookies):
    """获取笔记本列表"""
    url = "https://i.weread.qq.com/user/notebooks"
    r = requests.get(url, headers=headers, cookies=cookies, verify=False)

    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)
    books = []
    for b in data["books"]:
        book = b["book"]
        b = Book(book["bookId"], book["title"], book["author"], book["cover"])
        books.append(b)
    books.sort(key=attrgetter("title"))
    return books


def get_bookcover(book, output_dir=None):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0",
        "if-modified-since": "Thu, 01 Nov 2018 11:45:36 GMT",
        "if-none-match": "d52c44c46328acfc2e0bd6f4b444f9f03e2a5be2",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    }

    url = "b".join(book.cover.rsplit("s", 1))
    r = requests.get(url, headers=headers, verify=False)
    print(r)
    if r.ok:
        data = r.content
    else:
        raise Exception(r.text)

    if output_dir is None:
        output_dir = os.path.abspath(os.path.dirname(__file__))

    path = os.path.join(output_dir, str(book.bookId) + ".jpg")
    print(path)
    with open(path, "wb") as f:
        f.write(data)


def get_readbooks():
    url = "https://i.weread.qq.com/mine/readbook"
    headers = """
accessToken: qAanBoeF
vid: 23859891
baseapi: 31
appver: 7.3.5.10161335
User-Agent: WeRead/7.3.5 WRBrand/other Dalvik/2.1.0 (Linux; U; Android 12; 22041211AC Build/SP1A.210812.016)
osver: 12
channelId: 12
basever: 7.3.5.10161334
Host: i.weread.qq.com
Connection: Keep-Alive
Accept-Encoding: gzip
"""
    headers = dict(x.split(": ", 1) for x in headers.splitlines() if x)
    params = dict(vid=23859891,star=0,yearRange="0_0",count=15,rating=0,listType=2)
    r = requests.get(url, params=params, headers=headers, verify=False)
    if r.ok:
        data = r.json()
    else:
        raise Exception(r.text)

    return data
