from flask import Flask, render_template, request, jsonify
import requests
import easyocr
import cv2
import numpy as np
import base64
import re
import io
from PIL import Image

app = Flask(__name__, template_folder='gate_templates')

# Configuration to connect to main server
MAIN_SERVER = "http://127.0.0.1:5000"
ADMIN_EMAIL = "guptaayush122006@gmail.com"  
ADMIN_PASSWORD = "admin"

# Initialize EasyOCR Reader (English)
# This will download the model files on the first run
print("--- AI: Initializing EasyOCR Engine... ---")
reader = easyocr.Reader(['en'], gpu=False, verbose=False) 

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

@app.route('/proxy/scan_ocr', methods=['POST'])
def proxy_scan_ocr():
    """Receive image from webcam, run OCR, and verify with gate."""
    data = request.json.get('image')
    if not data:
        return jsonify({'status': 'denied', 'message': 'No image received'}), 400

    try:
        # 1. Decode base64 image
        header, encoded = data.split(",", 1)
        image_data = base64.b64decode(encoded)
        
        # 2. Convert to OpenCV format
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 3. AI Text Extraction
        results = reader.readtext(img, detail=0)
        print(f"--- AI Detected Text: {results} ---")
        
        # 4. Find the most likely Number Plate
        # We look for alphanumeric strings that aren't common noise
        plate = ""
        for text in results:
            clean = re.sub(r'[^A-Z0-9]', '', text.upper())
            if len(clean) >= 4: # Typical plate length minimum
                plate = clean
                break
        
        if not plate:
            return jsonify({'status': 'denied', 'message': 'Could not detect any clear text. Try holding the paper steady.'})

        # 5. Automatically verify with main server
        ensure_login()
        req = api_session.post(f"{MAIN_SERVER}/api/gate/verify", json={'vehicle_number': plate})
        
        result = req.json()
        # Add the detected plate to the response so the UI can show what it read
        result['vehicle_number'] = plate
        return jsonify(result), req.status_code

    except Exception as e:
        print(f"OCR Error: {e}")
        return jsonify({'status': 'denied', 'message': f'AI Error: {str(e)}'}), 500

if __name__ == '__main__':
    print("==================================================")
    print(" GATE TERMINAL SEPARATE UI RUNNING ON PORT 5001")
    print("==================================================")
    # Run on port 5001 so it doesn't conflict with main app on 5000
    app.run(port=5001, debug=True)
