# Smart Parking System

A comprehensive Smart Parking System implemented with Python and Flask. This project allows users to seamlessly book parking slots, manage their profiles and wallets, buy subscriptions, and check out securely. It also provides an admin dashboard to visualize analytics, manage users, and operate the parking gate terminal.

## Features

- **User Dashboard:** Book slots (hourly or monthly), manage profiles, and review booking history.
- **Wallet System:** Add funds to your digital wallet and use them for seamless checkout.
- **Subscriptions:** Purchase premium or standard monthly plans for uninterrupted parking access.
- **Admin Dashboard:** Access analytics such as total revenue, daily revenue trends, currently active sessions, and global history.
- **Gate Terminal Module:** API for verifying vehicle authorization upon entry/exit based on live bookings and subscriptions.
- **Payment & Receipts:** Interactive QR code generation for payments and detailed digital receipts.

## Technologies Used
- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML/CSS, Jinja2 Templates, JavaScript
- **Libraries**: `qrcode`, `werkzeug`

## Getting Started

1. Clone this repository.
2. Setup a virtual environment: `python -m venv .venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run the application: `python app.py`.
5. Access the application at `http://127.0.0.1:5000`.

## Credentials
Admins are based on email. To login as admin, register with predefined admin emails:
- `guptaayush122006@gmail.com`
- `jagratisinghal9@gmail.com`

Any other email will be registered as a regular user.
