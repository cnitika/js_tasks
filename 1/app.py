# app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from functools import wraps
import sqlite3, pandas as pd
from collections import Counter
import os, datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.secret_key = 'super-secret-key'
DB_NAME = 'clicks.db'

# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

# --- Init DB ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            product TEXT,
            ip TEXT,
            watch_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            ip TEXT,
            total_watch_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/click', methods=['POST'])
def click():
    data = request.get_json()
    user = data['user']
    product = data['product']
    watch_time = data.get('watch_time', 0)
    ip = request.remote_addr

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO clicks (user, product, ip, watch_time) VALUES (?, ?, ?, ?)',
              (user, product, ip, watch_time))
    conn.commit()

    # Recommend top 2 products
    c.execute('SELECT product FROM clicks WHERE user = ?', (user,))
    products = [row[0] for row in c.fetchall()]
    recommendations = [p for p, _ in Counter(products).most_common(2)]

    conn.close()
    return jsonify({"message": "Click recorded", "recommendations": recommendations})

@app.route('/exit', methods=['POST'])
def exit_page():
    data = request.get_json()
    user = data['user']
    watch_time = data.get('watch_time', 0)
    ip = request.remote_addr

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO sessions (user, ip, total_watch_time) VALUES (?, ?, ?)',
              (user, ip, watch_time))
    conn.commit()
    conn.close()
    return jsonify({"message": "Watch time recorded"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    days = int(request.args.get('days', 0))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    query_suffix = ""
    if days > 0:
        date_limit = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        query_suffix = f" WHERE date(created_at) >= '{date_limit}'"

    c.execute(f'''SELECT user, COUNT(*) FROM clicks{query_suffix} GROUP BY user ORDER BY COUNT(*) DESC''')
    top_users = c.fetchall()

    c.execute(f'''SELECT product, COUNT(*) FROM clicks{query_suffix} GROUP BY product ORDER BY COUNT(*) DESC''')
    top_products = c.fetchall()

    c.execute('''SELECT user, SUM(total_watch_time) FROM sessions GROUP BY user ORDER BY SUM(total_watch_time) DESC''')
    top_watch_time = c.fetchall()

    conn.close()
    return render_template("dashboard.html", top_users=top_users, top_products=top_products, top_watch_time=top_watch_time)

@app.route('/export')
@login_required
def export_excel():
    conn = sqlite3.connect(DB_NAME)
    df_clicks = pd.read_sql_query("SELECT * FROM clicks", conn)
    df_sessions = pd.read_sql_query("SELECT * FROM sessions", conn)

    file_path = "user_data.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df_clicks.to_excel(writer, sheet_name='Clicks', index=False)
        df_sessions.to_excel(writer, sheet_name='Sessions', index=False)

    conn.close()
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

