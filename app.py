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
    session.clear() 
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
    
    # Load users to dynamically populate the employee access list
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    # Extract only accounts categorized under the 'Employee' policy
    employees = [username for username, data in users.items() if data.get('role') == 'Employee']
    
    return render_template(
        'dashboard.html', 
        files=files, 
        current_role=session.get('role', 'Admin'), 
        current_user=session.get('username'),
        employees=employees
    )

# Admin-Only Route: Register New Employees
@app.route('/add_user', methods=['POST'])
def add_user():
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

# Admin-Only Route: Grant File-Specific Access to specific Employees (DAC / ACL)
@app.route('/grant_access', methods=['POST'])
def grant_access():
    if session.get('role') != 'Admin':
        return "Access Denied: Unauthorized administrative request.", 403

    filename = request.form.get('filename')
    target_user = request.form.get('target_user')
    
    if not filename or not target_user:
        flash("Authorization failed: Missing inputs.", "danger")
        return redirect(url_for('dashboard'))
        
    target_user_clean = target_user.strip().lower()
    
    # Verify that the target Employee actually exists in users.json
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    if target_user_clean not in users:
        flash(f"Authorization failed: Target user '{target_user_clean}' does not exist.", "danger")
        return redirect(url_for('dashboard'))
        
    vault_data = load_vault()
    file_found = False
    
    for file in vault_data:
        if file['original_name'] == filename:
            file_found = True
            # Initialize allowed_users array if missing
            if 'allowed_users' not in file:
                file['allowed_users'] = []
            
            if target_user_clean in file['allowed_users']:
                flash(f"User '{target_user_clean}' already possesses access clearance.", "danger")
            else:
                file['allowed_users'].append(target_user_clean)
                flash(f"Access granted: '{target_user_clean}' can now decrypt '{filename}'.", "success")
            break
            
    if not file_found:
        flash("Authorization failed: File not found.", "danger")
    else:
        save_vault(vault_data)
        
    return redirect(url_for('dashboard'))

# Admin-Only Route: Revoke File-Specific Access from specific Employees (DAC / ACL)
@app.route('/revoke_access', methods=['POST'])
def revoke_access():
    if session.get('role') != 'Admin':
        return "Access Denied: Unauthorized administrative request.", 403

    filename = request.form.get('filename')
    target_user = request.form.get('target_user')
    
    if not filename or not target_user:
        flash("Revocation failed: Missing inputs.", "danger")
        return redirect(url_for('dashboard'))
        
    target_user_clean = target_user.strip().lower()
    
    vault_data = load_vault()
    file_found = False
    
    for file in vault_data:
        if file['original_name'] == filename:
            file_found = True
            if 'allowed_users' in file and target_user_clean in file['allowed_users']:
                file['allowed_users'].remove(target_user_clean)
                flash(f"Access revoked: '{target_user_clean}' can no longer decrypt '{filename}'.", "success")
            else:
                flash(f"User '{target_user_clean}' did not possess access clearance.", "danger")
            break
            
    if not file_found:
        flash("Revocation failed: File not found.", "danger")
    else:
        save_vault(vault_data)
        
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
        "size": f"{len(file_bytes) / 1024:.1f} KB",
        "allowed_users": []  # Initialize empty file-access list
    })
    save_vault(vault_data)
    
    flash(f"File '{file.filename}' encrypted and stored in vault.", "success")
    return redirect(url_for('dashboard'))

# Decrypt File Route (Verifies permissions and matches integrity hash)
@app.route('/decrypt/<filename>')
def decrypt(filename):
    if 'username' not in session:
        return redirect(url_for('home'))

    vault_data = load_vault()
    target_meta = next((item for item in vault_data if item['original_name'] == filename), None)
    
    if not target_meta:
        return "File metadata not found in database.", 404
        
    # Hybrid RBAC + DAC Verification Check:
    allowed_list = target_meta.get('allowed_users', [])
    if session.get('role') != 'Admin' and session.get('username') not in allowed_list:
        return "Access Denied: You do not possess decryption clearances.", 403

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

# Cryptographic Payload Inspector API (Hex view vs Decrypted Plaintext)
@app.route('/inspect/<filename>')
def inspect(filename):
    if 'username' not in session:
        return jsonify({"error": "Session expired"}), 401
        
    vault_data = load_vault()
    target_meta = next((item for item in vault_data if item['original_name'] == filename), None)
    
    if not target_meta:
        return jsonify({"error": "File metadata not found."}), 404
        
    encrypted_path = os.path.join(ENCRYPTED_DIR, target_meta['encrypted_filename'])
    if not os.path.exists(encrypted_path):
        return jsonify({"error": "Encrypted file payload missing from storage."}), 404
        
    with open(encrypted_path, 'rb') as f:
        encrypted_bytes = f.read()
        
    # Format the first 256 bytes as a structured hex dump for visual demonstration
    preview_bytes = encrypted_bytes[:256]
    hex_dump = " ".join(f"{b:02X}" for b in preview_bytes)
    if len(encrypted_bytes) > 256:
        hex_dump += " ... [TRUNCATED]"
        
    # DAC Access Control Check
    allowed_list = target_meta.get('allowed_users', [])
    is_authorized = (session.get('role') == 'Admin') or (session.get('username') in allowed_list)
    
    if not is_authorized:
        # If unauthorized, return only the ciphertext (proving it is secure) but block plaintext
        return jsonify({
            "original_name": filename,
            "ciphertext_hex": hex_dump,
            "plaintext": "ACCESS_DENIED: Decryption Key Locked. Insufficient clearances.",
            "authorized": False
        })
        
    # If authorized, decrypt the ciphertext to display the plaintext
    try:
        cipher = GDES(GDES_KEY)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        try:
            plaintext = decrypted_bytes.decode('utf-8', errors='replace')
        except Exception:
            # Fallback representation if it's a binary file
            plaintext = "[Binary Stream Payload]\n" + " ".join(f"{b:02X}" for b in decrypted_bytes[:256])
    except Exception as e:
        plaintext = f"DECRYPTION_ERROR: Failed to run round functions. {str(e)}"
        
    return jsonify({
        "original_name": filename,
        "ciphertext_hex": hex_dump,
        "plaintext": plaintext,
        "authorized": True
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)