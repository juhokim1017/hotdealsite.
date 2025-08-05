from flask import Flask, render_template, request
import requests, datetime, sqlite3
from urllib.parse import quote
from collections import defaultdict

app = Flask(__name__)

NAVER_CLIENT_ID = "snUgCPwELuh2Gh4S1ifV"
NAVER_CLIENT_SECRET = "m49FxLN16o"
LINKPRICE_PARTNER_CODE = "A100698035"

CATEGORY_KEYWORDS = {
    "편의점": ["편의점 행사", "편의점 1+1", "편의점 할인"],
    "마트": ["이마트 세일", "롯데마트 행사", "홈플러스 할인"],
    "가전": ["노트북 할인", "에어컨 특가", "TV 할인"],
    "패션": ["운동화 특가", "패딩 세일", "셔츠 할인"],
    "식품": ["라면 할인", "과자 세일", "음료 특가"],
    "가구": ["책상 할인", "의자 세일", "소파 특가"]
}

DB_PATH = "price_history.db"
search_counts = defaultdict(int)


# DB 초기화
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            price INTEGER
        )
    ''')
    conn.commit()
    conn.close()


def save_price_history(title, price):
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO price_history (title, date, price) VALUES (?, ?, ?)", (title, date_str, price))
    conn.commit()
    conn.close()


def convert_to_affiliate_link(original_url):
    if LINKPRICE_PARTNER_CODE:
        if "gmarket.co.kr" in original_url:
            return f"https://click.linkprice.com/click.php?m=gmarket&a={LINKPRICE_PARTNER_CODE}&l={original_url}"
        elif "11st.co.kr" in original_url:
            return f"https://click.linkprice.com/click.php?m=11st&a={LINKPRICE_PARTNER_CODE}&l={original_url}"
    return original_url


def search_naver(keyword):
    encoded_keyword = quote(keyword)
    url = f"https://openapi.naver.com/v1/search/shop.json?query={encoded_keyword}&display=20&sort=asc"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    res = requests.get(url, headers=headers, timeout=5)
    if res.status_code != 200:
        return []
    data = res.json()
    results = []
    for item in data.get("items", []):
        title = item["title"].replace("<b>", "").replace("</b>", "")
        price = int(item['lprice'])
        save_price_history(title, price)
        link = convert_to_affiliate_link(item["link"])
        results.append({
            "title": title,
            "desc": item["mallName"],
            "price": price,
            "price_text": f"{price:,}원",
            "link": link,
            "image": item["image"],
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "discount_flag": False
        })
    return results


def merge_popular_keywords():
    user_keywords = sorted(search_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    user_keywords_list = [kw for kw, _ in user_keywords]
    base_keywords = ["무선청소기", "에어프라이어", "게이밍의자", "노트북", "선풍기", "캠핑의자", "블루투스이어폰", "스마트워치"]
    merged = list(dict.fromkeys(user_keywords_list + base_keywords))
    return merged[:10]


def get_hotdeals(category=None):
    hotdeals = []
    if category and category in CATEGORY_KEYWORDS:
        keywords = CATEGORY_KEYWORDS[category]
    else:
        keywords = sum(CATEGORY_KEYWORDS.values(), [])
    for kw in keywords:
        hotdeals.extend(search_naver(kw))
    return hotdeals


@app.route("/")
def index():
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    query = request.args.get("query")
    per_page = 12

    if query:
        hotdeals = search_naver(query)
    else:
        hotdeals = get_hotdeals(category)

    total_pages = (len(hotdeals) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    hotdeals_page = hotdeals[start:end]

    top_keywords = merge_popular_keywords()

    return render_template(
        "index.html",
        hotdeals=hotdeals_page,
        categories=list(CATEGORY_KEYWORDS.keys()),
        selected_category=category,
        top_keywords=top_keywords,
        total_pages=total_pages,
        current_page=page,
        search_query=query
    )


@app.route("/load-more")
def load_more():
    category = request.args.get("category")
    query = request.args.get("query")
    page = int(request.args.get("page", 1))
    per_page = 12

    if query:
        hotdeals = search_naver(query)
    else:
        hotdeals = get_hotdeals(category)

    start = (page - 1) * per_page
    end = start + per_page
    hotdeals_page = hotdeals[start:end]
    return render_template("_product_cards.html", hotdeals=hotdeals_page)


# 🔍 검색 라우트 추가
@app.route("/search")
def search():
    query = request.args.get("q")
    page = int(request.args.get("page", 1))
    per_page = 12

    if not query:
        return render_template("search.html", hotdeals=[], query="", total_pages=0, current_page=page)

    search_counts[query] += 1
    hotdeals = search_naver(query)

    total_pages = (len(hotdeals) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    hotdeals_page = hotdeals[start:end]

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("_product_cards.html", hotdeals=hotdeals_page)

    return render_template(
        "search.html",
        hotdeals=hotdeals_page,
        query=query,
        total_pages=total_pages,
        current_page=page
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
