from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('price_history.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    category = request.args.get('category')
    query = request.args.get('query')

    conn = get_db_connection()
    if query:
        hotdeals = conn.execute("SELECT * FROM hotdeals WHERE title LIKE ? ORDER BY id DESC LIMIT 20",
                                (f'%{query}%',)).fetchall()
    elif category:
        hotdeals = conn.execute("SELECT * FROM hotdeals WHERE category=? ORDER BY id DESC LIMIT 20",
                                (category,)).fetchall()
    else:
        hotdeals = conn.execute("SELECT * FROM hotdeals ORDER BY id DESC LIMIT 20").fetchall()

    categories = [row['category'] for row in conn.execute("SELECT DISTINCT category FROM hotdeals").fetchall()]
    conn.close()

    return render_template('index.html', hotdeals=hotdeals, categories=categories, selected_category=category)

@app.route('/load-more')
def load_more():
    page = int(request.args.get('page', 1))
    offset = (page - 1) * 20
    category = request.args.get('category')
    query = request.args.get('query')

    conn = get_db_connection()
    if query:
        hotdeals = conn.execute("SELECT * FROM hotdeals WHERE title LIKE ? ORDER BY id DESC LIMIT 20 OFFSET ?",
                                (f'%{query}%', offset)).fetchall()
    elif category:
        hotdeals = conn.execute("SELECT * FROM hotdeals WHERE category=? ORDER BY id DESC LIMIT 20 OFFSET ?",
                                (category, offset)).fetchall()
    else:
        hotdeals = conn.execute("SELECT * FROM hotdeals ORDER BY id DESC LIMIT 20 OFFSET ?",
                                (offset,)).fetchall()
    conn.close()

    return render_template('_product_cards.html', hotdeals=hotdeals)

@app.route('/search')
def search():
    q = request.args.get('q')
    page = int(request.args.get('page', 1))
    offset = (page - 1) * 20

    conn = get_db_connection()
    hotdeals = conn.execute("SELECT * FROM hotdeals WHERE title LIKE ? ORDER BY id DESC LIMIT 20 OFFSET ?",
                            (f'%{q}%', offset)).fetchall()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_product_cards.html', hotdeals=hotdeals)

    return render_template('search.html', hotdeals=hotdeals, search_query=q)

if __name__ == '__main__':
    app.run(debug=True)
