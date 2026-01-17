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

        # Get categories for dropdown
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
                                       mode="add",
                                       categories=categories,
                                       product=None)

            try:
                # Start transaction
                cur.execute("""
                    INSERT INTO product (product_name, category_id, unit_price, description, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, category_id, unit_price, description, is_active))
                
                product_id = cur.lastrowid
                
                # Create warehouse stock rows for all warehouses
                cur.execute("""
                    INSERT INTO warehouse_stock (warehouse_id, product_id, on_hand_qty, min_qty, last_purchase_date)
                    SELECT warehouse_id, %s, 0, 10, NULL
                    FROM warehouse
                """, (product_id,))
                
                warehouse_rows = cur.rowcount
                
                # Create branch stock rows for all branches
                cur.execute("""
                    INSERT INTO branch_stock (branch_id, product_id, on_hand_qty, min_qty, last_restock_date)
                    SELECT branch_id, %s, 0, 5, NULL
                    FROM branch
                """, (product_id,))
                
                branch_rows = cur.rowcount
                
                conn.commit()
                
                flash(f"Product added with stock initialized in {warehouse_rows} warehouse(s) and {branch_rows} branch(es).", "success")
                return redirect(url_for("products"))
                
            except Exception as e:
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
    """
    Unified inventory page supporting both warehouse and branch views.
    Query param 'view' determines which: view=warehouse or view=branch (default)
    """
    conn = get_connection()
    if not conn:
        return render_template(
            'inventory.html',
            inventory=[],
            branches=[],
            warehouses=[],
            categories=[],
            view='branch',
            error="Unable to connect to database"
        )

    try:
        cur = conn.cursor(dictionary=True)

        # Determine view type
        view = (request.args.get('view') or 'branch').strip().lower()
        if view not in ('branch', 'warehouse'):
            view = 'branch'

        # Filters
        location_id = request.args.get('location_id', type=int)  # branch_id or warehouse_id
        category_id = request.args.get('category_id', type=int)
        status = (request.args.get('status') or "").strip().upper()

        # Sorting + pagination
        sort = (request.args.get('sort') or "product_name").strip()
        direction = (request.args.get('dir') or "asc").strip().lower()
        direction = "desc" if direction == "desc" else "asc"

        page = request.args.get('page', default=1, type=int)
        if page < 1:
            page = 1
        per_page = 15
        offset = (page - 1) * per_page

        # Get locations for dropdown
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()
        
        cur.execute("SELECT warehouse_id, warehouse_name FROM warehouse ORDER BY warehouse_name")
        warehouses = cur.fetchall()

        cur.execute("SELECT category_id, category_name FROM category ORDER BY category_name")
        categories = cur.fetchall()

        # Build query based on view
        conditions = []
        params = []

        if view == 'branch':
            base_from = """
                FROM branch_stock s
                JOIN product p ON s.product_id = p.product_id
                JOIN category c ON p.category_id = c.category_id
                JOIN branch b ON s.branch_id = b.branch_id
            """
            
            if location_id:
                conditions.append("s.branch_id = %s")
                params.append(location_id)
                
            location_name_col = "b.branch_name"
            last_date_col = "s.last_restock_date"
            
        else:  # warehouse
            base_from = """
                FROM warehouse_stock s
                JOIN product p ON s.product_id = p.product_id
                JOIN category c ON p.category_id = c.category_id
                JOIN warehouse w ON s.warehouse_id = w.warehouse_id
            """
            
            if location_id:
                conditions.append("s.warehouse_id = %s")
                params.append(location_id)
                
            location_name_col = "w.warehouse_name"
            last_date_col = "s.last_purchase_date"

        # Category filter
        if category_id:
            conditions.append("p.category_id = %s")
            params.append(category_id)

        # Status filter
        if status == "LOW":
            conditions.append("s.on_hand_qty <= s.min_qty")
        elif status == "OK":
            conditions.append("s.on_hand_qty > s.min_qty")

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # Sorting whitelist
        sort_map = {
            "location_name": location_name_col,
            "product_name": "p.product_name",
            "category_name": "c.category_name",
            "on_hand_qty": "s.on_hand_qty",
            "min_qty": "s.min_qty",
            "last_date": last_date_col,
            "status": "stock_status"
        }
        sort_sql = sort_map.get(sort, "p.product_name")

        # Count total records
        count_query = f"SELECT COUNT(*) AS total {base_from} {where_clause}"
        cur.execute(count_query, params)
        total_records = cur.fetchone()["total"]
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        if page > total_pages:
            page = total_pages
            offset = (page - 1) * per_page

        # Main SELECT
        if view == 'branch':
            location_id_col = "s.branch_id"
        else:
            location_id_col = "s.warehouse_id"

        main_query = f"""
            SELECT
                {location_id_col} AS location_id,
                s.product_id,
                {location_name_col} AS location_name,
                p.product_name,
                c.category_name,
                s.on_hand_qty,
                s.min_qty,
                {last_date_col} AS last_date,
                CASE
                    WHEN s.on_hand_qty <= s.min_qty THEN 'LOW'
                    ELSE 'OK'
                END AS stock_status
            {base_from}
            {where_clause}
            ORDER BY {sort_sql} {direction}
            LIMIT %s OFFSET %s
        """
        cur.execute(main_query, params + [per_page, offset])
        rows = cur.fetchall()

        # Summary
        summary_query = f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN s.on_hand_qty <= s.min_qty THEN 1 ELSE 0 END) AS low_count,
                SUM(CASE WHEN s.on_hand_qty > s.min_qty THEN 1 ELSE 0 END) AS ok_count,
                SUM(CASE WHEN s.on_hand_qty = 0 THEN 1 ELSE 0 END) AS out_of_stock,
                COUNT(DISTINCT s.product_id) AS unique_products
            {base_from}
            {where_clause}
        """
        cur.execute(summary_query, params)
        summary = cur.fetchone() or {}
        
        for k in ["low_count", "ok_count", "out_of_stock"]:
            summary[k] = summary.get(k) or 0

        return render_template(
            'inventory.html',
            inventory=rows,
            branches=branches,
            warehouses=warehouses,
            categories=categories,
            view=view,
            selected_location_id=location_id,
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
            warehouses=[],
            categories=[],
            view='branch',
            error="Error loading inventory"
        )
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()

# =========================================================
# NEW: STOCK TRANSFER ROUTE (warehouse → branch)
# =========================================================

@app.route('/inventory/transfer', methods=['POST'])
@role_required('admin', 'employee')
def transfer_stock():
    """
    Transfer stock from warehouse to branch.
    Replaces the old 'restock' functionality.
    """
    warehouse_id = request.form.get('warehouse_id', type=int)
    branch_id = request.form.get('branch_id', type=int)
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)

    if not all([warehouse_id, branch_id, product_id, quantity]) or quantity < 1:
        flash("Invalid transfer request.", "danger")
        return redirect(url_for('inventory'))

    conn = get_connection()
    if not conn:
        flash("DB connection failed.", "danger")
        return redirect(url_for('inventory'))

    try:
        performed_by = session.get("user_id")
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # 1) Check warehouse stock
        cur.execute("""
            SELECT on_hand_qty 
            FROM warehouse_stock 
            WHERE warehouse_id = %s AND product_id = %s
            FOR UPDATE
        """, (warehouse_id, product_id))
        
        warehouse_stock = cur.fetchone()
        if not warehouse_stock:
            conn.rollback()
            flash("Product not found in warehouse.", "danger")
            return redirect(url_for('inventory'))
            
        if warehouse_stock['on_hand_qty'] < quantity:
            conn.rollback()
            flash(f"Insufficient warehouse stock. Available: {warehouse_stock['on_hand_qty']}", "warning")
            return redirect(url_for('inventory'))

        # 2) Decrease warehouse stock
        cur.execute("""
            UPDATE warehouse_stock
            SET on_hand_qty = on_hand_qty - %s
            WHERE warehouse_id = %s AND product_id = %s
        """, (quantity, warehouse_id, product_id))

        # 3) Increase branch stock
        cur.execute("""
            UPDATE branch_stock
            SET on_hand_qty = on_hand_qty + %s,
                last_restock_date = NOW()
            WHERE branch_id = %s AND product_id = %s
        """, (quantity, branch_id, product_id))

        # 4) Log transfer
        cur.execute("""
            INSERT INTO stock_transfer
                (warehouse_id, branch_id, product_id, quantity, performed_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (warehouse_id, branch_id, product_id, quantity, performed_by))
        
        transfer_id = cur.lastrowid

        # 5) Log movements
        # Warehouse: TRANSFER_OUT (negative)
        cur.execute("""
            INSERT INTO stock_movement
                (warehouse_id, product_id, change_qty, movement_type, 
                 reference_transfer_id, performed_by)
            VALUES (%s, %s, %s, 'TRANSFER_OUT', %s, %s)
        """, (warehouse_id, product_id, -quantity, transfer_id, performed_by))

        # Branch: TRANSFER_IN (positive)
        cur.execute("""
            INSERT INTO stock_movement
                (branch_id, product_id, change_qty, movement_type,
                 reference_transfer_id, performed_by)
            VALUES (%s, %s, %s, 'TRANSFER_IN', %s, %s)
        """, (branch_id, product_id, quantity, transfer_id, performed_by))

        conn.commit()
        flash(f"Successfully transferred {quantity} units to branch.", "success")
        return redirect(request.referrer or url_for('inventory'))

    except Exception as e:
        conn.rollback()
        print(f"Transfer error: {e}")
        flash("Error during transfer.", "danger")
        return redirect(url_for('inventory'))
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()
            
            
# =========================================================
# NEW: PURCHASES ROUTE (supplier → warehouse)
# =========================================================

@app.route('/purchases/new', methods=['GET', 'POST'])
@role_required('admin', 'employee')
def purchase_new():
    """Create new purchase from supplier to warehouse."""
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for('dashboard'))

    try:
        cur = conn.cursor(dictionary=True)

        # Load warehouses and products
        cur.execute("SELECT warehouse_id, warehouse_name FROM warehouse ORDER BY warehouse_name")
        warehouses = cur.fetchall()

        cur.execute("SELECT product_id, product_name, unit_price FROM product WHERE is_active = 1 ORDER BY product_name")
        products = cur.fetchall()

        if request.method == 'POST':
            warehouse_id = request.form.get('warehouse_id', type=int)
            supplier_name = (request.form.get('supplier_name') or '').strip()

            if not warehouse_id or not supplier_name:
                flash("Please select warehouse and enter supplier name.", "warning")
                return render_template('purchase_form.html',
                                     warehouses=warehouses,
                                     products=products,
                                     selected_warehouse_id=warehouse_id,
                                     supplier_name=supplier_name)

            performed_by = session.get('user_id')

            # Create purchase header
            cur.execute("""
                INSERT INTO purchase (warehouse_id, supplier_name, total_amount, performed_by)
                VALUES (%s, %s, 0.00, %s)
            """, (warehouse_id, supplier_name, performed_by))
            
            purchase_id = cur.lastrowid
            conn.commit()

            flash("Purchase created. Add items now.", "success")
            return redirect(url_for('purchase_detail', purchase_id=purchase_id))

        return render_template('purchase_form.html',
                             warehouses=warehouses,
                             products=products,
                             selected_warehouse_id=None,
                             supplier_name='')

    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/purchases/<int:purchase_id>')
@role_required('admin', 'employee')
def purchase_detail(purchase_id):
    """View and manage purchase details."""
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for('dashboard'))

    try:
        cur = conn.cursor(dictionary=True)

        # Get purchase header
        cur.execute("""
            SELECT
                p.purchase_id,
                p.warehouse_id,
                w.warehouse_name,
                p.purchase_date,
                p.supplier_name,
                p.total_amount,
                p.performed_by,
                u.full_name AS performed_by_name
            FROM purchase p
            JOIN warehouse w ON p.warehouse_id = w.warehouse_id
            JOIN users u ON p.performed_by = u.user_id
            WHERE p.purchase_id = %s
        """, (purchase_id,))
        
        purchase = cur.fetchone()
        if not purchase:
            flash("Purchase not found.", "warning")
            return redirect(url_for('purchases_list'))

        # Get products for dropdown
        cur.execute("""
            SELECT product_id, product_name, unit_price
            FROM product
            WHERE is_active = 1
            ORDER BY product_name
        """)
        products = cur.fetchall()

        # Get purchase lines
        cur.execute("""
            SELECT
                pl.purchase_line_id,
                pl.product_id,
                p.product_name,
                pl.quantity,
                pl.unit_cost,
                pl.line_total
            FROM purchase_line pl
            JOIN product p ON pl.product_id = p.product_id
            WHERE pl.purchase_id = %s
            ORDER BY pl.purchase_line_id
        """, (purchase_id,))
        lines = cur.fetchall()

        total = sum(float(l["line_total"]) for l in lines) if lines else 0.0

        return render_template(
            'purchase_detail.html',
            purchase=purchase,
            products=products,
            lines=lines,
            computed_total=total,
            error=None
        )

    finally:
        cur.close()
        conn.close()


@app.route('/purchases/<int:purchase_id>/add-item', methods=['POST'])
@role_required('admin', 'employee')
def purchase_add_item(purchase_id):
    """Add item to purchase."""
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)
    unit_cost = request.form.get('unit_cost', type=float)

    if not product_id or not quantity or quantity <= 0 or not unit_cost or unit_cost < 0:
        flash("Invalid item details.", "warning")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))

    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))

    try:
        cur = conn.cursor(dictionary=True)

        # Check if item already exists
        cur.execute("""
            SELECT purchase_line_id, quantity, unit_cost
            FROM purchase_line
            WHERE purchase_id = %s AND product_id = %s
        """, (purchase_id, product_id))
        
        existing = cur.fetchone()

        if existing:
            # Update existing line
            new_qty = existing['quantity'] + quantity
            new_total = new_qty * unit_cost
            
            cur.execute("""
                UPDATE purchase_line
                SET quantity = %s, unit_cost = %s, line_total = %s
                WHERE purchase_line_id = %s
            """, (new_qty, unit_cost, new_total, existing['purchase_line_id']))
        else:
            # Insert new line
            line_total = quantity * unit_cost
            cur.execute("""
                INSERT INTO purchase_line (purchase_id, product_id, quantity, unit_cost, line_total)
                VALUES (%s, %s, %s, %s, %s)
            """, (purchase_id, product_id, quantity, unit_cost, line_total))

        conn.commit()
        flash("Item added to purchase.", "success")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))

    except Exception as e:
        conn.rollback()
        print("purchase_add_item error:", e)
        flash("Failed to add item.", "danger")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))
    finally:
        cur.close()
        conn.close()


@app.route('/purchases/<int:purchase_id>/complete', methods=['POST'])
@role_required('admin', 'employee')
def purchase_complete(purchase_id):
    """Complete purchase and update warehouse stock."""
    conn = get_connection()
    if not conn:
        flash("Database connection failed.", "danger")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))

    try:
        performed_by = session.get("user_id")
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Get purchase header
        cur.execute("SELECT warehouse_id FROM purchase WHERE purchase_id = %s", (purchase_id,))
        purchase = cur.fetchone()
        if not purchase:
            conn.rollback()
            flash("Purchase not found.", "warning")
            return redirect(url_for('purchases_list'))

        warehouse_id = purchase['warehouse_id']

        # Get purchase lines
        cur.execute("""
            SELECT product_id, quantity, line_total
            FROM purchase_line
            WHERE purchase_id = %s
        """, (purchase_id,))
        lines = cur.fetchall()

        if not lines:
            conn.rollback()
            flash("Add at least one item before completing.", "warning")
            return redirect(url_for('purchase_detail', purchase_id=purchase_id))

        # Update warehouse stock and log movements
        for line in lines:
            product_id = line['product_id']
            qty = line['quantity']

            # Increase warehouse stock
            cur.execute("""
                UPDATE warehouse_stock
                SET on_hand_qty = on_hand_qty + %s,
                    last_purchase_date = NOW()
                WHERE warehouse_id = %s AND product_id = %s
            """, (qty, warehouse_id, product_id))

            # Log movement
            cur.execute("""
                INSERT INTO stock_movement
                    (warehouse_id, product_id, change_qty, movement_type,
                     reference_purchase_id, performed_by)
                VALUES (%s, %s, %s, 'PURCHASE', %s, %s)
            """, (warehouse_id, product_id, qty, purchase_id, performed_by))

        # Update purchase total
        total_amount = sum(float(l['line_total']) for l in lines)
        cur.execute("""
            UPDATE purchase
            SET total_amount = %s
            WHERE purchase_id = %s
        """, (total_amount, purchase_id))

        conn.commit()
        flash("Purchase completed. Warehouse stock updated.", "success")
        return redirect(url_for('purchases_list'))

    except Exception as e:
        conn.rollback()
        print("purchase_complete error:", e)
        flash("Failed to complete purchase.", "danger")
        return redirect(url_for('purchase_detail', purchase_id=purchase_id))
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/purchases')
@role_required('admin', 'employee')
def purchases_list():
    """List all purchases."""
    conn = get_connection()
    if not conn:
        return render_template('purchases.html', purchases=[], warehouses=[], error="DB connection failed")

    try:
        cur = conn.cursor(dictionary=True)

        # Filters
        warehouse_id = request.args.get('warehouse_id', type=int)
        date_from = (request.args.get('date_from') or '').strip()
        date_to = (request.args.get('date_to') or '').strip()

        # Get warehouses for filter
        cur.execute("SELECT warehouse_id, warehouse_name FROM warehouse ORDER BY warehouse_name")
        warehouses = cur.fetchall()

        # Build query
        conditions = []
        params = []

        if warehouse_id:
            conditions.append("p.warehouse_id = %s")
            params.append(warehouse_id)

        if date_from:
            conditions.append("DATE(p.purchase_date) >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("DATE(p.purchase_date) <= %s")
            params.append(date_to)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        cur.execute(f"""
            SELECT
                p.purchase_id,
                p.purchase_date,
                w.warehouse_name,
                p.supplier_name,
                p.total_amount,
                u.full_name AS performed_by_name
            FROM purchase p
            JOIN warehouse w ON p.warehouse_id = w.warehouse_id
            JOIN users u ON p.performed_by = u.user_id
            {where_clause}
            ORDER BY p.purchase_date DESC
        """, params)

        purchases = cur.fetchall()

        return render_template(
            'purchases.html',
            purchases=purchases,
            warehouses=warehouses,
            selected_warehouse_id=warehouse_id,
            date_from=date_from,
            date_to=date_to,
            error=None
        )

    finally:
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
    Now uses branch_stock table.
    """
    if session.get("role") not in ("admin", "employee"):
        return {"low_stock_count": None}

    conn = get_connection()
    if not conn:
        return {"low_stock_count": None}

    try:
        cur = conn.cursor(dictionary=True)
        # Updated to use branch_stock
        cur.execute("SELECT COUNT(*) AS cnt FROM branch_stock WHERE on_hand_qty <= min_qty")
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
    Helper function to get low stock count from branch_stock.
    """
    conn = get_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor(dictionary=True)
        # Updated to use branch_stock
        cur.execute("SELECT COUNT(*) AS cnt FROM branch_stock WHERE on_hand_qty <= min_qty")
        result = cur.fetchone()
        return result["cnt"] if result else 0
    except Exception as e:
        print(f"get_low_stock_count error: {e}")
        return 0
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

    try:
        performed_by = session.get("user_id")
        cur = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Get sale header
        cur.execute("SELECT sale_id, branch_id FROM sale WHERE sale_id = %s", (sale_id,))
        sale = cur.fetchone()
        if not sale:
            conn.rollback()
            flash("Sale not found.", "warning")
            return redirect(url_for("sales_new"))

        branch_id = sale["branch_id"]

        # Get sale lines
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

        # Check branch stock and deduct
        for line in lines:
            pid = line["product_id"]
            qty = int(line["quantity"])

            # Lock branch stock
            cur.execute("""
                SELECT on_hand_qty
                FROM branch_stock
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
                UPDATE branch_stock
                SET on_hand_qty = on_hand_qty - %s
                WHERE branch_id = %s AND product_id = %s
            """, (qty, branch_id, pid))

            # Log movement
            cur.execute("""
                INSERT INTO stock_movement
                    (branch_id, product_id, change_qty, movement_type, reference_sale_id, performed_by)
                VALUES (%s, %s, %s, 'SALE', %s, %s)
            """, (branch_id, pid, -qty, sale_id, performed_by))

        # Update sale total
        total_amount = sum(float(str(l["line_total"])) for l in lines)
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




@app.route("/stock-movements")
@role_required("admin", "employee")
def stock_movements():
    conn = get_connection()
    if not conn:
        return render_template(
            "stock_movements.html",
            rows=[],
            branches=[],
            warehouses=[],
            products=[],
            error="Unable to connect to database"
        )

    try:
        cur = conn.cursor(dictionary=True)

        # Filters
        location_type = (request.args.get('location_type') or '').strip().lower()  # 'branch' or 'warehouse'
        location_id = request.args.get('location_id', type=int)
        product_id = request.args.get('product_id', type=int)
        mtype = (request.args.get('type') or '').strip().upper()
        date_from = (request.args.get('date_from') or '').strip()
        date_to = (request.args.get('date_to') or '').strip()

        # Dropdowns
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()

        cur.execute("SELECT warehouse_id, warehouse_name FROM warehouse ORDER BY warehouse_name")
        warehouses = cur.fetchall()

        cur.execute("SELECT product_id, product_name FROM product ORDER BY product_name")
        products = cur.fetchall()

        # Build WHERE
        conditions = []
        params = []

        if location_type == 'branch' and location_id:
            conditions.append("sm.branch_id = %s")
            params.append(location_id)
        elif location_type == 'warehouse' and location_id:
            conditions.append("sm.warehouse_id = %s")
            params.append(location_id)

        if product_id:
            conditions.append("sm.product_id = %s")
            params.append(product_id)

        if mtype in ('PURCHASE', 'SALE', 'TRANSFER_IN', 'TRANSFER_OUT'):
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

        # Query
        query = f"""
            SELECT
                sm.movement_id,
                sm.movement_date,
                sm.movement_type,
                COALESCE(b.branch_name, w.warehouse_name) AS location_name,
                p.product_name,
                sm.change_qty,
                sm.reference_sale_id,
                sm.reference_purchase_id,
                sm.reference_transfer_id,
                u.full_name AS performed_by_name
            FROM stock_movement sm
            LEFT JOIN branch b ON sm.branch_id = b.branch_id
            LEFT JOIN warehouse w ON sm.warehouse_id = w.warehouse_id
            JOIN product p ON sm.product_id = p.product_id
            JOIN users u ON sm.performed_by = u.user_id
            {where_clause}
            ORDER BY sm.movement_date DESC
            LIMIT 200
        """
        cur.execute(query, params)
        rows = cur.fetchall()

        return render_template(
            "stock_movements.html",
            rows=rows,
            branches=branches,
            warehouses=warehouses,
            products=products,
            selected_location_type=location_type,
            selected_location_id=location_id,
            selected_product_id=product_id,
            selected_type=mtype,
            date_from=date_from,
            date_to=date_to,
            error=None
        )

    except Exception as e:
        print("stock_movements error:", e)

# =========================================================
# OPTIONAL: Inventory transfer history
# =========================================================

@app.route('/transfers')
@role_required('admin', 'employee')
def transfers_list():
    """View all stock transfers."""
    conn = get_connection()
    if not conn:
        return render_template('transfers.html', transfers=[], error="DB connection failed")

    try:
        cur = conn.cursor(dictionary=True)
        
        # Filters
        warehouse_id = request.args.get('warehouse_id', type=int)
        branch_id = request.args.get('branch_id', type=int)
        date_from = (request.args.get('date_from') or '').strip()
        date_to = (request.args.get('date_to') or '').strip()
        
        # Build query
        conditions = []
        params = []
        
        if warehouse_id:
            conditions.append("t.warehouse_id = %s")
            params.append(warehouse_id)
        
        if branch_id:
            conditions.append("t.branch_id = %s")
            params.append(branch_id)
        
        if date_from:
            conditions.append("DATE(t.transfer_date) >= %s")
            params.append(date_from)
        
        if date_to:
            conditions.append("DATE(t.transfer_date) <= %s")
            params.append(date_to)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        cur.execute(f"""
            SELECT
                t.transfer_id,
                t.transfer_date,
                w.warehouse_name,
                b.branch_name,
                p.product_name,
                t.quantity,
                u.full_name AS performed_by_name,
                t.notes
            FROM stock_transfer t
            JOIN warehouse w ON t.warehouse_id = w.warehouse_id
            JOIN branch b ON t.branch_id = b.branch_id
            JOIN product p ON t.product_id = p.product_id
            JOIN users u ON t.performed_by = u.user_id
            {where_clause}
            ORDER BY t.transfer_date DESC
            LIMIT 200
        """, params)
        
        transfers = cur.fetchall()
        
        # Get dropdowns
        cur.execute("SELECT warehouse_id, warehouse_name FROM warehouse ORDER BY warehouse_name")
        warehouses = cur.fetchall()
        
        cur.execute("SELECT branch_id, branch_name FROM branch ORDER BY branch_name")
        branches = cur.fetchall()
        
        return render_template(
            'transfers.html',
            transfers=transfers,
            warehouses=warehouses,
            branches=branches,
            selected_warehouse_id=warehouse_id,
            selected_branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            error=None
        )
    finally:
        cur.close()
        conn.close()
# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def check_warehouse_stock(warehouse_id, product_id):
    """
    Check available stock in warehouse for a product.
    Returns the on_hand_qty or 0 if not found.
    """
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT on_hand_qty
            FROM warehouse_stock
            WHERE warehouse_id = %s AND product_id = %s
        """, (warehouse_id, product_id))
        
        result = cur.fetchone()
        return result['on_hand_qty'] if result else 0
    except Exception as e:
        print(f"check_warehouse_stock error: {e}")
        return 0
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


