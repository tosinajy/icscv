import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

app = Flask(__name__)

def get_db_connection():
    """Attempts to establish and return a new MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# --- Routes ---

@app.route('/')
def index():
    """Renders the main search frontend template."""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_carriers():
    """
    API Endpoint: Performs case-insensitive search.
    """
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
            wildcard_term = f"%{search_term.lower()}%"
            params = (wildcard_term, wildcard_term, wildcard_term)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            return jsonify(results)

    except Error as e:
        print(f"Query Error: {e}")
        return jsonify({'error': 'Search query failed'}), 500

@app.route('/carrier/<naic_code>')
def carrier_details(naic_code):
    """
    Route to display detailed information for a single carrier.
    """
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('index', error="Database connection failed."))

    carrier = None
    try:
        with conn, conn.cursor(dictionary=True) as cursor:
            query = "SELECT * FROM carriers WHERE naic_code = %s"
            cursor.execute(query, (naic_code,))
            carrier = cursor.fetchone()
            
    except Error as e:
        print(f"Detail Query Error: {e}")
        carrier = None
        
    return render_template('carrier_details.html', carrier=carrier, naic_code=naic_code)

if __name__ == '__main__':
    app.run(debug=True, port=5000)