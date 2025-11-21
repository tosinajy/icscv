import os
import io
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# --- Auth Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

class User(UserMixin):
    def __init__(self, id, username, role_name, role_id):
        self.id = id
        self.username = username
        self.role_name = role_name
        self.role_id = role_id

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Database Error: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    query = "SELECT u.*, r.role_name FROM users u LEFT JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(user['user_id'], user['username'], user['role_name'], user['role_id'])
    return None

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated: return redirect(url_for('admin_login'))
            if current_user.role_name == 'Admin': return f(*args, **kwargs)
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT 1 FROM role_permissions rp JOIN permissions p ON rp.permission_id = p.permission_id WHERE rp.role_id = %s AND p.page_name = %s"
            cursor.execute(query, (current_user.role_id, permission_name))
            has_perm = cursor.fetchone()
            conn.close()
            if has_perm: return f(*args, **kwargs)
            else:
                flash("Access denied.", "danger")
                return redirect(url_for('admin_dashboard'))
        return decorated_function
    return decorator

# --- Public Routes ---

@app.route('/')
def index(): return render_template('index.html')

@app.route('/directory')
def directory():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM carriers ORDER BY legal_name LIMIT %s OFFSET %s", (per_page, offset))
    carriers = cursor.fetchall()
    conn.close()
    return render_template('directory.html', carriers=carriers, page=page, total_pages=10)

