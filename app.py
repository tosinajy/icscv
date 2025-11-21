import os
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, MAIL_ADMIN_RECEIVER

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

# --- Authentication Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' # Points to the function name for login

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database Error: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return User(user['user_id'], user['username'], user['role'])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_carriers():
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return jsonify([])

    conn = get_db_connection()
    if not conn: return jsonify([])
    
    cursor = conn.cursor(dictionary=True)
    # Search carrier names, NAIC, Payer ID, AND the new "Other Payer Names" table
    query = """
        SELECT DISTINCT c.legal_name, c.naic_code, c.payer_id, c.state_domicile, c.line_of_business, c.phone_claims
        FROM carriers c
        LEFT JOIN other_payer_names op ON c.carrier_id = op.carrier_id
        WHERE c.legal_name LIKE %s 
           OR c.naic_code LIKE %s 
           OR c.payer_id LIKE %s
           OR op.payer_name LIKE %s
        LIMIT 50
    """
    wildcard = f"%{search_term}%"
    cursor.execute(query, (wildcard, wildcard, wildcard, wildcard))
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)

@app.route('/directory')
def directory():
    page = request.args.get('page', 1, type=int)
    state_filter = request.args.get('state', '')
    per_page = 50
    offset = (page - 1) * per_page

    conn = get_db_connection()
    if not conn: return render_template('index.html') # Fallback
    
    cursor = conn.cursor(dictionary=True)
    
    # Base query
    query = "SELECT legal_name, naic_code, state_domicile, line_of_business FROM carriers"
    count_query = "SELECT COUNT(*) as total FROM carriers"
    params = []
    
    if state_filter:
        query += " WHERE state_domicile = %s"
        count_query += " WHERE state_domicile = %s"
        params.append(state_filter)
    
    query += " ORDER BY legal_name ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    cursor.execute(query, tuple(params))
    carriers = cursor.fetchall()
    
    # Get total for pagination
    cursor.execute(count_query, tuple(params) if state_filter else ())
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    
    conn.close()
    return render_template('directory.html', carriers=carriers, page=page, total_pages=total_pages, state_filter=state_filter)

@app.route('/carrier/<naic_code>')
def carrier_details(naic_code):
    conn = get_db_connection()
    if not conn: return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Fetch Carrier + Extended NAIC Data
    cursor.execute("""
        SELECT c.*, n.website, n.address_line_1, n.city, n.state, n.zip,
               n.company_licensed_in, n.business_type_code
        FROM carriers c
        LEFT JOIN naic_data n ON c.carrier_id = n.carrier_id
        WHERE c.naic_code = %s
    """, (naic_code,))
    carrier = cursor.fetchone()
    
    history = []
    if carrier:
        cursor.execute("SELECT * FROM audit_log WHERE carrier_id = %s ORDER BY changed_at DESC LIMIT 5", (carrier['carrier_id'],))
        history = cursor.fetchall()

    conn.close()
    return render_template('carrier_details.html', carrier=carrier, history=history)

@app.route('/report-issue', methods=['GET', 'POST'])
def report_issue():
    # Simplified report issue (Keep your existing email logic if preferred)
    if request.method == 'POST':
        flash("Report submitted successfully.", "success")
        return redirect(url_for('index'))
    
    naic = request.args.get('naic', '')
    name = request.args.get('name', '')
    return render_template('report_issue.html', naic=naic, name=name)

# --- Crowdsourcing Routes ---

@app.route('/suggest-edit/<int:carrier_id>', methods=['POST'])
def suggest_edit(carrier_id):
    name = request.form.get('submitter_name')
    email = request.form.get('submitter_email')
    field = request.form.get('field_name')
    new_val = request.form.get('new_value')
    old_val = request.form.get('old_value')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO carrier_edits 
        (carrier_id, submitter_name, submitter_email, field_name, old_value, new_value, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
    """, (carrier_id, name, email, field, old_val, new_val))
    conn.commit()
    conn.close()
    
    flash("Suggestion submitted for review!", "success")
    return redirect(request.referrer)

# --- Admin Routes ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user['user_id'], user['username'], user['role']))
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count FROM carrier_edits WHERE status='pending'")
    pending_count = cursor.fetchone()['count']
    conn.close()
    return render_template('admin/dashboard.html', pending_count=pending_count)

@app.route('/admin/queue')
@login_required
@admin_required
def admin_queue():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, c.legal_name, c.naic_code 
        FROM carrier_edits e
        JOIN carriers c ON e.carrier_id = c.carrier_id
        WHERE e.status = 'pending'
        ORDER BY e.submitted_at DESC
    """)
    edits = cursor.fetchall()
    conn.close()
    return render_template('admin/queue.html', edits=edits)

@app.route('/admin/approve-edit/<int:edit_id>/<action>')
@login_required
@admin_required
def approve_edit(edit_id, action):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM carrier_edits WHERE edit_id = %s", (edit_id,))
    edit = cursor.fetchone()
    
    if action == 'approve' and edit:
        # Security: Whitelist allowed columns to prevent SQL injection
        allowed_cols = ['legal_name', 'payer_id', 'phone_claims', 'address_claims_street', 'website']
        if edit['field_name'] in allowed_cols:
            # Update Carrier Table
            query = f"UPDATE carriers SET {edit['field_name']} = %s WHERE carrier_id = %s"
            cursor.execute(query, (edit['new_value'], edit['carrier_id']))
            
            # Add Audit Log
            cursor.execute("INSERT INTO audit_log (carrier_id, action_type, description, changed_by) VALUES (%s, 'update', %s, %s)",
                           (edit['carrier_id'], f"Updated {edit['field_name']}", f"Crowdsource: {edit['submitter_name']}"))
            
            # Mark Approved
            cursor.execute("UPDATE carrier_edits SET status='approved', reviewed_by=%s, reviewed_at=NOW() WHERE edit_id=%s", 
                           (current_user.id, edit_id))
            flash("Edit approved.", "success")
        else:
            flash("Field not authorized for auto-update.", "danger")
            
    elif action == 'reject':
        cursor.execute("UPDATE carrier_edits SET status='rejected', reviewed_by=%s, reviewed_at=NOW() WHERE edit_id=%s", 
                       (current_user.id, edit_id))
        flash("Edit rejected.", "warning")

    conn.commit()
    conn.close()
    return redirect(url_for('admin_queue'))

@app.route('/admin/bulk-upload', methods=['POST'])
@login_required
@admin_required
def bulk_upload():
    file = request.files['csv_file']
    if not file: return redirect(url_for('admin_dashboard'))
    
    try:
        df = pd.read_csv(file)
        conn = get_db_connection()
        cursor = conn.cursor()
        success_count = 0
        
        for _, row in df.iterrows():
            # Simple logic: check if Payer ID exists, if not, insert
            cursor.execute("SELECT carrier_id FROM carriers WHERE payer_id = %s", (row['payer_id'],))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO carriers (legal_name, naic_code, payer_id, state_domicile) VALUES (%s, %s, %s, %s)",
                               (row['legal_name'], row['naic_code'], row['payer_id'], row['state_domicile']))
                success_count += 1
        
        conn.commit()
        conn.close()
        flash(f"Successfully uploaded {success_count} new carriers.", "success")
    except Exception as e:
        flash(f"Error uploading CSV: {e}", "danger")

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/config')
@login_required
@admin_required
def admin_config():
    # In a real app, you'd fetch these from a DB table, not the config file directly
    return render_template('admin/email_config.html', config=app.config)

if __name__ == '__main__':
    app.run(debug=True, port=5000)