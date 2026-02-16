from flask import Flask, request, render_template_string, redirect, url_for, flash, send_file
import sqlite3, os, io
from datetime import datetime

app = Flask(__name__)
app.secret_key = "ultra_secret_2026"

STORE_NAME = "🏪 سوبر ماركت أولاد قايد محمد"
ADMIN_PASSWORD = "1112"

BASE_DIR = "/var/data" if os.path.exists("/var/data") else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "supermarket.db")

# ================= قاعدة البيانات =================
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        discount REAL DEFAULT 0,
        image BLOB
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT,
        product_id INTEGER,
        qty INTEGER,
        total REAL
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON products(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id)")

    conn.commit()
    conn.close()

init_db()

# ================= أدوات =================
def get_products():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,name,price,stock,discount FROM products")
    data = cur.fetchall()
    conn.close()
    return data

def get_product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=?", (pid,))
    data = cur.fetchone()
    conn.close()
    return data

# ================= عرض الصورة =================
@app.route("/image/<int:pid>")
def image(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT image FROM products WHERE id=?", (pid,))
    img = cur.fetchone()
    conn.close()

    if img and img[0]:
        return send_file(io.BytesIO(img[0]), mimetype='image/jpeg')
    return ""

# ================= واجهة الزبون =================
@app.route("/")
def home():
    products = get_products()

    html = """
    <html dir="rtl">
    <head>
    <meta charset="UTF-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
    body{background:linear-gradient(135deg,#111,#222);color:#fff;padding:20px}
    .card{
        background:#1c1c1c;
        border:none;
        border-radius:15px;
        box-shadow:0 0 15px rgba(255,215,0,0.2);
        transition:0.3s;
    }
    .card:hover{
        transform:scale(1.05);
        box-shadow:0 0 25px rgba(255,215,0,0.5);
    }
    .btn-buy{
        background:#FFD700;
        border:none;
        color:black;
        font-weight:bold;
    }
    img{
        height:180px;
        object-fit:contain;
        padding:10px;
    }
    </style>
    </head>
    <body class="container">

    <h1 class="text-center mb-4">{{store}}</h1>

    <div class="row">
    {% for p in products %}
        <div class="col-md-3 mb-4">
            <div class="card text-center p-3">
                <img src="/image/{{p[0]}}">
                <h5>{{p[1]}}</h5>
                <p>السعر: {{p[2]}} ريال</p>
                <p>المخزون: {{p[3]}}</p>
                {% if p[4] > 0 %}
                    <p class="text-warning">خصم {{p[4]}}%</p>
                {% endif %}

                <form method="POST" action="/buy">
                    <input type="hidden" name="id" value="{{p[0]}}">
                    <input type="number" name="qty" min="1" value="1" class="form-control mb-2">
                    <button class="btn btn-buy w-100">🛒 شراء الآن</button>
                </form>
            </div>
        </div>
    {% endfor %}
    </div>

    </body>
    </html>
    """

    return render_template_string(html, products=products, store=STORE_NAME)

# ================= شراء =================
@app.route("/buy", methods=["POST"])
def buy():
    pid = request.form.get("id")
    qty = int(request.form.get("qty"))

    product = get_product(pid)
    if not product:
        return redirect("/")

    if qty > product[3]:
        flash("الكمية غير متوفرة")
        return redirect("/")

    price = product[2]
    discount = product[4]
    final = price - (price * discount / 100)
    total = final * qty

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, pid))
    cur.execute("INSERT INTO sales(datetime,product_id,qty,total) VALUES(?,?,?,?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), pid, qty, total))
    conn.commit()
    conn.close()

    flash(f"تمت العملية - الإجمالي {total}")
    return redirect("/")

# ================= لوحة المدير =================
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            return redirect("/admin")

        name = request.form.get("name")
        price = float(request.form.get("price"))
        stock = int(request.form.get("stock"))
        discount = float(request.form.get("discount"))
        image = request.files.get("image")

        img_blob = image.read() if image else None

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO products(name,price,stock,discount,image) VALUES(?,?,?,?,?)",
                        (name, price, stock, discount, img_blob))
            conn.commit()
        except:
            pass
        conn.close()

    products = get_products()

    html = """
    <html dir="rtl">
    <head>
    <meta charset="UTF-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="container p-4">

    <h2>لوحة المدير</h2>

    <form method="POST" enctype="multipart/form-data">
        كلمة المرور: <input type="password" name="password" required><br><br>
        اسم المنتج: <input name="name" required><br><br>
        السعر: <input type="number" step="0.01" name="price" required><br><br>
        الكمية: <input type="number" name="stock" required><br><br>
        الخصم %: <input type="number" step="0.01" name="discount" value="0"><br><br>
        صورة: <input type="file" name="image"><br><br>
        <button class="btn btn-warning">إضافة منتج</button>
    </form>

    <hr>
    <h4>المنتجات</h4>
    <ul>
    {% for p in products %}
        <li>{{p[1]}} - {{p[2]}} ريال</li>
    {% endfor %}
    </ul>

    </body>
    </html>
    """

    return render_template_string(html, products=products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
