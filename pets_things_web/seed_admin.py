from werkzeug.security import generate_password_hash
from db import get_connection

# Choose an admin password (change it later if you want)
ADMIN_EMAIL = "admin@pets.com"
ADMIN_PASSWORD = "1234"  # you can change this

password_hash = generate_password_hash(ADMIN_PASSWORD)

conn = get_connection()
cur = conn.cursor()

cur.execute(
    "UPDATE users SET password_hash=%s WHERE email=%s",
    (password_hash, ADMIN_EMAIL)
)

conn.commit()
cur.close()
conn.close()

print("✅ Admin password hash updated.")
print("Login email:", ADMIN_EMAIL)
print("Login password:", ADMIN_PASSWORD)
