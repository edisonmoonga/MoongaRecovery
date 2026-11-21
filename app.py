from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'moonga_secret_key_123'

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
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT * FROM cases WHERE customer_name LIKE ? OR imei LIKE ?", ('%'+search_query+'%', '%'+search_query+'%'))
    else:
        cursor.execute("SELECT * FROM cases")
    all_cases = cursor.fetchall()
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
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cases (customer_name, phone_model, imei, phone_number, date_lost, location_lost, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_name, phone_model, imei, phone_number, date_lost, location_lost, status, notes))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/recover/<int:case_id>')
def recover_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE cases SET status = 'Recovered' WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/delete/<int:case_id>')
def delete_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM case_notes WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM gps_tracking WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/edit/<int:case_id>')
def edit_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case_to_edit = cursor.fetchone()
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
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cases SET customer_name=?, phone_model=?, imei=?, phone_number=?, date_lost=?, location_lost=?, notes=? WHERE id=?
    ''', (customer_name, phone_model, imei, phone_number, date_lost, location_lost, notes, case_id))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/case/<int:case_id>')
def view_case(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case_info = cursor.fetchone()
    cursor.execute("SELECT * FROM case_notes WHERE case_id = ? ORDER BY id DESC", (case_id,))
    notes_list = cursor.fetchall()
    # Fetch all GPS tracking history for this case
    cursor.execute("SELECT * FROM gps_tracking WHERE case_id = ? ORDER BY id DESC", (case_id,))
    gps_history = cursor.fetchall()
    conn.close()
    return render_template('view_case.html', case=case_info, notes=notes_list, gps_history=gps_history)

@app.route('/add_note/<int:case_id>', methods=['POST'])
def add_note(case_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    note_text = request.form['note_text']
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO case_notes (case_id, note_text, date_added) VALUES (?, ?, ?)", (case_id, note_text, current_date))
    conn.commit()
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
    conn = sqlite3.connect('mprs_cases.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gps_tracking (case_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)", (case_id, lat, lon, current_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)