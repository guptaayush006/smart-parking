from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__, template_folder='gate_templates')

# Configuration to connect to main server
MAIN_SERVER = "http://127.0.0.1:5000"
ADMIN_EMAIL = "guptaayush122006@gmail.com"  
ADMIN_PASSWORD = "admin"

# Global session to maintain admin login to main app
api_session = requests.Session()

def ensure_login():
    """Ensure we are connected and logged into the main web app as admin."""
    # Check if we already have a session cookie
    if 'session' not in api_session.cookies:
        try:
            api_session.post(f"{MAIN_SERVER}/api/auth/login", data={
                'email': ADMIN_EMAIL,
                'password': ADMIN_PASSWORD
            })
            if 'session' not in api_session.cookies:
                print("==================================================")
                print(" WARNING: GATE TERMINAL FAILED TO LOGIN AS ADMIN!")
                print(" Check ADMIN_EMAIL and ADMIN_PASSWORD in gate_app.py")
                print("==================================================")
        except Exception as e:
            print(f"Connection to main server failed: {e}")
@app.route('/')
def index():
    return render_template('gate_index.html')

@app.route('/proxy/verify', methods=['POST'])
def proxy_verify():
    ensure_login()
    vehicle_number = request.json.get('vehicle_number')
    
    try:
        req = api_session.post(f"{MAIN_SERVER}/api/gate/verify", json={'vehicle_number': vehicle_number})
        return jsonify(req.json()), req.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({'status': 'denied', 'message': 'Main Server (127.0.0.1:5000) is offline.'}), 500
    except Exception as e:
        return jsonify({'status': 'denied', 'message': str(e)}), 500

if __name__ == '__main__':
    print("==================================================")
    print(" GATE TERMINAL SEPARATE UI RUNNING ON PORT 5001")
    print("==================================================")
    # Run on port 5001 so it doesn't conflict with main app on 5000
    app.run(port=5001, debug=True)
