from binascii import Error
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
    """Display all products with category information"""
    conn = get_connection()
    
    if not conn:
        return render_template('products.html', 
                             products=[], 
                             error="Unable to connect to database")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                c.category_name,
                p.unit_price,
                p.description,
                p.is_active
            FROM product p
            INNER JOIN category c ON p.category_id = c.category_id
            ORDER BY p.product_name ASC
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        return render_template('products.html', products=products, error=None)
        
    except Error as e:
        print(f"Database query error: {e}")
        return render_template('products.html', 
                             products=[], 
                             error="Error retrieving products")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/products/active")
def active_products():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            c.category_name,
            p.unit_price,
            p.description,
            p.is_active
        FROM product p
        INNER JOIN category c ON p.category_id = c.category_id
        WHERE p.is_active = 1
        ORDER BY p.product_name ASC
    """)

    products = cur.fetchall()
    cur.close()
    conn.close()

    # We pass a custom title so the same template can display a different heading
    return render_template("products.html",
                           products=products,
                           error=None,
                           page_title="Active Products")




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