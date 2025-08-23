
# MyStore — Flask + Bootstrap + SQLite

A simple laptop shop with:
- Navbar items: MyStore, Asus, Msi, gygabyte, Lenovo, Dell, Macbook, monitor, Desktop
- Auto image slider (Bootstrap Carousel) pulling images from DB
- Home/product grid (like your first screenshot)
- Product detail page (like your second screenshot)
- Admin: Dashboard, product list (edit/delete), add product (by image URL), sign out

## Run

```bash
cd laptop_store_flask
python3 -m venv venv && source venv/bin/activate   # (Windows: venv\Scripts\activate)
pip install flask
python app.py
# open http://127.0.0.1:5000/
```

The DB seeds on first run with 80 products (10 for each brand).  
Use the **Admin** link in the navbar to manage products.
