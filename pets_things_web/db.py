import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def get_connection():
    """
    Establish and return a MySQL database connection using environment variables.
    Returns None if connection fails.
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_user_by_email(email):
    """
    Retrieve user by email using parameterized query to prevent SQL injection.
    Returns user dict or None if not found.
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Parameterized query prevents SQL injection
        query = """
            SELECT user_id, full_name, email, password_hash, role, is_active 
            FROM users 
            WHERE email = %s
        """
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        return user
    except Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def create_user(full_name, email, password_hash, role='customer'):
    """
    Create a new user in the database.
    Returns True if successful, False otherwise.
    """
    print("create_user called:", full_name, email, role)

    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE() AS db")
        print("Flask connected to DB:", cursor.fetchone())

        query = """
            INSERT INTO users (full_name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, 1)
        """
        cursor.execute(query, (full_name, email, password_hash, role))
        conn.commit()
        return True
    except Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def email_exists(email):
    """
    Check if an email already exists in the database.
    Returns True if exists, False otherwise.
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        count = cursor.fetchone()[0]
        return count > 0
    except Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            
def get_today_sales_summary():
    conn = get_connection()
    if not conn:
        return {"count": 0, "total": 0.0}

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT
                COUNT(*) AS sale_count,
                COALESCE(SUM(total_amount), 0) AS total_amount
            FROM sale
            WHERE DATE(sale_date) = CURDATE()
        """)
        row = cur.fetchone()
        return {
            "count": row["sale_count"] or 0,
            "total": float(row["total_amount"] or 0)
        }
    except Exception as e:
        print("today sales summary error:", e)
        return {"count": 0, "total": 0.0}
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
