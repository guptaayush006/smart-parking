import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE = 'parking.db'
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Clear dynamic tables
cursor.execute("DELETE FROM parking_sessions")
cursor.execute("DELETE FROM bookings")
cursor.execute("DELETE FROM subscriptions")
cursor.execute("DELETE FROM payments")
cursor.execute("DELETE FROM users")
cursor.execute("UPDATE parking_slots SET is_occupied = 0, status = 'available'")

# Re-create the admin user for gate_app
hash_pw = generate_password_hash('admin')
cursor.execute("INSERT INTO users (name, email, password, role) VALUES ('Ayush Admin', 'guptaayush122006@gmail.com', ?, 'admin')", (hash_pw,))
conn.commit()
conn.close()
print("DB cleared and admin re-created.")
