
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["DATABASE"] = os.path.join(app.root_path, "store.db")

# ---------------------- DB Helpers ----------------------
def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    conn.commit()

    if seed:
        # Only seed when table is empty
        count = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            seed_products(conn)
            conn.commit()

def seed_products(conn):
    import random
    brands = [
        ("Asus", "Asus"),
        ("Msi", "Msi"),
        ("gygabyte", "gygabyte"),
        ("Lenovo", "Lenovo"),
        ("Dell", "Dell"),
        ("Macbook", "Macbook"),
        ("monitor", "Monitor"),
        ("Desktop", "Desktop"),
    ]

    # Simple helper to generate placeholder images with text
    def img(text):
        from urllib.parse import quote_plus
        return f"https://via.placeholder.com/640x480?text={quote_plus(text)}"

    rows = []
    for brand_key, brand_label in brands:
        for i in range(1, 11):
            name = f"{brand_label} Model {i}"
            desc = f"{brand_label} performance laptop {i} with 12-core CPU, 16GB RAM, 512GB SSD. Great for creators and gamers."
            price = round(random.uniform(399, 2499), 2) if brand_key.lower() != "monitor" else round(random.uniform(99, 799), 2)
            if brand_key.lower() == "desktop":
                desc = f"{brand_label} tower PC {i} with Ryzen/Intel options, 16-64GB RAM, NVMe storage."
            if brand_key.lower() == "monitor":
                desc = f"{brand_label} {i} 27-inch 144Hz IPS display with HDR."
            image = img(f"{brand_label}+{i}")
            category = brand_label if brand_key.lower() not in ["monitor", "desktop"] else brand_label
            rows.append((name, brand_label, desc, price, image, category))

    conn.executemany(
        "INSERT INTO products (name, brand, description, price, image_url, category) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )

@app.route("/")
def index():
    conn = get_db()
    # Latest 12 for the main grid
    products  = conn.execute(
        "SELECT * FROM products ORDER BY id DESC LIMIT 12"
    ).fetchall()
    # Images for the hero carousel
    images    = conn.execute(
        "SELECT image_url, name FROM products ORDER BY id DESC LIMIT 10"
    ).fetchall()
    # Top 4 most expensive across all products (home only)
    expensive = conn.execute(
        "SELECT * FROM products ORDER BY price DESC LIMIT 6"
    ).fetchall()

    brands = ["MyStore","Asus","Msi","gygabyte","Lenovo","Dell","Macbook","monitor","Desktop"]
    return render_template(
        "index.html",
        products=products,
        images=images,
        expensive=expensive,   # home: show the right column
        brands=brands
    )


@app.route("/brand/<brand>")
def by_brand(brand):
    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE brand=? ORDER BY id DESC", (brand,)
    ).fetchall()

    brands = ["MyStore","Asus","Msi","gygabyte","Lenovo","Dell","Macbook","monitor","Desktop"]
    return render_template(
        "index.html",
        products=products,
        images=[],              # brand page: no hero (or set a custom list if you want slider)
        # NOTE: do NOT pass 'expensive' so the right column is hidden on brand pages
        brands=brands,
        current_brand=brand
    )



@app.route("/product/<int:pid>")
def product_detail(pid):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not product:
        flash("Product not found", "warning")
        return redirect(url_for("index"))
    # simple "related" products: same brand
    related = conn.execute("SELECT * FROM products WHERE brand = ? AND id != ? LIMIT 6", (product["brand"], pid)).fetchall()
    return render_template("detail.html", product=product, related=related)

# ---------------------- Admin (very light-weight) ----------------------
def require_admin():
    if not session.get("is_admin"):
        session["is_admin"] = True  # auto-auth for demo
    return True
@app.route("/admin")
def admin_dashboard():
    require_admin()
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    max_price = conn.execute("SELECT MAX(price) FROM products").fetchone()[0] or 0
    avg_price = conn.execute("SELECT AVG(price) FROM products").fetchone()[0] or 0
    by_cat = conn.execute("SELECT category, COUNT(*) as c FROM products GROUP BY category").fetchall()
    recent = conn.execute("SELECT * FROM products ORDER BY id DESC LIMIT 5").fetchall()
    return render_template(
        "admin/dashboard.html",
        total=total, max_price=max_price, avg_price=avg_price,
        by_cat=by_cat, recent=recent,
        admin_full=True,   # << full-width
    )

@app.route("/admin/products")
def admin_products():
    require_admin()
    conn = get_db()
    q = request.args.get("q","").strip()
    if q:
        products = conn.execute(
            "SELECT * FROM products WHERE name LIKE ? OR brand LIKE ? ORDER BY id DESC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("admin/products.html", products=products, q=q, admin_full=True)
@app.route("/admin/products/new", methods=["GET", "POST"])
def admin_new_product():
    require_admin()
    if request.method == "POST":
        conn = get_db()

        # grab fields from the form
        name = (request.form.get("name") or "").strip()
        brand = (request.form.get("brand") or "").strip()
        category = (request.form.get("category") or "").strip()
        description = (request.form.get("description") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()

        # price: coerce to float; default 0 if empty/invalid
        try:
            price = float(request.form.get("price", "0").strip() or 0)
        except ValueError:
            price = 0.0

        # minimal validation
        if not name:
            flash("Name is required.", "warning")
            return redirect(url_for("admin_new_product"))

        # insert
        conn.execute(
            """
            INSERT INTO products (name, brand, category, price, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, brand, category, price, description, image_url or None),
        )
        conn.commit()
        flash("Product created.", "success")
        return redirect(url_for("admin_products"))

    # GET
    return render_template("admin/new_product.html", admin_full=True)
@app.route("/admin/products/<int:pid>/edit", methods=["GET", "POST"])
def admin_edit_product(pid):
    require_admin()
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not product:
        flash("Product not found", "warning")
        return redirect(url_for("admin_products"))

    if request.method == "POST":
        # take submitted values; fall back to current values if fields are omitted
        name = (request.form.get("name") or product["name"]).strip()
        brand = (request.form.get("brand") or product["brand"]).strip()
        category = (request.form.get("category") or product["category"]).strip()
        description = (request.form.get("description") or product.get("description", "")).strip()
        image_url = (request.form.get("image_url") or product.get("image_url", None))
        try:
            price_val = request.form.get("price", None)
            price = float(price_val) if price_val not in (None, "") else product["price"]
        except ValueError:
            price = product["price"]

        if not name:
            flash("Name is required.", "warning")
            return redirect(url_for("admin_edit_product", pid=pid))

        conn.execute(
            """
            UPDATE products
               SET name = ?, brand = ?, category = ?, price = ?, description = ?, image_url = ?
             WHERE id = ?
            """,
            (name, brand, category, price, description, image_url, pid),
        )
        conn.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin_products"))

    # GET
    return render_template("admin/edit_product.html", product=product, admin_full=True)
@app.route("/admin/products/<int:pid>/delete", methods=["POST"])
def admin_delete_product(pid):
    require_admin()
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    flash("Product deleted", "info")
    return redirect(url_for("admin_products"))

@app.route("/signout")
def signout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("index"))

# CLI helper
@app.cli.command("init-db")
def _init_db_cmd():
    init_db(seed=True)
    print("Database initialized with seed data.")

if __name__ == "__main__":
    with app.app_context():
        init_db(seed=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