@app.route('/carrier/<naic_code>')
def carrier_details(naic_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM carriers WHERE naic_code = %s", (naic_code,))
    carrier = cursor.fetchone()
    
    history = []
    if carrier:
        cursor.execute("SELECT * FROM audit_log WHERE carrier_id = %s ORDER BY changed_at DESC LIMIT 5", (carrier['carrier_id'],))
        history = cursor.fetchall()
    conn.close()
    return render_template('carrier_details.html', carrier=carrier, history=history)

@app.route('/suggest-edit/<int:carrier_id>', methods=['POST'])
def suggest_edit(carrier_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO carrier_edits 
        (carrier_id, submitter_name, submitter_email, field_name, old_value, new_value, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
    """, (carrier_id, request.form.get('submitter_name'), request.form.get('submitter_email'),
          request.form.get('field_name'), request.form.get('old_value'), request.form.get('new_value')))
    conn.commit()
    conn.close()
    flash("Edit submitted for approval!", "success")
    return redirect(request.referrer)

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT u.*, r.role_name FROM users u LEFT JOIN roles r ON u.role_id = r.role_id WHERE u.username = %s", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user['user_id'], user['username'], user['role_name'], user['role_id']))
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
@permission_required('admin_dashboard')
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Carrier Stats
    cursor.execute("SELECT COUNT(*) as total FROM carriers")
    total_carriers = cursor.fetchone()['total']
    
    # 2. Edit Stats for Chart
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM carrier_edits 
        WHERE submitted_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY status
    """)
    edit_stats = cursor.fetchall()
    
    # 3. Data Quality Analysis (Hardcoded fields)
    dq_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN phone_claims IS NULL OR phone_claims = '' THEN 1 ELSE 0 END) as missing_phone,
            SUM(CASE WHEN website_url IS NULL OR website_url = '' THEN 1 ELSE 0 END) as missing_web,
            SUM(CASE WHEN payer_id IS NULL OR payer_id = '' THEN 1 ELSE 0 END) as missing_payer
        FROM carriers
    """
    cursor.execute(dq_query)
    dq_data = cursor.fetchone()
    
    dq_report = []
    if dq_data['total'] > 0:
        total = dq_data['total']
        dq_report = [
            {'field': 'Claims Phone', 'missing': dq_data['missing_phone'], 'pct': round((dq_data['missing_phone']/total)*100, 1)},
            {'field': 'Website', 'missing': dq_data['missing_web'], 'pct': round((dq_data['missing_web']/total)*100, 1)},
            {'field': 'Payer ID', 'missing': dq_data['missing_payer'], 'pct': round((dq_data['missing_payer']/total)*100, 1)},
        ]

    conn.close()
    return render_template('admin/dashboard.html', 
                           total_carriers=total_carriers, 
                           edit_stats=edit_stats,
                           dq_report=dq_report)

@app.route('/admin/queue')
@login_required
@permission_required('admin_queue')
def admin_queue():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT e.*, c.legal_name 
        FROM carrier_edits e
        JOIN carriers c ON e.carrier_id = c.carrier_id
        WHERE e.status = 'pending'
        ORDER BY e.submitted_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    edits = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) as total FROM carrier_edits WHERE status='pending'")
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    
    conn.close()
    return render_template('admin/queue.html', edits=edits, page=page, total_pages=total_pages)

@app.route('/admin/approve-edit/<int:edit_id>/<action>')
@login_required
@permission_required('admin_queue')
def approve_edit(edit_id, action):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM carrier_edits WHERE edit_id = %s", (edit_id,))
    edit = cursor.fetchone()
    
    if action == 'approve' and edit:
        # Whitelist allowed columns (Hardcoded)
        allowed_cols = ['legal_name', 'payer_id', 'phone_claims', 'address_claims_street', 'website_url']
        if edit['field_name'] in allowed_cols:
            try:
                query = f"UPDATE carriers SET {edit['field_name']} = %s WHERE carrier_id = %s"
                cursor.execute(query, (edit['new_value'], edit['carrier_id']))
                
                cursor.execute("INSERT INTO audit_log (carrier_id, action_type, description, changed_by) VALUES (%s, 'update', %s, %s)",
                               (edit['carrier_id'], f"Approved edit for {edit['field_name']}", f"Crowdsource: {edit['submitter_name']}"))
                
                cursor.execute("UPDATE carrier_edits SET status='approved', reviewed_by=%s, reviewed_at=NOW() WHERE edit_id=%s", 
                               (current_user.id, edit_id))
                conn.commit()
                flash("Edit approved and applied.", "success")
            except Error as e:
                flash(f"Database Error: {e}", "danger")
        else:
            flash(f"Field '{edit['field_name']}' is not authorized for auto-updates.", "warning")
            
    elif action == 'reject':
        cursor.execute("UPDATE carrier_edits SET status='rejected', reviewed_by=%s, reviewed_at=NOW() WHERE edit_id=%s", 
                       (current_user.id, edit_id))
        conn.commit()
        flash("Edit rejected.", "warning")

    conn.close()
    return redirect(url_for('admin_queue'))

@app.route('/admin/carriers', methods=['GET', 'POST'])
@login_required
@permission_required('admin_carriers')
def admin_carriers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM carriers"
    params = []
    if search:
        query += " WHERE legal_name LIKE %s OR naic_code LIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY legal_name ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    cursor.execute(query, tuple(params))
    carriers = cursor.fetchall()
    
    count_query = "SELECT COUNT(*) as total FROM carriers"
    count_params = []
    if search:
        count_query += " WHERE legal_name LIKE %s OR naic_code LIKE %s"
        count_params.extend([f"%{search}%", f"%{search}%"])
    cursor.execute(count_query, tuple(count_params))
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    
    conn.close()
    return render_template('admin/carriers.html', carriers=carriers, page=page, total_pages=total_pages, search=search)

@app.route('/admin/carriers/add', methods=['POST'])
@login_required
@permission_required('admin_carriers')
def add_carrier():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO carriers (legal_name, naic_code, payer_id, state_domicile, phone_claims) VALUES (%s, %s, %s, %s, %s)",
                       (request.form['legal_name'], request.form['naic_code'], request.form.get('payer_id'), request.form.get('state'), request.form.get('phone')))
        conn.commit()
        flash('Carrier added successfully', 'success')
    except Error as e:
        flash(f'Error adding carrier: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_carriers'))

@app.route('/admin/carriers/edit/<int:id>', methods=['POST'])
@login_required
@permission_required('admin_carriers')
def edit_carrier_admin(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE carriers SET legal_name=%s, naic_code=%s, payer_id=%s, phone_claims=%s WHERE carrier_id=%s",
                       (request.form['legal_name'], request.form['naic_code'], request.form['payer_id'], request.form['phone'], id))
        conn.commit()
        flash('Carrier updated', 'success')
    except Error as e:
        flash(f'Error: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_carriers'))

@app.route('/admin/carriers/delete/<int:id>')
@login_required
@permission_required('admin_carriers')
def delete_carrier(id):
    if current_user.role_name != 'Admin':
        flash("Only super admins can delete records.", "danger")
        return redirect(url_for('admin_carriers'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM carriers WHERE carrier_id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Carrier deleted', 'warning')
    return redirect(url_for('admin_carriers'))

@app.route('/admin/carriers/import', methods=['POST'])
@login_required
@permission_required('admin_carriers')
def import_carriers():
    file = request.files['csv_file']
    if not file: return redirect(url_for('admin_carriers'))
    try:
        df = pd.read_csv(file)
        conn = get_db_connection()
        cursor = conn.cursor()
        added = 0
        for _, row in df.iterrows():
            cursor.execute("SELECT 1 FROM carriers WHERE naic_code = %s", (row['naic_code'],))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO carriers (legal_name, naic_code, payer_id, state_domicile) VALUES (%s, %s, %s, %s)",
                               (row['legal_name'], row['naic_code'], row.get('payer_id'), row.get('state_domicile')))
                added += 1
        conn.commit()
        conn.close()
        flash(f"Imported {added} carriers.", "success")
    except Exception as e:
        flash(f"Import failed: {e}", "danger")
    return redirect(url_for('admin_carriers'))

@app.route('/admin/leads')
@login_required
@permission_required('admin_leads')
def admin_leads():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT submitter_name, submitter_email, COUNT(*) as contribution_count, MAX(submitted_at) as last_active FROM carrier_edits WHERE submitter_email != '' GROUP BY submitter_email, submitter_name ORDER BY last_active DESC LIMIT %s OFFSET %s", (per_page, offset))
    leads = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total FROM (SELECT submitter_email FROM carrier_edits WHERE submitter_email != '' GROUP BY submitter_email, submitter_name) as sub")
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    conn.close()
    return render_template('admin/leads.html', leads=leads, page=page, total_pages=total_pages)

@app.route('/admin/leads/export')
@login_required
@permission_required('admin_leads')
def export_leads():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT submitter_name, submitter_email FROM carrier_edits WHERE submitter_email != ''")
    leads = cursor.fetchall()
    conn.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Email'])
    for lead in leads:
        cw.writerow([lead['submitter_name'], lead['submitter_email']])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=leads_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@permission_required('admin_users')
def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        if action == 'add':
            password = generate_password_hash(request.form.get('password'))
            cursor.execute("INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)", (username, email, password, role_id))
            flash("User added.", "success")
        elif action == 'edit':
            user_id = request.form.get('user_id')
            cursor.execute("UPDATE users SET username=%s, email=%s, role_id=%s WHERE user_id=%s", (username, email, role_id, user_id))
            flash("User updated.", "success")
        conn.commit()
    cursor.execute("SELECT u.*, r.role_name FROM users u LEFT JOIN roles r ON u.role_id = r.role_id")
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()
    conn.close()
    return render_template('admin/users.html', users=users, roles=roles)

@app.route('/admin/roles', methods=['GET', 'POST'])
@login_required
@permission_required('admin_roles')
def admin_roles():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        if 'add_role' in request.form:
            role_name = request.form.get('role_name')
            desc = request.form.get('description')
            cursor.execute("INSERT INTO roles (role_name, description) VALUES (%s, %s)", (role_name, desc))
            conn.commit()
            flash("Role added.", "success")
        elif 'update_perms' in request.form:
            role_id = request.form.get('role_id')
            selected_perms = request.form.getlist('permissions')
            cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
            for perm_id in selected_perms:
                cursor.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s)", (role_id, perm_id))
            conn.commit()
            flash("Permissions updated.", "success")
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()
    cursor.execute("SELECT * FROM permissions")
    all_perms = cursor.fetchall()
    role_perms_map = {}
    cursor.execute("SELECT role_id, permission_id FROM role_permissions")
    for row in cursor.fetchall():
        if row['role_id'] not in role_perms_map: role_perms_map[row['role_id']] = []
        role_perms_map[row['role_id']].append(row['permission_id'])
    conn.close()
    return render_template('admin/roles.html', roles=roles, all_perms=all_perms, role_perms_map=role_perms_map)

if __name__ == '__main__':
    app.run(debug=True, port=5000)