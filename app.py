import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, MAIL_ADMIN_RECEIVER

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-prod'  # Required for flash messages

# --- Security: Simple In-Memory Rate Limiter ---
# Stores ip: timestamp to prevent spamming the email endpoint
request_log = {}

def is_rate_limited(ip_address):
    current_time = time.time()
    # Remove old entries (older than 1 hour)
    for ip in list(request_log.keys()):
        if current_time - request_log[ip]['start_time'] > 3600:
            del request_log[ip]
            
    if ip_address not in request_log:
        request_log[ip_address] = {'count': 1, 'start_time': current_time}
        return False
    
    user_data = request_log[ip_address]
    # Limit: 5 requests per hour per IP
    if user_data['count'] >= 5:
        return True
    
    user_data['count'] += 1
    return False

# --- Database Connection ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# --- Email Function ---
def send_issue_email(naic, name, comments):
    msg = MIMEMultipart()
    msg['From'] = MAIL_DEFAULT_SENDER
    msg['To'] = MAIL_ADMIN_RECEIVER
    msg['Subject'] = f"Issue Reported: {name} (NAIC: {naic})"

    body = f"""
    A user has reported an issue with a carrier.
    
    ----------------------------------------
    Carrier Name: {name}
    NAIC Code:    {naic}
    ----------------------------------------
    
    User Comments:
    {comments}
    
    ----------------------------------------
    Sent from CarrierCodeVerify
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_carriers():
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn, conn.cursor(dictionary=True) as cursor:
            query = """
                SELECT legal_name, naic_code, payer_id, contact_phone, website_url, state_domicile,
                       phone_claims, phone_prior_auth, phone_eligibility, line_of_business
                FROM carriers
                WHERE LOWER(legal_name) LIKE %s 
                   OR LOWER(naic_code) LIKE %s 
                   OR LOWER(payer_id) LIKE %s
                LIMIT 50
            """
            wildcard = f"%{search_term.lower()}%"
            cursor.execute(query, (wildcard, wildcard, wildcard))
            return jsonify(cursor.fetchall())
    except Error as e:
        print(f"Query Error: {e}")
        return jsonify({'error': 'Search query failed'}), 500

# In app.py, add this new route (e.g., before or after the search route)

@app.route('/directory')
def directory():
    conn = get_db_connection()
    if not conn:
        return render_template('index.html'), 500

    try:
        with conn, conn.cursor(dictionary=True) as cursor:
            # Fetch all carriers, ordered by state and then name
            query = """
                SELECT legal_name, naic_code, state_domicile 
                FROM carriers 
                ORDER BY state_domicile ASC, legal_name ASC
            """
            cursor.execute(query)
            carriers = cursor.fetchall()

            # Group carriers by state for the template
            grouped_carriers = {}
            for c in carriers:
                state = c['state_domicile'] if c['state_domicile'] else 'Other'
                if state not in grouped_carriers:
                    grouped_carriers[state] = []
                grouped_carriers[state].append(c)

            return render_template('directory.html', grouped_carriers=grouped_carriers)
    except Error as e:
        print(f"Directory Query Error: {e}")
        return redirect(url_for('index'))

@app.route('/carrier/<naic_code>')
def carrier_details(naic_code):
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index'))

    try:
        with conn, conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM carriers WHERE naic_code = %s LIMIT 1", (naic_code,))
            carrier = cursor.fetchone()
            return render_template('carrier_details.html', carrier=carrier, naic_code=naic_code)
    except Error as e:
        print(f"Detail Query Error: {e}")
        return render_template('carrier_details.html', carrier=None, naic_code=naic_code)

# --- New: Report Issue Routes ---

@app.route('/report-issue', methods=['GET', 'POST'])
def report_issue():
    if request.method == 'POST':
        # 1. Security: Honeypot Check (hidden field should be empty)
        if request.form.get('website_check'):
            # Silently fail for bots
            return redirect(url_for('index'))

        # 2. Security: Rate Limiting
        user_ip = request.remote_addr
        if is_rate_limited(user_ip):
            flash("Too many requests. Please try again later.", "danger")
            return redirect(url_for('index'))

        # 3. Process Form
        naic = request.form.get('naic_code')
        name = request.form.get('carrier_name')
        comments = request.form.get('comments')

        if send_issue_email(naic, name, comments):
            flash("Thank you! Your report has been sent to the admin.", "success")
        else:
            flash("There was an error sending your report. Please try again.", "danger")
        
        # Return to the carrier details page
        return redirect(url_for('carrier_details', naic_code=naic))

    # GET Request: Render form with pre-filled data
    naic = request.args.get('naic', '')
    name = request.args.get('name', '')
    return render_template('report_issue.html', naic=naic, name=name)

if __name__ == '__main__':
    app.run(debug=True, port=5000)