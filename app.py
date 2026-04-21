import sqlite3
import os
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for, flash
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import easyocr
import cv2
import numpy as np
import re

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = 'smart_parking_super_secret_key'
DATABASE = 'parking.db'

ADMIN_EMAILS = ['admin@smartparking.com', 'system@smartparking.com', 'guptaayush122006@gmail.com']

# Initialize AI Engine - Shared globally
print("--- MAIN APP: Initializing AI Scanning Core (EasyOCR)... ---")
ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)

def get_db() -> sqlite3.Connection:
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                phone TEXT,
                vehicle_number TEXT UNIQUE,
                is_blocked BOOLEAN DEFAULT 0,
                subscription_end DATETIME,
                wallet_balance REAL DEFAULT 0.0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT,
                price REAL,
                start_date DATETIME,
                end_date DATETIME,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                booking_id INTEGER,
                amount REAL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                transaction_date DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_occupied BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'available'
            )
        ''')
        
        # Initialize 50 slots (A1-A10, B1-B10... E1-E10)
        cursor.execute('SELECT COUNT(*) as count FROM parking_slots')
        if cursor.fetchone()['count'] == 0:
            slots = []
            for zone in ['A', 'B', 'C', 'D', 'E']:
                for i in range(1, 11):
                    slots.append((f"{zone}{i}",))
            cursor.executemany('INSERT INTO parking_slots (name) VALUES (?)', slots)

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                slot_id INTEGER,
                vehicle_type TEXT,
                book_type TEXT CHECK(book_type IN ('hourly', 'monthly')),
                status TEXT DEFAULT 'pending',
                start_time DATETIME,
                end_time DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(slot_id) REFERENCES parking_slots(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_number TEXT,
                vehicle_type TEXT,
                entry_time DATETIME,
                exit_time DATETIME,
                total_duration_minutes INTEGER,
                cost REAL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        db.commit()

# --- Auth Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def cleanup_expired_bookings():
    db = get_db()
    cursor = db.cursor()
    # Find active bookings for slots currently marked as 'booked'
    rows = cursor.execute('''
        SELECT b.id as booking_id, b.slot_id, b.start_time 
        FROM bookings b
        JOIN parking_slots s ON b.slot_id = s.id
        WHERE b.status = 'active' AND s.status = 'booked'
    ''').fetchall()
    
    expired_count = 0
    for r in rows:
        try:
            # Handle both microsecond and non-microsecond formats
            if '.' in r['start_time']:
                start = datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M:%S.%f')
            else:
                start = datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            continue
        
        diff = (datetime.now() - start).total_seconds()
        if diff >= 300: # 5 minutes threshold
            cursor.execute("UPDATE bookings SET status='expired' WHERE id=?", (r['booking_id'],))
            cursor.execute("UPDATE parking_slots SET is_occupied=0, status='available' WHERE id=?", (r['slot_id'],))
            expired_count += 1
            
    if expired_count > 0:
        db.commit()

# --- Frontend Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    cleanup_expired_bookings()
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    bookings = db.execute('SELECT b.*, s.name as slot_name FROM bookings b JOIN parking_slots s ON b.slot_id = s.id WHERE b.user_id = ? ORDER BY b.id DESC', (session['user_id'],)).fetchall()
    
    slots = db.execute('''
        SELECT s.*, 
            (SELECT b.start_time FROM bookings b WHERE b.slot_id = s.id AND b.status = 'active' AND s.status = 'booked' ORDER BY b.id DESC LIMIT 1) as start_time_str
        FROM parking_slots s ORDER BY id
    ''').fetchall()
    
    total_slots = len(slots)
    available_slots = sum(1 for s in slots if not s['is_occupied'])
    
    subscription = db.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' ORDER BY end_date DESC LIMIT 1", (session['user_id'],)).fetchone()
    
    return render_template('user_dashboard.html', user=user, bookings=bookings, slots=slots, total_slots=total_slots, available_slots=available_slots, subscription=subscription)

@app.route('/wallet')
@login_required
def wallet_dashboard():
    db = get_db()
    user = db.execute('SELECT id, wallet_balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    transactions = db.execute('SELECT * FROM payments WHERE user_id = ? ORDER BY transaction_date DESC LIMIT 10', (session['user_id'],)).fetchall()
    
    # Merge subscription tracking info into wallet
    subscription = db.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' ORDER BY end_date DESC LIMIT 1", (session['user_id'],)).fetchone()
    
    return render_template('wallet.html', user=user, transactions=transactions, subscription=subscription)

@app.route('/profile')
@login_required
def profile_dashboard():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user)

@app.route('/api/add_funds', methods=['POST'])
@login_required
def add_funds():
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, session['user_id']))
        # Log transaction
        cursor.execute("INSERT INTO payments (user_id, amount, payment_method, status, transaction_date) VALUES (?, ?, 'wallet_load', 'completed', ?)", (session['user_id'], amount, datetime.now()))
        db.commit()
    return redirect(url_for('wallet_dashboard', msg=f"Added ₹{amount} to wallet successfully."))

@app.route('/subscription')
@login_required
def subscription_dashboard():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    subscription = db.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' ORDER BY end_date DESC LIMIT 1", (session['user_id'],)).fetchone()
    return render_template('subscription.html', user=user, subscription=subscription)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    
    # Calculate total revenue
    rev_row = db.execute("SELECT SUM(cost) as total FROM parking_sessions WHERE status = 'completed'").fetchone()
    total_revenue = rev_row['total'] if rev_row['total'] else 0.0
    
    # Analytics metrics
    users_row = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
    total_users = users_row['count']
    
    bookings_row = db.execute("SELECT COUNT(*) as count FROM bookings").fetchone()
    total_bookings = bookings_row['count']
    
    # Get currently active vehicles inside
    active_sessions = db.execute("SELECT * FROM parking_sessions WHERE status = 'active' ORDER BY entry_time DESC").fetchall()
    
    # Retrieve all static slots for Jinja SSR
    slots = db.execute('SELECT * FROM parking_slots ORDER BY id').fetchall()
    
    # ---- NEW ANALYTICS & DIRECTORY LOGIC ----
    # 1. Overall Revenue Trend
    daily_revenue_raw = db.execute('''
        SELECT transaction_date, amount
        FROM payments
        WHERE status = 'completed'
    ''').fetchall()
    
    from collections import defaultdict
    from datetime import datetime
    
    revenue_map = defaultdict(float)
    
    for row in daily_revenue_raw:
        try:
            # Safely extract YYYY-MM-DD piece from whatever timestamp string is returned
            dt_str = str(row['transaction_date']).split()[0]
            # Convert to UI format "DD MMM"
            ui_date = datetime.strptime(dt_str, '%Y-%m-%d').strftime('%d %b')
            revenue_map[ui_date] += row['amount']
        except Exception:
            pass
            
    # Sort dates dynamically based on actual chronological order
    def sort_key(d_str):
        try:
            return datetime.strptime(d_str, '%d %b')
        except:
            return datetime.min

    sorted_dates = sorted(revenue_map.keys(), key=sort_key)
    revenues = [revenue_map[d] for d in sorted_dates]

    if not sorted_dates:
        sorted_dates = [datetime.now().strftime('%d %b')]
        revenues = [0]

    chart_data = {
        'dates': sorted_dates,
        'revenues': revenues
    }

    # 1.1 Payment Method Distribution for Pie Chart
    payment_methods_raw = db.execute('''
        SELECT payment_method, COUNT(*) as count 
        FROM payments 
        WHERE status = 'completed'
        GROUP BY payment_method
    ''').fetchall()
    
    payment_stats = {row['payment_method']: row['count'] for row in payment_methods_raw}
    chart_data['payment_methods'] = list(payment_stats.keys())
    chart_data['method_counts'] = list(payment_stats.values())

    # 2. Complete User Directory (including Admins)
    users_list = db.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    
    # 3. Transaction History (Joined Payments)
    transaction_history = db.execute('''
        SELECT p.*, u.name as user_name, u.email as user_email 
        FROM payments p 
        LEFT JOIN users u ON p.user_id = u.id 
        ORDER BY p.transaction_date DESC 
        LIMIT 50
    ''').fetchall()
    
    # 4. Global Parking History (Past Sessions)
    parking_history = db.execute('''
        SELECT s.*, u.name as user_name 
        FROM parking_sessions s 
        LEFT JOIN users u ON s.vehicle_number = u.vehicle_number 
        ORDER BY s.entry_time DESC 
        LIMIT 50
    ''').fetchall()
    
    return render_template('admin_dashboard.html', slots=slots, total_revenue=total_revenue, 
                           active_sessions=active_sessions, total_users=total_users, 
                           total_bookings=total_bookings, chart_data=chart_data, 
                           users_list=users_list, transaction_history=transaction_history, 
                           parking_history=parking_history)

@app.route('/book')
@login_required
def book_page():
    return redirect(url_for('user_dashboard'))

@app.route('/receipt')
def receipt_page():
    return render_template('receipt.html')

@app.route('/gate_terminal')
@admin_required
def gate_terminal():
    db = get_db()
    # Get last 10 gate operations for the log
    gate_logs = db.execute('''
        SELECT s.*, u.name as user_name 
        FROM parking_sessions s 
        LEFT JOIN users u ON s.vehicle_number = u.vehicle_number 
        ORDER BY s.id DESC LIMIT 10
    ''').fetchall()
    return render_template('gate_terminal.html', logs=gate_logs)

# --- API Endpoints ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    role = 'admin' if email in ADMIN_EMAILS else 'user'
    hashed_password = generate_password_hash(password)
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', (name, email, hashed_password, role))
        db.commit()
        return redirect(url_for('login_page', msg="Registration successful! Please login."))
    except sqlite3.IntegrityError:
        return redirect(url_for('login_page', error="Email already exists!"))

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']
        
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    else:
        return redirect(url_for('login_page', error="Invalid email or password!"))

@app.route('/api/auth/forgot_password', methods=['POST'])
def forgot_password():
    data = request.form
    email = data.get('email', '').strip()
    name = data.get('name', '').strip()
    new_password = data.get('new_password', '').strip()
    
    db = get_db()
    cursor = db.cursor()
    
    user = cursor.execute('SELECT * FROM users WHERE email = ? COLLATE NOCASE AND name = ? COLLATE NOCASE', (email, name)).fetchone()
    
    if user:
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user['id']))
        db.commit()
        return redirect(url_for('login_page', msg="Password reset completely updated! You may now login."))
    else:
        return redirect(url_for('login_page', error="Verification failed. Identity mismatch."))

@app.route('/api/admin/force_free/<int:slot_id>', methods=['POST'])
@admin_required
def admin_force_free(slot_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE parking_slots SET is_occupied = 0, status = 'available' WHERE id = ?", (slot_id,))
    # Mark associated active bookings as completed forcefully
    cursor.execute("UPDATE bookings SET status = 'completed' WHERE slot_id = ? AND status = 'active'", (slot_id,))
    db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/toggle_block/<int:user_id>', methods=['POST'])
@admin_required
def toggle_block(user_id):
    db = get_db()
    cursor = db.cursor()
    user = cursor.execute('SELECT is_blocked FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 0 if user['is_blocked'] else 1
        cursor.execute('UPDATE users SET is_blocked = ? WHERE id = ?', (new_status, user_id))
        db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/add_funds/<int:user_id>', methods=['POST'])
@admin_required
def admin_add_funds(user_id):
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))
        # Log transaction as admin_credit
        cursor.execute("INSERT INTO payments (user_id, amount, payment_method, status, transaction_date) VALUES (?, ?, 'admin_credit', 'completed', ?)", (user_id, amount, datetime.now()))
        db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name')
    phone = request.form.get('phone')
    vehicle = request.form.get('vehicle_number')
    db = get_db()
    try:
        db.execute('UPDATE users SET name = ?, phone = ?, vehicle_number = ? WHERE id = ?', (name, phone, vehicle, session['user_id']))
        db.commit()
        session['user_name'] = name  # Update session name
        return redirect(url_for('profile_dashboard') + "?msg=Profile+Updated")
    except sqlite3.IntegrityError:
        return redirect(url_for('profile_dashboard') + "?error=Vehicle+Number+Already+Exists!")

@app.route('/api/update_password', methods=['POST'])
@login_required
def update_password():
    current_pass = request.form.get('current_password')
    new_pass = request.form.get('new_password')
    confirm_pass = request.form.get('confirm_password')

    if new_pass != confirm_pass:
        return redirect(url_for('profile_dashboard') + "?error=New+passwords+do+not+match!")
        
    db = get_db()
    user = db.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not check_password_hash(user['password'], current_pass):
        return redirect(url_for('profile_dashboard') + "?error=Current+password+is+incorrect!")
        
    hashed_password = generate_password_hash(new_pass)
    db.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, session['user_id']))
    db.commit()
    
    return redirect(url_for('profile_dashboard', msg="Password updated successfully!"))

@app.route('/api/slots', methods=['GET'])
def get_slots():
    cleanup_expired_bookings()
    db = get_db()
    slots = db.execute('''
        SELECT s.*, 
            (SELECT b.start_time FROM bookings b WHERE b.slot_id = s.id AND b.status = 'active' AND s.status = 'booked' ORDER BY b.id DESC LIMIT 1) as start_time_str
        FROM parking_slots s ORDER BY id
    ''').fetchall()
    return jsonify([dict(s) for s in slots])

@app.route('/api/bookings', methods=['POST'])
@login_required
def create_booking():
    db = get_db()
    data = request.form
    book_type = data.get('book_type', 'hourly')
    vehicle_type = data.get('vehicle_type', 'car')
    
    user_id = session['user_id']
    cursor = db.cursor()
    
    vehicle_number_input = data.get('vehicle_number')
    if not vehicle_number_input:
        return "Vehicle Number is required to book a slot.", 400
        
    try:
        cursor.execute('UPDATE users SET vehicle_number = ? WHERE id = ?', (vehicle_number_input, user_id))
    except sqlite3.IntegrityError:
        pass # Handle duplicate vehicle numbers silently for demo purposes
        
    user = cursor.execute('SELECT vehicle_number FROM users WHERE id = ?', (user_id,)).fetchone()
    
    existing = cursor.execute("SELECT id FROM bookings WHERE user_id = ? AND status = 'active'", (user_id,)).fetchone()
    if existing:
        return "You already have an active booking.", 400

    slot_id = data.get('slot_id')
    if not slot_id:
        return "Please select a specific parking slot.", 400

    slot = cursor.execute('SELECT id, is_occupied FROM parking_slots WHERE id = ?', (slot_id,)).fetchone()
    if not slot or slot['is_occupied']:
        return "The selected slot is no longer available.", 400
        
    cursor.execute('UPDATE parking_slots SET is_occupied = 1, status = \'booked\' WHERE id = ?', (slot['id'],))
    
    cursor.execute('INSERT INTO bookings (user_id, slot_id, vehicle_type, book_type, status, start_time) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, slot['id'], vehicle_type, book_type, 'active', datetime.now()))
                   
    if book_type == 'monthly':
        cursor.execute('INSERT INTO subscriptions (user_id, start_date) VALUES (?, ?)',
                       (user_id, datetime.now()))
                       
    db.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/api/buy_subscription', methods=['POST'])
@login_required
def buy_subscription():
    plan = request.form.get('plan')
    user_id = session['user_id']
    
    price = 1500.0 if plan == 'premium' else 999.0
    start_date = datetime.now()
    
    # Calculate exactly 1 month from now manually, taking care of month rollovers
    try:
        end_date = start_date.replace(month=start_date.month + 1)
    except ValueError:
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            # Handle edge cases like Jan 31 -> Feb 28
            import calendar
            next_month = start_date.month + 1
            last_day = calendar.monthrange(start_date.year, next_month)[1]
            end_date = start_date.replace(month=next_month, day=min(start_date.day, last_day))

    db = get_db()
    cursor = db.cursor()
    
    # End existing active subscriptions
    cursor.execute("UPDATE subscriptions SET status = 'expired' WHERE user_id = ? AND status = 'active'", (user_id,))
    
    # Create new subscription
    cursor.execute('INSERT INTO subscriptions (user_id, plan_name, price, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, plan, price, start_date, end_date, 'active'))
                   
    cursor.execute('UPDATE users SET subscription_end = ? WHERE id = ?', (end_date, user_id))
    db.commit()
    
    return redirect(url_for('user_dashboard', msg="Subscription successfully activated!"))

@app.route('/api/entry', methods=['POST'])
@admin_required
def process_entry():
    """Manual Entry from Dashboard."""
    data = request.json
    result, code = process_gate_logic(data.get('vehicle_number', ''))
    return jsonify(result), code

def process_gate_logic(vehicle_raw):
    """Core logic for Gate Entry and Exit. Returns (JSON, HTTP_CODE)."""
    cleanup_expired_bookings()
    vehicle = vehicle_raw.strip().upper()
    if not vehicle:
        return {'status': 'denied', 'message': 'No vehicle number detected'}, 400

    # Remove all formatting for comparison
    vehicle_clean = vehicle.replace(' ', '').replace('-', '').replace('.', '')
    db = get_db()
    cursor = db.cursor()

    # 1. Check if vehicle is already inside (Active Session) -> EXIT LOGIC
    active_session = cursor.execute("SELECT id, entry_time, vehicle_type FROM parking_sessions WHERE REPLACE(REPLACE(REPLACE(UPPER(vehicle_number), ' ', ''), '-', ''), '.', '') = ? AND status = 'active'", (vehicle_clean,)).fetchone()

    if active_session:
        user = cursor.execute("SELECT id, role, name, vehicle_number FROM users WHERE REPLACE(REPLACE(REPLACE(UPPER(vehicle_number), ' ', ''), '-', ''), '.', '') = ?", (vehicle_clean,)).fetchone()
        if not user:
            return {'status': 'denied', 'message': 'Unregistered vehicle exit detection'}, 400

        # Calculate cost based on vehicle type
        entry_time = datetime.strptime(active_session['entry_time'], '%Y-%m-%d %H:%M:%S.%f')
        duration = datetime.now() - entry_time
        hours = max(1, round(duration.total_seconds() / 3600, 2))
        
        # Standard rates
        v_type = active_session['vehicle_type']
        rate = {"motorcycle": 20.0, "car": 50.0, "truck": 100.0}.get(v_type, 50.0)
        cost = round(hours * rate, 2)

        # Check for active subscription (No cost if active)
        subscription = cursor.execute("SELECT id FROM subscriptions WHERE user_id = ? AND status = 'active'", (user['id'],)).fetchone()
        if subscription:
            cost = 0.0

        # Mark session as completed
        cursor.execute("UPDATE parking_sessions SET status = 'completed', exit_time = ?, cost = ? WHERE id = ?", (datetime.now(), cost, active_session['id']))
        
        # Free the slot associated with this vehicle's active booking
        cursor.execute("UPDATE parking_slots SET is_occupied = 0, status = 'available' WHERE id = (SELECT slot_id FROM bookings WHERE user_id = ? AND status = 'active' LIMIT 1)", (user['id'],))
        # Mark booking as completed
        cursor.execute("UPDATE bookings SET status = 'completed', end_time = ? WHERE user_id = ? AND status = 'active'", (datetime.now(), user['id']))
        
        db.commit()
        return {
            'status': 'allowed',
            'mode': 'EXIT',
            'vehicle_number': user['vehicle_number'],
            'message': f'Exit Granted. Goodbye {user["name"]}! Fee: ₹{cost}'
        }, 200

    # 2. ENTRY LOGIC
    user = cursor.execute("SELECT id, name, vehicle_number FROM users WHERE REPLACE(REPLACE(REPLACE(UPPER(vehicle_number), ' ', ''), '-', ''), '.', '') = ?", (vehicle_clean,)).fetchone()
    if not user:
        return {'status': 'denied', 'message': 'Vehicle not registered. Please sign up first!'}, 404

    # Check for active booking or subscription
    booking = cursor.execute("SELECT id, slot_id, vehicle_type FROM bookings WHERE user_id = ? AND status = 'active'", (user['id'],)).fetchone()
    subscription = cursor.execute("SELECT id FROM subscriptions WHERE user_id = ? AND status = 'active'", (user['id'],)).fetchone()

    if not booking and not subscription:
        return {'status': 'denied', 'message': 'No active booking/subscription found. Please book a slot!'}, 403

    v_type = booking['vehicle_type'] if booking else 'car'
    
    # Open Gate / Log Entry
    cursor.execute('INSERT INTO parking_sessions (vehicle_number, vehicle_type, entry_time, status) VALUES (?, ?, ?, "active")', (user['vehicle_number'], v_type, datetime.now()))
    
    # Update slot status to occupied if entry via booking
    if booking:
        cursor.execute("UPDATE parking_slots SET status = 'occupied', is_occupied = 1 WHERE id = ?", (booking['slot_id'],))

    db.commit()
    return {
        'status': 'allowed',
        'mode': 'ENTRY',
        'vehicle_number': user['vehicle_number'],
        'message': f'Welcome, {user["name"]}! Gate Opened.'
    }, 200

@app.route('/api/gate/verify', methods=['POST'])
@admin_required
def gate_verify():
    data = request.json
    result, code = process_gate_logic(data.get('vehicle_number', ''))
    return jsonify(result), code

@app.route('/api/gate/scan_ocr', methods=['POST'])
@admin_required
def api_gate_scan_ocr():
    """Main AI Scanning endpoint for Dashboard and Terminals."""
    data = request.json.get('image')
    if not data:
        return jsonify({'status': 'denied', 'message': 'No image received'}), 400

    try:
        header, encoded = data.split(",", 1)
        image_data = base64.b64decode(encoded)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        results = ocr_reader.readtext(img, detail=0)
        plate = ""
        for text in results:
            clean = re.sub(r'[^A-Z0-9]', '', text.upper())
            if len(clean) >= 4:
                plate = clean
                break
        
        if not plate:
            return jsonify({'status': 'denied', 'message': 'AI could not read any text. Hold steady!'})

        result, code = process_gate_logic(plate)
        result['vehicle_number'] = plate # Show what we detected
        return jsonify(result), code

    except Exception as e:
        return jsonify({'status': 'denied', 'message': f'AI Error: {str(e)}'}), 500

@app.route('/api/exit', methods=['POST'])
@admin_required
def process_exit():
    """Manual Exit from Dashboard."""
    data = request.json
    result, code = process_gate_logic(data.get('vehicle_number', ''))
    return jsonify(result), code

@app.route('/api/user_checkout/<int:booking_id>', methods=['POST'])
@login_required
def user_checkout(booking_id):
    db = get_db()
    cursor = db.cursor()
    
    user_id = session['user_id']
    
    # Verify booking belongs to user
    booking = cursor.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ? AND status = 'active'", (booking_id, user_id)).fetchone()
    if not booking:
        return jsonify({'error': 'Active booking not found.'}), 404
        
    # Free the slot and close booking
    cursor.execute("UPDATE parking_slots SET is_occupied = 0, status = 'available' WHERE id = ?", (booking['slot_id'],))
    cursor.execute("UPDATE bookings SET status = 'completed', end_time = ? WHERE id = ?", (datetime.now(), booking_id))
    
    # Check if there's an active session built by admin gate
    user = cursor.execute("SELECT vehicle_number FROM users WHERE id = ?", (user_id,)).fetchone()
    session_rec = cursor.execute("SELECT id, entry_time, vehicle_type FROM parking_sessions WHERE vehicle_number = ? AND status = 'active'", (user['vehicle_number'],)).fetchone()
    
    # If they never entered the gate, just cancel nicely.
    if not session_rec:
        db.commit()
        return redirect(url_for('user_dashboard', msg="Booking Cancelled. Billing starts only AFTER gate entry!"))

    # Simulate exit cost logic securely
    entry_time = datetime.strptime(session_rec['entry_time'], '%Y-%m-%d %H:%M:%S.%f')
    exit_time = datetime.now()
    duration_mins = int((exit_time - entry_time).total_seconds() / 60)
    if duration_mins == 0: duration_mins = 60
    
    subscription = cursor.execute("SELECT id FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,)).fetchone()
    cost = 0.0
    if not subscription:
        hours = max(1.0, duration_mins / 60)
        v_type = session_rec['vehicle_type']
        rate = {"motorcycle": 20.0, "car": 50.0, "truck": 100.0}.get(v_type, 50.0)
        cost = hours * rate
        
    cursor.execute("UPDATE parking_sessions SET exit_time = ?, total_duration_minutes = ?, cost = ?, status = 'completed' WHERE id = ?",
                   (exit_time, duration_mins, cost, session_rec['id']))
    db.commit()
    # Redirect to the dynamic payment gateway funnel
    return redirect(url_for('payment_page', session_id=session_rec['id']))

@app.route('/api/receipt/<int:session_id>', methods=['GET'])
def get_receipt(session_id):
    db = get_db()
    session_rec = db.execute("SELECT * FROM parking_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session_rec:
        return jsonify({'error': 'Receipt not found'}), 404
        
    # The QR code now directly points to the checkout payment page URL
    payment_url = url_for('payment_page', session_id=session_id, _external=True)
    qr = qrcode.make(payment_url)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Fetch associated payment if any
    payment = db.execute("SELECT payment_method, amount FROM payments WHERE booking_id = ? ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
    payment_method = payment['payment_method'] if payment else 'N/A'
    paid_amount = payment['amount'] if payment else session_rec['cost']
    
    # Fetch user wallet balance
    user = db.execute("SELECT wallet_balance FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    return jsonify({
        'vehicle_number': session_rec['vehicle_number'],
        'entry_time': session_rec['entry_time'],
        'exit_time': session_rec['exit_time'] or 'Active',
        'duration': session_rec['total_duration_minutes'],
        'cost': paid_amount,
        'payment_method': payment_method,
        'wallet_balance': user['wallet_balance'] if user else 0.0,
        'qr_code': qr_base64,
        'payment_url': payment_url
    })

# --- Payment Gateway Routes ---
@app.route('/pay/<int:session_id>')
@login_required
def payment_page(session_id):
    db = get_db()
    session_rec = db.execute("SELECT * FROM parking_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session_rec:
        return "Session not found", 404
        
    # Generate UPI QR code explicitly for the requested ID
    upi_str = f"upi://pay?pa=pay@smartparking.com&pn=SmartParking&am={session_rec['cost']}&cu=INR"
    qr = qrcode.make(upi_str)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
    return render_template('pay.html', session_rec=session_rec, qr_base64=qr_base64)

@app.route('/api/process_payment', methods=['POST'])
@login_required
def process_payment():
    data = request.form
    session_id = data.get('session_id')
    amount = float(data.get('amount', 0))
    method = data.get('payment_method')
    user_id = session['user_id']
    
    db = get_db()
    cursor = db.cursor()
    
    session_rec = cursor.execute("SELECT * FROM parking_sessions WHERE id = ?", (session_id,)).fetchone()
    
    if session_rec['status'] == 'active':
        return "Cannot pay for an active session. Please exit the gate first.", 400

    # Ensure wallet has enough funds if selected
    if method == 'wallet':
        user = cursor.execute("SELECT wallet_balance FROM users WHERE id = ?", (user_id,)).fetchone()
        if user['wallet_balance'] < amount:
            return redirect(url_for('payment_page', session_id=session_id, error="Insufficient Wallet Balance. Please use UPI or add funds."))
        # Deduct from wallet securely
        cursor.execute("UPDATE users SET wallet_balance = wallet_balance - ? WHERE id = ?", (amount, user_id))

    # Insert successful payment record
    cursor.execute('''INSERT INTO payments (user_id, booking_id, amount, payment_method, status, transaction_date) 
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (user_id, session_id, amount, method, 'completed', datetime.now()))
                   
    # Clear the related booking completely now that they have paid and left
    b_slot = cursor.execute("SELECT slot_id, id FROM bookings WHERE user_id = ? AND status = 'completed'", (user_id,)).fetchone()
    if b_slot:
        # Actually archive the booking or map its payment, for now we just log it in payments linked to session
        pass

    db.commit()
    
    return redirect(url_for('user_dashboard', msg="Checkout successful! Exit gate opened securely."))

@app.route('/api/generate_qr')
@login_required
def generate_qr():
    amount = request.args.get('amount', '0')
    upi_str = f"upi://pay?pa=pay@smartparking.com&pn=SmartParking&am={amount}&cu=INR"
    qr = qrcode.make(upi_str)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return jsonify({'qr': qr_base64})

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True, port=5000)
