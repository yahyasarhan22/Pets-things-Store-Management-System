from werkzeug.security import generate_password_hash
from db import get_connection

EMAIL = "Employee2@pets.com"   # exactly like your table
NEW_PASSWORD = "1234"

hashed = generate_password_hash(NEW_PASSWORD)

conn = get_connection()
cur = conn.cursor()

cur.execute(
    "UPDATE users SET password_hash=%s WHERE email=%s",
    (hashed, EMAIL)
)

conn.commit()
cur.close()
conn.close()

print("✅ Updated password hash for:", EMAIL)
print("Password is:", NEW_PASSWORD)
