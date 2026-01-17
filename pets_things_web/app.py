from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from dotenv import load_dotenv
import os
import re
from db import get_user_by_email, create_user, email_exists

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# ==================== DECORATORS ====================

def login_required(f):
    """
    Decorator to protect routes that require authentication.
    Redirects to login page if user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to restrict access based on user role.
    Usage: @role_required('admin') or @role_required('admin', 'employee')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            if session.get('role') not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== ROUTES ====================
from flask import render_template
from db import get_connection

@app.route('/products')
def products():
    conn = get_connection()
    if not conn:
        return render_template(
            'products.html',
            products=[],
            categories=[],
            selected_category_id=None,
            min_price=None,
            max_price=None,
            search="",
            error="Unable to connect to database",
            page_title="All Products"
        )

    try:
        cursor = conn.cursor(dictionary=True)

        # 1) Read filters from URL
        category_id = request.args.get('category_id', type=int)
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        search = (request.args.get('search') or "").strip()

        # 2) Categories for dropdown
        cursor.execute("""
            SELECT category_id, category_name
            FROM category
            ORDER BY category_name ASC
        """)
        categories = cursor.fetchall()

        # 3) Base query
        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                c.category_name,
                p.unit_price,
                p.description,
                p.is_active,
                p.category_id
            FROM product p
            INNER JOIN category c ON p.category_id = c.category_id
        """

        # 4) Dynamic conditions
        conditions = []
        params = []

        if category_id:
            conditions.append("p.category_id = %s")
            params.append(category_id)

        if min_price is not None:
            conditions.append("p.unit_price >= %s")
            params.append(min_price)

        if max_price is not None:
            conditions.append("p.unit_price <= %s")
            params.append(max_price)

        if search:
            conditions.append("p.product_name LIKE %s")
            params.append(f"%{search}%")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY p.product_name ASC"

        cursor.execute(sql, params)
        products = cursor.fetchall()

        return render_template(
            'products.html',
            products=products,
            categories=categories,
            selected_category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            search=search,
            error=None,
            page_title="All Products"
        )

    finally:
        cursor.close()
        conn.close()




@app.route('/products/active')
def active_products():
    conn = get_connection()
    if not conn:
        return render_template(
            'products.html',
            products=[],
            categories=[],
            selected_category_id=None,
            min_price=None,
            max_price=None,
            search="",
            error="Unable to connect to database",
            page_title="Active Products"
        )

    try:
        cursor = conn.cursor(dictionary=True)

        category_id = request.args.get('category_id', type=int)
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        search = (request.args.get('search') or "").strip()

        cursor.execute("""
            SELECT category_id, category_name
            FROM category
            ORDER BY category_name ASC
        """)
        categories = cursor.fetchall()

        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                c.category_name,
                p.unit_price,
                p.description,
                p.is_active,
                p.category_id
            FROM product p
            INNER JOIN category c ON p.category_id = c.category_id
            WHERE p.is_active = 1
        """

        params = []

        if category_id:
            sql += " AND p.category_id = %s"
            params.append(category_id)

        if min_price is not None:
            sql += " AND p.unit_price >= %s"
            params.append(min_price)

        if max_price is not None:
            sql += " AND p.unit_price <= %s"
            params.append(max_price)

        if search:
            sql += " AND p.product_name LIKE %s"
            params.append(f"%{search}%")

        sql += " ORDER BY p.product_name ASC"

        cursor.execute(sql, params)
        products = cursor.fetchall()

        return render_template(
            'products.html',
            products=products,
            categories=categories,
            selected_category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            search=search,
            error=None,
            page_title="Active Products"
        )

    finally:
        cursor.close()
        conn.close()



######################
@app.route("/products/add", methods=["GET", "POST"])
@role_required("admin", "employee")
def add_product():
    conn = get_connection()
    if not conn:
        flash("DB connection failed.", "danger")
        return redirect(url_for("products"))

    try:
        cur = conn.cursor(dictionary=True)

        # categories for dropdown
        cur.execute("SELECT category_id, category_name FROM category ORDER BY category_name")
        categories = cur.fetchall()

        if request.method == "POST":
            name = (request.form.get("product_name") or "").strip()
            category_id = request.form.get("category_id", type=int)
            unit_price = request.form.get("unit_price", type=float)
            description = (request.form.get("description") or "").strip()
            is_active = 1 if request.form.get("is_active") == "1" else 0

            # basic validation
            if not name or not category_id or unit_price is None:
                flash("Please fill name, category, and price.", "warning")
                return render_template("product_form.html",
                                       mode="add",
                                       categories=categories,
                                       product=None)

            # Start transaction
            try:
                # 1) Insert product
                cur.execute("""
                    INSERT INTO product (product_name, category_id, unit_price, description, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, category_id, unit_price, description, is_active))
                
                # 2) Get the newly created product_id
                product_id = cur.lastrowid
                
                # 3) Create stock rows for all branches
                cur.execute("""
                    INSERT INTO stock (branch_id, product_id, on_hand_qty, min_qty, last_restock_date)
                    SELECT branch_id, %s, 0, 5, NULL
                    FROM branch
                """, (product_id,))
                
                # Commit transaction
                conn.commit()
                
                flash(f"Product added successfully with stock initialized in {cur.rowcount} branches.", "success")
                return redirect(url_for("products"))
                
            except Exception as e:
                # Rollback on error
                conn.rollback()
                print(f"Transaction error: {e}")
                flash("Failed to add product. Please try again.", "danger")
                return render_template("product_form.html",
                                       mode="add",
                                       categories=categories,
                                       product=None)

        return render_template("product_form.html",
                               mode="add",
                               categories=categories,
                               product=None)

    finally:
        cur.close()
        conn.close()

