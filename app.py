import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Database Configuration - Ensure this is correct
db_config = {
    'host': 'localhost',
    'user': 'root',          # Replace with your MySQL username
    'password': 'vaug',  # Replace with your MySQL password
    'database': 'icscv'
}

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/')
def index():
    """Renders the main frontend template."""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search_carriers():
    """
    API Endpoint: Searches carriers and returns key results with new fields.
    """
    search_term = request.args.get('q', '').strip()

    if not search_term:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Select all fields, including the new actionable data
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
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/carrier/<naic_code>')
def carrier_details(naic_code):
    """
    Route to display detailed information for a single carrier based on NAIC code.
    """
    conn = get_db_connection()
    if not conn:
        # If DB connection fails, redirect to home with a note
        return redirect(url_for('index', error="Database connection failed."))

    carrier = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT *
            FROM carriers
            WHERE naic_code = %s
        """
        cursor.execute(query, (naic_code,))
        carrier = cursor.fetchone()

        if not carrier:
            # Carrier not found
            return render_template('carrier_details.html', carrier=None, naic_code=naic_code)
            
    except Error as e:
        print(f"Detail Query Error: {e}")
        carrier = None # Ensure carrier is None on error
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return render_template('carrier_details.html', carrier=carrier)


if __name__ == '__main__':
    app.run(debug=True, port=5000)