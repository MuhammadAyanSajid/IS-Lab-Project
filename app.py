import os
import json
import hashlib
import uuid
import io
from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify, flash
from gdes import GDES

app = Flask(__name__)
app.secret_key = 'G-DES_SECRET_SESSION_SIGNING_KEY_2026' # HMAC-SHA256 Secret key

# Paths
ENCRYPTED_DIR = 'encrypted_files'
VAULT_META_FILE = 'vault.json'
USERS_FILE = 'users.json'

os.makedirs(ENCRYPTED_DIR, exist_ok=True)

# G-DES Symmetric Key (exactly 8 bytes / 64 bits)
GDES_KEY = b"Cyb3rPnk"

# Setup default credentials with salted hashes if users.json is missing
def setup_users():
    if not os.path.exists(USERS_FILE):
        # Initializing database configurations
        users = {
            "admin_account": {
                "salt": "n3on_salt_1",
                "password_hash": hashlib.sha256("admin123".encode() + "n3on_salt_1".encode()).hexdigest(),
                "role": "Admin"
            },
            "employee_staff": {
                "salt": "m4g3nta_salt_2",
                "password_hash": hashlib.sha256("employee123".encode() + "m4g3nta_salt_2".encode()).hexdigest(),
                "role": "Employee"
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)

setup_users()

# Load/Save Metadata helpers
def load_vault():
    if os.path.exists(VAULT_META_FILE):
        with open(VAULT_META_FILE, 'r') as f:
            return json.load(f)
    return []

def save_vault(vault_data):
    with open(VAULT_META_FILE, 'w') as f:
        json.dump(vault_data, f, indent=4)

# Gateway Landing Route
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# Secure Password Verification Logic
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('login.html', error="CREDENTIALS_REQUIRED: Missing inputs.")
        
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    username_clean = username.strip().lower()
    
    if username_clean in users:
        user_data = users[username_clean]
        salt = user_data['salt']
        
        # Verify salted hash
        input_hash = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
        
        if input_hash == user_data['password_hash']:
            # Cryptographically sign session variables
            session['username'] = username_clean
            session['role'] = user_data['role']
            return redirect(url_for('dashboard'))
            
    return render_template('login.html', error="ACCESS_DENIED: Invalid User ID or Passphrase.")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
    files = load_vault()
    return render_template('dashboard.html', files=files, current_role=session.get('role', 'Admin'))

# Admin-Only Route: Register New Employees
@app.route('/add_user', methods=['POST'])
def add_user():
    # Server-Side RBAC Enforcement: Is the user an Admin?
    if session.get('role') != 'Admin':
        return "Access Denied: Unauthorized administrative request.", 403

    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash("Registration failed: Missing parameters.", "danger")
        return redirect(url_for('dashboard'))
        
    username_clean = username.strip().lower()
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    if username_clean in users:
        flash(f"Registration failed: User '{username_clean}' already exists.", "danger")
        return redirect(url_for('dashboard'))
        
    # Generate unique salt and SHA-256 hash for the new Employee
    new_salt = uuid.uuid4().hex[:12]
    new_hash = hashlib.sha256(password.encode() + new_salt.encode()).hexdigest()
    
    users[username_clean] = {
        "salt": new_salt,
        "password_hash": new_hash,
        "role": "Employee"
    }
    
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)
        
    flash(f"User '{username_clean}' successfully registered as Employee.", "success")
    return redirect(url_for('dashboard'))

# Admin-Only File Uploader Route
@app.route('/upload', methods=['POST'])
def upload():
    # Server-Side RBAC Enforcement
    if session.get('role') != 'Admin':
        return jsonify({"error": "Unauthorized action"}), 403

    if 'file' not in request.files:
        return redirect(url_for('dashboard'))
        
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('dashboard'))

    file_bytes = file.read()
    
    # Calculate SHA-256 for integrity verification
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Run custom G-DES encryption
    cipher = GDES(GDES_KEY)
    encrypted_bytes = cipher.encrypt(file_bytes)
    
    file_id = str(uuid.uuid4())
    encrypted_filename = f"{file_id}.gdes"
    with open(os.path.join(ENCRYPTED_DIR, encrypted_filename), 'wb') as f:
        f.write(encrypted_bytes)
        
    vault_data = load_vault()
    vault_data.insert(0, {
        "original_name": file.filename,
        "encrypted_filename": encrypted_filename,
        "hash": file_hash,
        "blocks": len(encrypted_bytes) // 16,
        "size": f"{len(file_bytes) / 1024:.1f} KB"
    })
    save_vault(vault_data)
    
    flash(f"File '{file.filename}' encrypted and stored in vault.", "success")
    return redirect(url_for('dashboard'))

# Decrypt File Route (Verifies permissions and matches integrity hash)
@app.route('/decrypt/<filename>')
def decrypt(filename):
    # Server-Side RBAC Enforcement
    if session.get('role') != 'Admin':
        return "Access Denied: You do not possess decryption privileges.", 403

    vault_data = load_vault()
    target_meta = next((item for item in vault_data if item['original_name'] == filename), None)
    
    if not target_meta:
        return "File metadata not found in database.", 404
        
    encrypted_path = os.path.join(ENCRYPTED_DIR, target_meta['encrypted_filename'])
    
    with open(encrypted_path, 'rb') as f:
        encrypted_bytes = f.read()
        
    # Run G-DES decryption
    cipher = GDES(GDES_KEY)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    
    # Verify Decrypted Hash against Metadata (Integrity Verification check)
    decrypted_hash = hashlib.sha256(decrypted_bytes).hexdigest()
    if decrypted_hash != target_meta['hash']:
        return "INTEGRITY CORRUPTED: Hashes do not match.", 500
        
    return send_file(
        io.BytesIO(decrypted_bytes),
        as_attachment=True,
        download_name=target_meta['original_name']
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)