##########################
@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@role_required("admin", "employee")
def edit_product(product_id):
    conn = get_connection()
    if not conn:
        flash("DB connection failed.", "danger")
        return redirect(url_for("products"))

    try:
        cur = conn.cursor(dictionary=True)

        # get product
        cur.execute("SELECT * FROM product WHERE product_id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            flash("Product not found.", "warning")
            return redirect(url_for("products"))

        # categories
        cur.execute("SELECT category_id, category_name FROM category ORDER BY category_name")
        categories = cur.fetchall()

        if request.method == "POST":
            name = (request.form.get("product_name") or "").strip()
            category_id = request.form.get("category_id", type=int)
            unit_price = request.form.get("unit_price", type=float)
            description = (request.form.get("description") or "").strip()
            is_active = 1 if request.form.get("is_active") == "1" else 0

            if not name or not category_id or unit_price is None:
                flash("Please fill name, category, and price.", "warning")
                return render_template("product_form.html",
                                       mode="edit",
                                       categories=categories,
                                       product=product)

            cur.execute("""
                UPDATE product
                SET product_name = %s,
                    category_id = %s,
                    unit_price = %s,
                    description = %s,
                    is_active = %s
                WHERE product_id = %s
            """, (name, category_id, unit_price, description, is_active, product_id))
            conn.commit()

            flash("Product updated successfully.", "success")
            return redirect(url_for("products"))

        return render_template("product_form.html",
                               mode="edit",
                               categories=categories,
                               product=product)

    finally:
        cur.close()
        conn.close()
############
@app.route("/products/<int:product_id>/delete", methods=["POST"])
@role_required("admin", "employee")
def delete_product(product_id):
    conn = get_connection()
    if not conn:
        flash("DB connection failed.", "danger")
        return redirect(url_for("products"))

    try:
        cur = conn.cursor(dictionary=True)

        cur.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
        conn.commit()

        flash("Product deleted successfully.", "success")
        return redirect(url_for("products"))

    finally:
        cur.close()
        conn.close()



@app.route('/inventory')
@role_required('admin', 'employee')
def inventory():
    conn = get_connection()
    if not conn:
        return render_template(
            'inventory.html',
            inventory=[],
            branches=[],
            categories=[],
            selected_branch_id=None,
            selected_category_id=None,
            selected_status="",
            sort="branch_name",
            dir="asc",
            page=1,
            total_pages=1,
            total_records=0,
            summary={
                "total_rows": 0,
                "low_count": 0,
                "ok_count": 0,
                "out_of_stock": 0,
                "unique_products": 0,
                "unique_branches": 0
            },
            error="Unable to connect to database"
        )

    try:
        cur = conn.cursor(dictionary=True)

        # ----------------------------
        # 1) Read filters from query string
        # ----------------------------
        branch_id = request.args.get('branch_id', type=int)
        category_id = request.args.get('category_id', type=int)
        status = (request.args.get('status') or "").strip().upper()  # "LOW" / "OK" / ""

        # ----------------------------
        # 2) Sorting + pagination inputs
        # ----------------------------
        sort = (request.args.get('sort') or "branch_name").strip()
        direction = (request.args.get('dir') or "asc").strip().lower()
        direction = "desc" if direction == "desc" else "asc"

        page = request.args.get('page', default=1, type=int)
        if page < 1:
            page = 1

        per_page = 15
        offset = (page - 1) * per_page

        # ----------------------------
        # 3) Data for dropdowns
        # ----------------------------
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        cur.execute("SELECT category_id, category_name FROM category ORDER BY category_name")
        categories = cur.fetchall()

        # ----------------------------
        # 4) Build WHERE conditions dynamically
        # ----------------------------
        conditions = []
        params = []

        if branch_id:
            conditions.append("s.branch_id = %s")
            params.append(branch_id)

        if category_id:
            conditions.append("p.category_id = %s")
            params.append(category_id)

        # status filter: LOW means on_hand <= min, OK means on_hand > min
        if status == "LOW":
            conditions.append("s.on_hand_qty <= s.min_qty")
        elif status == "OK":
            conditions.append("s.on_hand_qty > s.min_qty")

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # ----------------------------
        # 5) Whitelist sorting (prevents SQL injection)
        # ----------------------------
        sort_map = {
            "branch_name": "b.branch_name",
            "product_name": "p.product_name",
            "category_name": "c.category_name",
            "on_hand_qty": "s.on_hand_qty",
            "min_qty": "s.min_qty",
            "last_restock_date": "s.last_restock_date",
            "status": "stock_status"
        }
        sort_sql = sort_map.get(sort, "b.branch_name")

        # ----------------------------
        # 6) Total records (for pagination)
        # ----------------------------
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM stock s
            JOIN product p  ON s.product_id = p.product_id
            JOIN category c ON p.category_id = c.category_id
            JOIN branch b   ON s.branch_id = b.branch_id
            {where_clause}
        """
        cur.execute(count_query, params)
        total_records = cur.fetchone()["total"]
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # If page is too big, clamp and recompute offset
        if page > total_pages:
            page = total_pages
            offset = (page - 1) * per_page

        # ----------------------------
        # 7) Main SELECT (table rows)
        # ----------------------------
        base_select = f"""
            SELECT
                s.branch_id,
                s.product_id,
                b.branch_name,
                p.product_name,
                c.category_name,
                s.on_hand_qty,
                s.min_qty,
                s.last_restock_date,
                CASE
                    WHEN s.on_hand_qty <= s.min_qty THEN 'LOW'
                    ELSE 'OK'
                END AS stock_status
            FROM stock s
            JOIN product p  ON s.product_id = p.product_id
            JOIN category c ON p.category_id = c.category_id
            JOIN branch b   ON s.branch_id = b.branch_id
            {where_clause}
            ORDER BY {sort_sql} {direction}
            LIMIT %s OFFSET %s
        """
        cur.execute(base_select, params + [per_page, offset])
        rows = cur.fetchall()

        # ----------------------------
        # 8) Summary cards (FILTERED – matches current view)
        # ----------------------------
        summary_query = f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN s.on_hand_qty <= s.min_qty THEN 1 ELSE 0 END) AS low_count,
                SUM(CASE WHEN s.on_hand_qty >  s.min_qty THEN 1 ELSE 0 END) AS ok_count,
                SUM(CASE WHEN s.on_hand_qty = 0 THEN 1 ELSE 0 END) AS out_of_stock,
                COUNT(DISTINCT s.product_id) AS unique_products,
                COUNT(DISTINCT s.branch_id) AS unique_branches
            FROM stock s
            JOIN product p  ON s.product_id = p.product_id
            JOIN category c ON p.category_id = c.category_id
            JOIN branch b   ON s.branch_id = b.branch_id
            {where_clause}
        """
        cur.execute(summary_query, params)
        summary = cur.fetchone() or {
            "total_rows": 0,
            "low_count": 0,
            "ok_count": 0,
            "out_of_stock": 0,
            "unique_products": 0,
            "unique_branches": 0
        }

        # MySQL SUM can return None when there are no rows
        for k in ["low_count", "ok_count", "out_of_stock"]:
            summary[k] = summary[k] or 0

        return render_template(
            'inventory.html',
            inventory=rows,
            branches=branches,
            categories=categories,
            selected_branch_id=branch_id,
            selected_category_id=category_id,
            selected_status=status,
            sort=sort,
            dir=direction,
            page=page,
            total_pages=total_pages,
            total_records=total_records,
            summary=summary,
            error=None
        )

    except Exception as e:
        print(f"Inventory query error: {e}")
        return render_template(
            'inventory.html',
            inventory=[],
            branches=[],
            categories=[],
            selected_branch_id=None,
            selected_category_id=None,
            selected_status="",
            sort="branch_name",
            dir="asc",
            page=1,
            total_pages=1,
            total_records=0,
            summary={
                "total_rows": 0,
                "low_count": 0,
                "ok_count": 0,
                "out_of_stock": 0,
                "unique_products": 0,
                "unique_branches": 0
            },
            error="Error loading inventory"
        )
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()




@app.route('/inventory/restock', methods=['POST'])
@role_required('admin', 'employee')
def restock_inventory():
    branch_id = request.form.get('branch_id', type=int)
    product_id = request.form.get('product_id', type=int)
    amount = request.form.get('restock_qty', type=int)

    if not branch_id or not product_id or not amount or amount < 1:
        flash("Invalid restock request.", "danger")
        return redirect(url_for('inventory'))

    conn = get_connection()
    if not conn:
        flash("DB connection failed.", "danger")
        return redirect(url_for('inventory'))

    cur = None
    try:
        performed_by = session.get("user_id")  # who restocked (admin/employee)

        cur = conn.cursor()
        conn.start_transaction()

        # 1) Update stock
        cur.execute("""
            UPDATE stock
            SET on_hand_qty = on_hand_qty + %s,
                last_restock_date = NOW()
            WHERE branch_id = %s AND product_id = %s
        """, (amount, branch_id, product_id))

        # If no row updated, do not log anything
        if cur.rowcount == 0:
            conn.rollback()
            flash("Stock row not found for this product and branch.", "danger")
            return redirect(url_for('inventory'))

        # 2) Log movement (RESTOCK) ✅
        cur.execute("""
            INSERT INTO stock_movement
                (branch_id, product_id, change_qty, movement_type, reference_sale_id, performed_by)
            VALUES
                (%s, %s, %s, 'RESTOCK', NULL, %s)
        """, (branch_id, product_id, amount, performed_by))

        conn.commit()
        flash("Stock updated successfully.", "success")
        return redirect(request.referrer or url_for('inventory'))

    except Error as e:
        conn.rollback()
        print(f"Restock error: {e}")
        flash("Error updating stock.", "danger")
        return redirect(url_for('inventory'))

    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()



@app.context_processor
def inject_low_stock_badge():
    """
    Makes low_stock_count available in ALL templates.
    Only computed for admin/employee.
    """
    if session.get("role") not in ("admin", "employee"):
        return {"low_stock_count": None}

    conn = get_connection()
    if not conn:
        return {"low_stock_count": None}

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS cnt FROM stock WHERE on_hand_qty <= min_qty")
        low_stock_count = cur.fetchone()["cnt"]
        return {"low_stock_count": low_stock_count}
    except Error as e:
        print(f"Low stock badge error: {e}")
        return {"low_stock_count": None}
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


def get_low_stock_count():
    """
    Helper function to get low stock count.
    """
    conn = get_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS cnt FROM stock WHERE on_hand_qty <= min_qty")
        result = cur.fetchone()
        return result["cnt"] if result else 0
    except Exception as e:
        print(f"get_low_stock_count error: {e}")
        return 0
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


def get_today_sales_summary():
    """
    Helper function to get today's sales summary.
    """
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT 
                COUNT(*) AS total_sales,
                SUM(total_amount) AS total_revenue
            FROM sale
            WHERE DATE(sale_date) = CURDATE()
        """)
        result = cur.fetchone()
        return result if result else {"total_sales": 0, "total_revenue": 0}
    except Exception as e:
        print(f"get_today_sales_summary error: {e}")
        return None
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


@app.route("/sales/new", methods=["GET", "POST"])
@role_required("admin", "employee")
def sales_new():
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("dashboard"))

    try:
        cur = conn.cursor(dictionary=True)

        # 1) Load branches for dropdown
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        # 2) Load customers (optional)
        # If you store customers as users with role='customer'
        cur.execute("""
            SELECT user_id, full_name
            FROM users
            WHERE role = 'customer' AND is_active = 1
            ORDER BY full_name
        """)
        customers = cur.fetchall()

        if request.method == "POST":
            branch_id = request.form.get("branch_id", type=int)
            customer_id_raw = request.form.get("customer_id", "").strip()
            customer_id = int(customer_id_raw) if customer_id_raw else None

            employee_id = session.get("user_id")  # who is doing the sale

            if not branch_id:
                flash("Please select a branch.", "warning")
                return render_template("sales_new.html",
                                       branches=branches,
                                       customers=customers,
                                       selected_branch_id=branch_id,
                                       selected_customer_id=customer_id)

            # 3) Insert sale header
            cur2 = conn.cursor()  # normal cursor is fine for insert
            cur2.execute("""
                INSERT INTO sale (branch_id, employee_id, customer_id, total_amount)
                VALUES (%s, %s, %s, 0.00)
            """, (branch_id, employee_id, customer_id))
            conn.commit()

            sale_id = cur2.lastrowid
            cur2.close()

            flash("Sale created. Add items now.", "success")
            return redirect(url_for("sale_detail", sale_id=sale_id))

        # GET
        return render_template("sales_new.html",
                               branches=branches,
                               customers=customers,
                               selected_branch_id=None,
                               selected_customer_id=None)

    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()
        conn.close()


@app.route("/sales/<int:sale_id>")
@role_required("admin", "employee")
def sale_detail(sale_id):
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("dashboard"))

    try:
        cur = conn.cursor(dictionary=True)

        # 1) Get sale header
        cur.execute("""
            SELECT
                s.sale_id,
                s.branch_id,
                b.branch_name,
                s.sale_date,
                s.employee_id,
                e.full_name AS employee_name,
                s.customer_id,
                cu.full_name AS customer_name,
                s.total_amount
            FROM sale s
            JOIN branch b ON s.branch_id = b.branch_id
            JOIN users e ON s.employee_id = e.user_id
            LEFT JOIN users cu ON s.customer_id = cu.user_id
            WHERE s.sale_id = %s
        """, (sale_id,))
        sale = cur.fetchone()

        if not sale:
            flash("Sale not found.", "warning")
            return redirect(url_for("sales_new"))

        # 2) Products dropdown (active only)
        cur.execute("""
            SELECT product_id, product_name, unit_price
            FROM product
            WHERE is_active = 1
            ORDER BY product_name
        """)
        products = cur.fetchall()

        # 3) Sale lines
        cur.execute("""
            SELECT
                sl.sale_line_id,
                sl.product_id,
                p.product_name,
                sl.quantity,
                sl.unit_price,
                sl.line_total
            FROM sale_line sl
            JOIN product p ON sl.product_id = p.product_id
            WHERE sl.sale_id = %s
            ORDER BY sl.sale_line_id
        """, (sale_id,))
        lines = cur.fetchall()

        # 4) Compute total from lines (safe)
        total = sum(float(l["line_total"]) for l in lines) if lines else 0.0

        return render_template(
            "sale_detail.html",
            sale=sale,
            products=products,
            lines=lines,
            computed_total=total,
            error=None
        )

    finally:
        cur.close()
        conn.close()

@app.route("/sales/<int:sale_id>/receipt")
@role_required("admin", "employee")
def sale_receipt(sale_id):
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("sales_list"))

    try:
        cur = conn.cursor(dictionary=True)

        # Sale header
        cur.execute("""
            SELECT
                s.sale_id,
                s.sale_date,
                s.total_amount,
                b.branch_name,
                e.full_name AS employee_name,
                cu.full_name AS customer_name
            FROM sale s
            JOIN branch b ON s.branch_id = b.branch_id
            JOIN users e ON s.employee_id = e.user_id
            LEFT JOIN users cu ON s.customer_id = cu.user_id
            WHERE s.sale_id = %s
        """, (sale_id,))
        sale = cur.fetchone()

        if not sale:
            flash("Sale not found.", "warning")
            return redirect(url_for("sales_list"))

        # Sale lines
        cur.execute("""
            SELECT
                p.product_name,
                sl.quantity,
                sl.unit_price,
                sl.line_total
            FROM sale_line sl
            JOIN product p ON sl.product_id = p.product_id
            WHERE sl.sale_id = %s
        """, (sale_id,))
        items = cur.fetchall()

        return render_template(
            "sale_receipt.html",
            sale=sale,
            items=items
        )

    finally:
        cur.close()
        conn.close()


@app.route("/sales/<int:sale_id>/add-item", methods=["POST"])
@role_required("admin", "employee")
def sale_add_item(sale_id):
    product_id = request.form.get("product_id", type=int)
    qty = request.form.get("quantity", type=int)

    if not product_id or not qty or qty <= 0:
        flash("Please select a product and valid quantity.", "warning")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    try:
        cur = conn.cursor(dictionary=True)

        # 1) Get product price (price at time of sale)
        cur.execute("SELECT unit_price FROM product WHERE product_id = %s", (product_id,))
        p = cur.fetchone()
        if not p:
            flash("Product not found.", "warning")
            return redirect(url_for("sale_detail", sale_id=sale_id))

        unit_price = float(p["unit_price"])

        # 2) Check if this product already exists in sale_line for this sale
        cur.execute("""
            SELECT sale_line_id, quantity
            FROM sale_line
            WHERE sale_id = %s AND product_id = %s
        """, (sale_id, product_id))
        existing = cur.fetchone()

        if existing:
            new_qty = int(existing["quantity"]) + qty
            new_total = new_qty * unit_price

            cur.execute("""
                UPDATE sale_line
                SET quantity = %s,
                    unit_price = %s,
                    line_total = %s
                WHERE sale_line_id = %s
            """, (new_qty, unit_price, new_total, existing["sale_line_id"]))
        else:
            line_total = qty * unit_price
            cur.execute("""
                INSERT INTO sale_line (sale_id, product_id, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s)
            """, (sale_id, product_id, qty, unit_price, line_total))

        conn.commit()
        flash("Item added.", "success")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    except Exception as e:
        conn.rollback()
        print("sale_add_item error:", e)
        flash("Failed to add item.", "danger")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    finally:
        cur.close()
        conn.close()

@app.route("/sales/<int:sale_id>/complete", methods=["POST"])
@role_required("admin", "employee")
def sale_complete(sale_id):
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    cur = None
    try:
        performed_by = session.get("user_id")  # who completed the sale

        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # 1) Get sale header (branch_id needed because stock is per branch)
        cur.execute("SELECT sale_id, branch_id FROM sale WHERE sale_id = %s", (sale_id,))
        sale = cur.fetchone()
        if not sale:
            conn.rollback()
            flash("Sale not found.", "warning")
            return redirect(url_for("sales_new"))

        branch_id = sale["branch_id"]

        # 2) Get sale lines
        cur.execute("""
            SELECT product_id, quantity, line_total
            FROM sale_line
            WHERE sale_id = %s
        """, (sale_id,))
        lines = cur.fetchall()

        if not lines:
            conn.rollback()
            flash("Add at least one item before completing the sale.", "warning")
            return redirect(url_for("sale_detail", sale_id=sale_id))

        # 3) Check stock + deduct safely
        for line in lines:
            pid = line["product_id"]
            qty = int(line["quantity"])

            # Lock stock row to avoid race conditions
            cur.execute("""
                SELECT on_hand_qty
                FROM stock
                WHERE branch_id = %s AND product_id = %s
                FOR UPDATE
            """, (branch_id, pid))
            st = cur.fetchone()

            if not st:
                conn.rollback()
                flash(f"Stock row missing for product #{pid} in this branch.", "danger")
                return redirect(url_for("sale_detail", sale_id=sale_id))

            on_hand = int(st["on_hand_qty"])
            if qty > on_hand:
                conn.rollback()
                flash(f"Not enough stock for product #{pid}. Available: {on_hand}.", "warning")
                return redirect(url_for("sale_detail", sale_id=sale_id))

            # Deduct stock
            cur.execute("""
                UPDATE stock
                SET on_hand_qty = on_hand_qty - %s
                WHERE branch_id = %s AND product_id = %s
            """, (qty, branch_id, pid))

            # 4) Log movement (SALE) ✅ (negative quantity)
            cur.execute("""
                INSERT INTO stock_movement
                    (branch_id, product_id, change_qty, movement_type, reference_sale_id, performed_by)
                VALUES
                    (%s, %s, %s, 'SALE', %s, %s)
            """, (branch_id, pid, -qty, sale_id, performed_by))

        # 5) Update sale total
        total_amount = sum(float(str(l["line_total"])) for l in lines) if lines else 0.0
        cur.execute("""
            UPDATE sale
            SET total_amount = %s
            WHERE sale_id = %s
        """, (total_amount, sale_id))

        conn.commit()
        flash("Sale completed successfully. Stock updated.", "success")
        return redirect(url_for("sales_list"))

    except Exception as e:
        conn.rollback()
        print("sale_complete error:", e)
        flash("Failed to complete sale.", "danger")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/sales")
@role_required("admin", "employee")
def sales_list():
    conn = get_connection()
    if not conn:
        return render_template("sales.html", sales=[], branches=[], error="Unable to connect to database")

    try:
        cur = conn.cursor(dictionary=True)

        # Filters
        branch_id = request.args.get("branch_id", type=int)
        date_from = (request.args.get("date_from") or "").strip()   # "YYYY-MM-DD"
        date_to = (request.args.get("date_to") or "").strip()       # "YYYY-MM-DD"

        # Dropdown branches
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        # Build dynamic WHERE
        conditions = []
        params = []

        if branch_id:
            conditions.append("s.branch_id = %s")
            params.append(branch_id)

        if date_from:
            conditions.append("DATE(s.sale_date) >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("DATE(s.sale_date) <= %s")
            params.append(date_to)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Main query
        cur.execute(f"""
            SELECT
                s.sale_id,
                s.sale_date,
                b.branch_name,
                e.full_name AS employee_name,
                cu.full_name AS customer_name,
                s.total_amount
            FROM sale s
            JOIN branch b ON s.branch_id = b.branch_id
            JOIN users e ON s.employee_id = e.user_id
            LEFT JOIN users cu ON s.customer_id = cu.user_id
            {where_clause}
            ORDER BY s.sale_date DESC
        """, params)

        sales = cur.fetchall()

        return render_template(
            "sales.html",
            sales=sales,
            branches=branches,
            selected_branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            error=None
        )

    finally:
        cur.close()
        conn.close()

@app.route("/sales/<int:sale_id>/remove-line", methods=["POST"])
@role_required("admin", "employee")
def sale_remove_line(sale_id):
    sale_line_id = request.form.get("sale_line_id", type=int)

    if not sale_line_id:
        flash("Invalid line item.", "warning")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for("sale_detail", sale_id=sale_id))

    try:
        cur = conn.cursor()

        # Make sure the line belongs to this sale (prevents deleting other sales lines)
        cur.execute("""
            DELETE FROM sale_line
            WHERE sale_line_id = %s AND sale_id = %s
        """, (sale_line_id, sale_id))

        conn.commit()

        if cur.rowcount == 0:
            flash("Line not found (or already removed).", "warning")
        else:
            flash("Item removed from sale.", "success")

    except Exception as e:
        conn.rollback()
        print("sale_remove_line error:", e)
        flash("Failed to remove item.", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("sale_detail", sale_id=sale_id))


@app.context_processor
def inject_dashboard_metrics():
    data = {"nav_low_stock_count": None, "today_sales": None}

    if 'user_id' in session and session.get('role') in ('admin', 'employee'):
        data["nav_low_stock_count"] = get_low_stock_count()
        data["today_sales"] = get_today_sales_summary()

    return data

@app.route("/reports/top-products")
@role_required("admin", "employee")
def report_top_products():
    conn = get_connection()
    if not conn:
        return render_template("report_top_products.html",
                               rows=[],
                               branches=[],
                               error="Unable to connect to database")

    try:
        cur = conn.cursor(dictionary=True)

        # Filters
        branch_id = request.args.get("branch_id", type=int)
        date_from = (request.args.get("date_from") or "").strip()   # YYYY-MM-DD
        date_to = (request.args.get("date_to") or "").strip()       # YYYY-MM-DD

        metric = (request.args.get("metric") or "qty").strip().lower()   # qty | revenue
        metric = metric if metric in ("qty", "revenue") else "qty"

        top_n = request.args.get("top", default=10, type=int)
        if top_n not in (5, 10, 20, 50):
            top_n = 10

        # Branch dropdown
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        # Build WHERE
        conditions = []
        params = []

        if branch_id:
            conditions.append("s.branch_id = %s")
            params.append(branch_id)

        if date_from:
            conditions.append("DATE(s.sale_date) >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("DATE(s.sale_date) <= %s")
            params.append(date_to)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Order by chosen metric
        order_sql = "total_qty DESC" if metric == "qty" else "total_revenue DESC"

        query = f"""
            SELECT
                p.product_id,
                p.product_name,
                c.category_name,
                SUM(sl.quantity) AS total_qty,
                SUM(sl.line_total) AS total_revenue
            FROM sale_line sl
            JOIN sale s      ON sl.sale_id = s.sale_id
            JOIN product p   ON sl.product_id = p.product_id
            JOIN category c  ON p.category_id = c.category_id
            {where_clause}
            GROUP BY p.product_id, p.product_name, c.category_name
            ORDER BY {order_sql}
            LIMIT %s
        """

        cur.execute(query, params + [top_n])
        rows = cur.fetchall()

        return render_template(
            "report_top_products.html",
            rows=rows,
            branches=branches,
            selected_branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            top=top_n,
            error=None
        )

    except Exception as e:
        print("Top products report error:", e)
        return render_template("report_top_products.html",
                               rows=[],
                               branches=[],
                               error="Error loading report")
    finally:
        cur.close()
        conn.close()


@app.route("/reports/sales-analytics")
@role_required("admin", "employee")
def sales_analytics():
    conn = get_connection()
    if not conn:
        return render_template("sales_analytics.html",
                               branches=[], error="DB connection failed")

    try:
        cur = conn.cursor(dictionary=True)

        # Filters (GET params)
        branch_id = request.args.get("branch_id", type=int)
        date_from = (request.args.get("date_from") or "").strip()  # YYYY-MM-DD
        date_to = (request.args.get("date_to") or "").strip()      # YYYY-MM-DD
        group_by = (request.args.get("group_by") or "day").strip().lower()  # day|month
        group_by = group_by if group_by in ("day", "month") else "day"

        # Default date range if empty (last 30 days)
        # (This keeps the page useful the first time you open it.)
        if not date_to:
            cur.execute("SELECT CURDATE() AS d")
            date_to = str(cur.fetchone()["d"])
        if not date_from:
            cur.execute("SELECT DATE_SUB(%s, INTERVAL 30 DAY) AS d", (date_to,))
            date_from = str(cur.fetchone()["d"])

        # Branch dropdown
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        # WHERE builder
        conditions = ["DATE(s.sale_date) >= %s", "DATE(s.sale_date) <= %s"]
        params = [date_from, date_to]

        if branch_id:
            conditions.append("s.branch_id = %s")
            params.append(branch_id)

        where_clause = "WHERE " + " AND ".join(conditions)

        # 1) KPI summary
        cur.execute(f"""
            SELECT
                COUNT(*) AS sale_count,
                COALESCE(SUM(s.total_amount), 0) AS total_revenue,
                COALESCE(AVG(s.total_amount), 0) AS avg_sale
            FROM sale s
            {where_clause}
        """, params)
        summary = cur.fetchone()

        # 2) Trend (daily/monthly)
        if group_by == "month":
            label_sql = "DATE_FORMAT(s.sale_date, '%Y-%m')"
        else:
            label_sql = "DATE(s.sale_date)"

        cur.execute(f"""
            SELECT
                {label_sql} AS label,
                COALESCE(SUM(s.total_amount), 0) AS revenue
            FROM sale s
            {where_clause}
            GROUP BY label
            ORDER BY label ASC
        """, params)
        trend_rows = cur.fetchall()

        chart_labels = [str(r["label"]) for r in trend_rows]
        chart_values = [float(r["revenue"]) for r in trend_rows]

        # 3) Top categories
        cur.execute(f"""
            SELECT
                c.category_name,
                COALESCE(SUM(sl.quantity), 0) AS total_qty,
                COALESCE(SUM(sl.line_total), 0) AS total_revenue
            FROM sale_line sl
            JOIN sale s      ON sl.sale_id = s.sale_id
            JOIN product p   ON sl.product_id = p.product_id
            JOIN category c  ON p.category_id = c.category_id
            {where_clause}
            GROUP BY c.category_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """, params)
        top_categories = cur.fetchall()

        return render_template(
            "sales_analytics.html",
            branches=branches,
            selected_branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            group_by=group_by,
            summary=summary,
            chart_labels=chart_labels,
            chart_values=chart_values,
            top_categories=top_categories,
            error=None
        )

    except Exception as e:
        print("sales_analytics error:", e)
        return render_template("sales_analytics.html",
                               branches=[], error="Error loading analytics")

    finally:
        cur.close()
        conn.close()


#Purchase
@app.route("/purchases")
@role_required("admin", "employee")
def purchases_list():
    # later: list view
    return redirect(url_for("purchases_new"))

@app.route("/purchases/new", methods=["GET", "POST"])
@role_required("admin", "employee")
def purchases_new():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
    branches = cur.fetchall()

    if request.method == "POST":
        branch_id = request.form.get("branch_id", type=int)
        supplier_name = (request.form.get("supplier_name") or "").strip()
        employee_id = session.get("user_id")

        if not branch_id:
            flash("Select a branch.", "warning")
            return render_template("purchase_new.html", branches=branches)

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO purchase (branch_id, employee_id, supplier_name, total_amount)
            VALUES (%s, %s, %s, 0.00)
        """, (branch_id, employee_id, supplier_name))
        conn.commit()
        purchase_id = cur2.lastrowid
        cur2.close()

        return redirect(url_for("purchase_detail", purchase_id=purchase_id))

    return render_template("purchase_new.html", branches=branches)





