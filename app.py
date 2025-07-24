from flask import Flask, render_template, request, redirect, session, url_for, send_file
import sqlite3
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db_connection():
    conn = sqlite3.connect('recruitment.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'], role=session['role'])

@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = get_db_connection()
        last = conn.execute('SELECT MAX(app_ref_no) FROM candidates').fetchone()[0]
        app_ref_no = (last + 1) if last else 50001

        recruiter = session['username']
        date_of_call = request.form.get('date_of_call', '')
        interview_type = request.form.get('interview_type', '')
        client = request.form.get('client', '')
        source = request.form.get('source', '')
        source_type = request.form.get('source_type', '')
        candidate_name = request.form.get('candidate_name', '')
        mobile = request.form.get('mobile', '')
        email = request.form.get('email', '')
        gender = request.form.get('gender', '')
        age = request.form.get('age', '')
        location = request.form.get('location', '')
        qualification = request.form.get('qualification', '')
        position = request.form.get('position', '')
        department = request.form.get('department', '')
        hr_comments = request.form.get('hr_comments', '')
        hr_status = request.form.get('hr_status', '')
        client_interview_date = request.form.get('client_interview_date', '')
        interview_attended = request.form.get('interview_attended', '')
        not_attended_comments = request.form.get('not_attended_comments', '')
        client_status = request.form.get('client_status', '')
        client_comments = request.form.get('client_comments', '')
        final_status = request.form.get('final_status', '')
        comments = request.form.get('comments', '')

        conn.execute('''
            INSERT INTO candidates (
                app_ref_no, recruiter, date_of_call, interview_type, client, source, source_type,
                candidate_name, mobile, email, gender, age, location, qualification,
                position, department, hr_comments, hr_status, client_interview_date,
                interview_attended, not_attended_comments, client_status,
                client_comments, final_status, comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            app_ref_no, recruiter, date_of_call, interview_type, client, source, source_type,
            candidate_name, mobile, email, gender, age, location, qualification,
            position, department, hr_comments, hr_status, client_interview_date,
            interview_attended, not_attended_comments, client_status,
            client_comments, final_status, comments
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    return render_template('add_candidate.html')

@app.route('/edit_candidate/<int:candidate_id>', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()

    if request.method == 'POST':
        fields = ['date_of_call', 'interview_type', 'client', 'source', 'source_type', 'candidate_name', 'mobile', 'email', 'gender', 'age', 'location', 'qualification', 'position', 'department', 'hr_comments', 'hr_status', 'client_interview_date', 'interview_attended', 'not_attended_comments', 'client_status', 'client_comments', 'final_status', 'comments']
        updates = [request.form.get(f, '') for f in fields]
        conn.execute(f'''
            UPDATE candidates SET 
                date_of_call=?, interview_type=?, client=?, source=?, source_type=?,
                candidate_name=?, mobile=?, email=?, gender=?, age=?, location=?, qualification=?,
                position=?, department=?, hr_comments=?, hr_status=?, client_interview_date=?,
                interview_attended=?, not_attended_comments=?, client_status=?,
                client_comments=?, final_status=?, comments=?
            WHERE id = ?
        ''', (*updates, candidate_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_candidates'))

    conn.close()
    return render_template('edit_candidate.html', candidate=candidate)

@app.route('/view_candidates', methods=['GET', 'POST'])
def view_candidates():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    name_filter = request.form.get('candidate_name', '').strip() if request.method == 'POST' else request.args.get('candidate_name', '').strip()
    mobile_filter = request.form.get('mobile_number', '').strip() if request.method == 'POST' else request.args.get('mobile_number', '').strip()
    position_filter = request.form.get('position', '').strip() if request.method == 'POST' else request.args.get('position', '').strip()

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    query = "SELECT * FROM candidates WHERE 1=1"
    params = []

    if session['role'] != 'admin':
        query += " AND recruiter = ?"
        params.append(session['username'])

    if name_filter:
        query += " AND candidate_name LIKE ?"
        params.append(f"%{name_filter}%")
    if mobile_filter:
        query += " AND mobile LIKE ?"
        params.append(f"%{mobile_filter}%")
    if position_filter:
        query += " AND position LIKE ?"
        params.append(f"%{position_filter}%")

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total = cursor.execute(count_query, params).fetchone()[0]

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    candidates = cursor.execute(query, params).fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'view_candidates.html',
        candidates=candidates,
        page=page,
        total_pages=total_pages,
        candidate_name=name_filter,
        mobile_number=mobile_filter,
        position=position_filter
    )

@app.route('/export_excel')
def export_excel():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM candidates WHERE 1=1"
    params = []

    if session['role'] != 'admin':
        query += " AND recruiter = ?"
        params.append(session['username'])

    name_filter = request.args.get('candidate_name', '').strip()
    mobile_filter = request.args.get('mobile_number', '').strip()
    position_filter = request.args.get('position', '').strip()

    if name_filter:
        query += " AND candidate_name LIKE ?"
        params.append(f"%{name_filter}%")
    if mobile_filter:
        query += " AND mobile LIKE ?"
        params.append(f"%{mobile_filter}%")
    if position_filter:
        query += " AND position LIKE ?"
        params.append(f"%{position_filter}%")

    data = cursor.execute(query, params).fetchall()
    df = pd.DataFrame(data, columns=data[0].keys() if data else [])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Candidates')

    output.seek(0)
    return send_file(output, download_name="candidates.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
