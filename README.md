# 🚀 Smart Parking Pro – Next-Gen Access Control

![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Framework-Flask-red?style=for-the-badge&logo=flask)
![UI](https://img.shields.io/badge/Design-Premium%20Glassmorphism-purple?style=for-the-badge)

A state-of-the-art **Smart Parking Ecosystem** built with Python and Flask. This project features a fully automated gate terminal driven by Artificial Intelligence (ANPR), premium glassmorphism aesthetics, dynamic chart analytics, and seamless digital wallet integrations for a frictionless user experience.

---

## ✨ Core Features

### 🤖 AI-Powered Gate Terminal (ANPR)
*   **Automatic Number Plate Recognition:** Leverages `EasyOCR` for high-precision vehicle plate extraction.
*   **Auto-Gate Control:** Instantly cross-checks plates with active bookings to open the barrier, log entries, and flag unauthorized vehicles.
*   **Real-time Logic:** Automated entry/exit detection with dynamic session management.

### 💎 Premium User Experience
*   **Live Interactive Map:** Visually select from 50 parking slots, dynamically color-coded by status (Available, Booked, Occupied).
*   **Digital Wallet & Payments:** Load funds via UPI QR codes and use balance for 1-click checkout.
*   **VIP Subscriptions:** Integrated membership system for discounted rates and automated clearances.

### 📊 Advanced Admin Command Center
*   **Live Analytics:** Real-time revenue trends and booking distributions via interactive `Chart.js` dashboards.
*   **Identity Management:** One-click tools to block users, manually top-up wallets, or force-free slots.
*   **Emergency Overrides:** Manual gate control and session simulation directly from the web interface.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, Flask, SQLite3 |
| **Frontend** | HTML5, CSS3 (Glassmorphism), Vanilla JS |
| **AI Engine** | EasyOCR, OpenCV (ANPR Logic) |
| **Data Vis** | Chart.js 4.0 |
| **Utilities** | qrcode, Jinja2, Werkzeug Security |

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and set up the environment:
```bash
git clone https://github.com/guptaayush006/smart-parking.git
cd smart-parking
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Launch the Ecosystem
For the full experience, run both the backend server and the standalone AI Gate application:

**Main Web Application (Port 5000):**
```bash
python app.py
```

**AI Gate Camera Terminal (Port 5001):**
```bash
python gate_app.py
```

---

## 🎨 Design Philosophy
The system uses a **Glassmorphism Design System** defined in CSS variables, ensuring a sleek, modern, and consistent look across all modules. Mobile-responsive layouts and subtle micro-animations provide a premium feel on any device.

---

## 👨‍💻 Developed By
**Ayush Gupta**  
[GitHub Profile](https://github.com/guptaayush006)

---
*Developed with a focus on mission-critical stability and high-end visual aesthetics.*
