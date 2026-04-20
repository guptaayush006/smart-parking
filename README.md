# 🚀 Smart Parking System – Next-Gen Access Control

![Smart Parking System](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-red)

A state-of-the-art **Smart Parking System** built with Python and Flask, featuring a fully automated gate terminal with Artificial Intelligence (ANPR), premium glassmorphism aesthetics, dynamic chart analytics, and seamless digital wallet integrations. 

## ✨ Key Features

### 📸 AI-Powered Gate Terminal (ANPR)
- **Automatic Number Plate Recognition:** Integrates `Tesseract.js` directly into the web browser for lightning-fast, client-side vehicle plate extraction.
- **Auto-Gate Control:** Instantly cross-checks plates with active database bookings to open the gate barrier, log entries, and flag unauthorized vehicles.
- **Dynamic Overlays:** Real-time feedback with green "Access Granted" and red "Access Denied" overlays right on the camera feed.

### 💎 Premium User Dashboard
- **Live Interactive Parking Map:** Visually select from 50 parking slots, dynamically color-coded (available, booked, physically inside, etc.).
- **Digital Wallet & Payments:** Load funds via dynamically generated UPI QR codes and use your balance for smooth 1-click checkouts.
- **VIP Subscriptions:** Upgrade to 'Standard' or 'Premium' memberships to enjoy automatic gate clearances, VIP zones, and heavily discounted long-term stays.

### 📊 Advanced Admin Analytics
- **Live Metrics & Graphs:** View daily revenue trends, wallet recharges, and booking distributions via interactive `Chart.js` visualizers.
- **User & Identity Management:** One-click options to block/unblock users or manually top-up their wallets.
- **Emergency Gate Control:** Force-free occupied slots or manually simulate gate API entries directly from the dashboard.

## 🛠️ Technology Stack
- **Backend Infrastructure:** Python, Flask, SQL (SQLite3)
- **Frontend Layer:** HTML5, modern CSS3 (Glassmorphism, custom CSS Variables), Vanilla JavaScript
- **AI & Data Vis:** Tesseract.js (Optical Character Recognition), Chart.js (Data Analytics)
- **Utilities:** `qrcode` (Secure Wallet API), Jinja2 Templating

## 🚀 Getting Started

### 1. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/guptaayush006/smart-parking.git
cd smart-parking
python -m venv .venv
# Activate virtual environment (.venv\Scripts\activate on Windows)
pip install -r requirements.txt
```

### 2. Run the Server
Launch the primary backend application.
```bash
python app.py
```
*The main application runs on `http://127.0.0.1:5000`.*

### 3. Setup Administrator Accounts
Registration defaults to normal users unless the email matches predefined Admin credentials. To access the admin panel, register with one of the following emails:
- `guptaayush122006@gmail.com`
- `jagratisinghal9@gmail.com`

---
*Developed with a focus on modern UI aesthetics and frictionless user experiences.*