def check_branch_stock(branch_id, product_id):
    """
    Check available stock in branch for a product.
    Returns the on_hand_qty or 0 if not found.
    """
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT on_hand_qty
            FROM branch_stock
            WHERE branch_id = %s AND product_id = %s
        """, (branch_id, product_id))
        
        result = cur.fetchone()
        return result['on_hand_qty'] if result else 0
    except Exception as e:
        print(f"check_branch_stock error: {e}")
        return 0
    finally:
        if conn.is_connected():
            cur.close()
            conn.close()


def get_warehouse_summary():
    """
    Get summary statistics for warehouse inventory.
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT
                COUNT(DISTINCT ws.product_id) AS total_products,
                SUM(ws.on_hand_qty) AS total_stock,
                SUM(CASE WHEN ws.on_hand_qty <= ws.min_qty THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN ws.on_hand_qty = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
            FROM warehouse_stock ws
            JOIN product p ON ws.product_id = p.product_id
            WHERE p.is_active = 1
        """)
        
        return cur.fetchone()
    except Exception as e:
        print(f"get_warehouse_summary error: {e}")
        return None
    finally:
        if conn.is_connected():
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

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html', error='Internal server error'), 500

@app.route('/')
@login_required
def dashboard():
    """
    Enhanced dashboard with warehouse/branch metrics.
    """
    role = session.get('role')
    full_name = session.get('full_name')
    
    conn = get_connection()
    
    # Initialize metrics
    products_count = 0
    low_stock_count = 0
    today_sales = {"total_sales": 0, "total_revenue": 0}
    active_bookings = 0
    
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            
            # Products count
            cur.execute("SELECT COUNT(*) AS cnt FROM product WHERE is_active = 1")
            products_count = cur.fetchone()["cnt"]
            
            # Low stock (branch only - customer-facing)
            if role in ['admin', 'employee']:
                cur.execute("SELECT COUNT(*) AS cnt FROM branch_stock WHERE on_hand_qty <= min_qty")
                low_stock_count = cur.fetchone()["cnt"]
            
            # Today's sales
            if role in ['admin', 'employee']:
                cur.execute("""
                    SELECT 
                        COUNT(*) AS total_sales,
                        COALESCE(SUM(total_amount), 0) AS total_revenue
                    FROM sale
                    WHERE DATE(sale_date) = CURDATE()
                """)
                today_sales = cur.fetchone() or today_sales
            
            # Active bookings (if you have bookings)
            # cur.execute("SELECT COUNT(*) AS cnt FROM bookings WHERE status = 'active'")
            # active_bookings = cur.fetchone()["cnt"]
            
        except Exception as e:
            print(f"Dashboard metrics error: {e}")
        finally:
            cur.close()
            conn.close()
    
    # Role-specific content
    content = {
        'admin': {
            'title': 'Admin Dashboard',
            'features': [
                'Manage warehouse & branch inventory',
                'Process purchases from suppliers',
                'View system analytics',
                'Configure application settings',
                'Manage employee and customer accounts'
            ],
            'color': 'danger'
        },
        'employee': {
            'title': 'Employee Dashboard',
            'features': [
                'View branch inventory',
                'Transfer stock from warehouse',
                'Process customer sales',
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
        content=content.get(role, content['customer']),
        products_count=products_count,
        low_stock_count=low_stock_count,
        today_sales=today_sales,
        active_bookings=active_bookings
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)