@app.route("/stock-movements")
@role_required("admin", "employee")
def stock_movements():
    conn = get_connection()
    if not conn:
        return render_template(
            "stock_movements.html",
            rows=[],
            branches=[],
            products=[],
            selected_branch_id=None,
            selected_product_id=None,
            selected_type="",
            date_from="",
            date_to="",
            error="Unable to connect to database"
        )

    try:
        cur = conn.cursor(dictionary=True)

        # Filters
        branch_id = request.args.get("branch_id", type=int)
        product_id = request.args.get("product_id", type=int)
        mtype = (request.args.get("type") or "").strip().upper()  # RESTOCK / SALE / ""
        date_from = (request.args.get("date_from") or "").strip() # YYYY-MM-DD
        date_to = (request.args.get("date_to") or "").strip()     # YYYY-MM-DD

        # Dropdowns
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        cur.execute("SELECT product_id, product_name FROM product ORDER BY product_name")
        products = cur.fetchall()

        # Dynamic WHERE
        conditions = []
        params = []

        if branch_id:
            conditions.append("sm.branch_id = %s")
            params.append(branch_id)

        if product_id:
            conditions.append("sm.product_id = %s")
            params.append(product_id)

        if mtype in ("RESTOCK", "SALE"):
            conditions.append("sm.movement_type = %s")
            params.append(mtype)

        if date_from:
            conditions.append("DATE(sm.movement_date) >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("DATE(sm.movement_date) <= %s")
            params.append(date_to)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Main query
        query = f"""
            SELECT
                sm.movement_id,
                sm.movement_date,
                sm.movement_type,
                b.branch_name,
                p.product_name,
                sm.change_qty,
                sm.reference_sale_id,
                u.full_name AS performed_by_name
            FROM stock_movement sm
            JOIN branch b  ON sm.branch_id = b.branch_id
            JOIN product p ON sm.product_id = p.product_id
            JOIN users u   ON sm.performed_by = u.user_id
            {where_clause}
            ORDER BY sm.movement_date DESC
        """
        cur.execute(query, params)
        rows = cur.fetchall()

        return render_template(
            "stock_movements.html",
            rows=rows,
            branches=branches,
            products=products,
            selected_branch_id=branch_id,
            selected_product_id=product_id,
            selected_type=mtype,
            date_from=date_from,
            date_to=date_to,
            error=None
        )

    except Exception as e:
        print("stock_movements error:", e)
        return render_template(
            "stock_movements.html",
            rows=[],
            branches=[],
            products=[],
            selected_branch_id=None,
            selected_product_id=None,
            selected_type="",
            date_from="",
            date_to="",
            error="Error loading stock movements"
        )

    finally:
        cur.close()
        conn.close()





@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    GET: Display login form
    POST: Authenticate user credentials
    """
    # Redirect if already logged in
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Basic validation
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('login.html')
        
        # Retrieve user from database
        user = get_user_by_email(email)
        
        # Validate credentials
        if user is None:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Check if account is active
        if not user['is_active']:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return render_template('login.html')
        
        # Verify password
        if not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Successful login - create session
        session['user_id'] = user['user_id']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        
        flash(f'Welcome back, {user["full_name"]}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    """
    Handle user signup (registration).
    Only allows customer role registrations via web form.
    """
    # Redirect if already logged in
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # Extract form data
    full_name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    # Validation
    if not full_name or not email or not password or not confirm_password:
        flash('Please fill in all fields.', 'danger')
        return render_template('login.html')
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Please enter a valid email address.', 'danger')
        return render_template('login.html')
    
    # Validate password length
    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'danger')
        return render_template('login.html')
    
    # Check if passwords match
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('login.html')
    
    # Check if email already exists
    if email_exists(email):
        flash('An account with this email already exists. Please log in or use a different email.', 'danger')
        return render_template('login.html')
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Create user with customer role
    success = create_user(full_name, email, password_hash, role='customer')
    
    if success:
        flash('Account created successfully! Please log in with your credentials.', 'success')
        return render_template('login.html')
    else:
        flash('An error occurred while creating your account. Please try again.', 'danger')
        return render_template('login.html')

@app.route('/logout')
def logout():
    """
    Clear session and log out user.
    """
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """
    Role-based dashboard displaying content based on user role.
    """
    role = session.get('role')
    full_name = session.get('full_name')
    
    # Role-specific content
    content = {
        'admin': {
            'title': 'Admin Dashboard',
            'features': [
                'Manage all users',
                'View system analytics',
                'Configure application settings',
                'Access audit logs',
                'Manage employee and customer accounts'
            ],
            'color': 'danger'
        },
        'employee': {
            'title': 'Employee Dashboard',
            'features': [
                'View customer information',
                'Process orders and requests',
                'Update inventory',
                'Generate reports',
                'Access employee resources'
            ],
            'color': 'primary'
        },
        'customer': {
            'title': 'Customer Dashboard',
            'features': [
                'View your orders',
                'Update profile information',
                'Browse products',
                'Contact support',
                'View purchase history'
            ],
            'color': 'success'
        }
    }
    
    return render_template(
        'dashboard.html',
        full_name=full_name,
        role=role,
        content=content.get(role, content['customer'])
    )

# ==================== EXAMPLE PROTECTED ROUTES ====================

@app.route('/admin')
@role_required('admin')
def admin_panel():
    """
    Example admin-only route.
    """
    return '<h1>Admin Panel</h1><p>Only administrators can access this page.</p>'

@app.route('/employee/tools')
@role_required('admin', 'employee')
def employee_tools():
    """
    Example route accessible by both admin and employee.
    """
    return '<h1>Employee Tools</h1><p>Admins and employees can access this page.</p>'

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html', error='Internal server error'), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)