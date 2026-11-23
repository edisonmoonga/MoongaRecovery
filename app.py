from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'moonga_secret_key_123'

# DATABASE CONNECTION
DATABASE_URL = "postgresql://postgres:moonga225588.@db.npeakgkqzjhxnnvsdnjx.supabase.co:5432/postgres"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY,
            customer_name TEXT,
            phone_model TEXT,
            imei TEXT,
            phone_number TEXT,
            date_lost TEXT,
            location_lost TEXT,
            status TEXT,
            notes TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS case_notes (
            id SERIAL PRIMARY KEY,
            case_id INTEGER,
            note_text TEXT,
            date_added TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gps_tracking (
            id SERIAL PRIMARY KEY,
            case_id INTEGER,
            latitude TEXT,
            longitude TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    if search_query:
        cur.execute("SELECT * FROM cases WHERE customer_name ILIKE %s OR imei ILIKE %s", ('%'+search_query+'%', '%'+search_query+'%'))
    else:
        cur.execute("SELECT * FROM cases")
    
    all_cases = [tuple(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('index.html', cases=all_cases, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_case():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    customer_name = request.form['customer_name']
    phone_model = request.form['phone_model']
    imei = request.form['imei']
    phone_number = request.form['phone_number']
    date_lost = request.form['date_lost']
    location_lost = request.form['location_lost']
    notes = request.form['notes']
    status = "Open"
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO cases (customer_name, phone_model, imei, phone_number, date_lost, location_lost, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (customer_name, phone_model, imei, phone_number, date_lost, location_lost, status, notes))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/recover/<int:case_id>')
def recover_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cases SET status = 'Recovered' WHERE id = %s", (case_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/delete/<int:case_id>')
def delete_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM case_notes WHERE case_id = %s", (case_id,))
    cur.execute("DELETE FROM gps_tracking WHERE case_id = %s", (case_id,))
    cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/edit/<int:case_id>')
def edit_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case_to_edit = tuple(cur.fetchone())
    cur.close()
    conn.close()
    return render_template('edit.html', case=case_to_edit)

@app.route('/update/<int:case_id>', methods=['POST'])
def update_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    customer_name = request.form['customer_name']
    phone_model = request.form['phone_model']
    imei = request.form['imei']
    phone_number = request.form['phone_number']
    date_lost = request.form['date_lost']
    location_lost = request.form['location_lost']
    notes = request.form['notes']
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE cases SET customer_name=%s, phone_model=%s, imei=%s, phone_number=%s, date_lost=%s, location_lost=%s, notes=%s WHERE id=%s
    ''', (customer_name, phone_model, imei, phone_number, date_lost, location_lost, notes, case_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/case/<int:case_id>')
def view_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case_info = tuple(cur.fetchone())
    
    cur.execute("SELECT * FROM case_notes WHERE case_id = %s ORDER BY id DESC", (case_id,))
    notes_list = [tuple(row) for row in cur.fetchall()]
    
    cur.execute("SELECT * FROM gps_tracking WHERE case_id = %s ORDER BY id DESC", (case_id,))
    gps_history = [tuple(row) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    return render_template('view_case.html', case=case_info, notes=notes_list, gps_history=gps_history)

@app.route('/add_note/<int:case_id>', methods=['POST'])
def add_note(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    note_text = request.form['note_text']
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO case_notes (case_id, note_text, date_added) VALUES (%s, %s, %s)", (case_id, note_text, current_date))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('view_case', case_id=case_id))

@app.route('/track/<int:case_id>')
def track_page(case_id):
    return render_template('track.html', case_id=case_id)

@app.route('/api/location/<int:case_id>', methods=['POST'])
def receive_location(case_id):
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO gps_tracking (case_id, latitude, longitude, timestamp) VALUES (%s, %s, %s, %s)", (case_id, lat, lon, current_time))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/status', methods=['GET', 'POST'])
def public_status():
    case_info = None
    error = None
    if request.method == 'POST':
        imei_search = request.form['imei']
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute("SELECT * FROM cases WHERE imei = %s", (imei_search,))
        row = cur.fetchone()
        if row:
            case_info = tuple(row)
        cur.close()
        conn.close()
        if not case_info:
            error = "No case found with that IMEI. Please check the number and try again."
            
    return render_template('public_status.html', case=case_info, error=error)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
