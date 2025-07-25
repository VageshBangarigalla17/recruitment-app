import os
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# Configure SQLAlchemy to use Render's Postgres
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---- Routes ----
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        result = db.engine.execute(
            'SELECT * FROM users WHERE username = %s AND password = %s',
            (username, password)
        )
        user = result.fetchone()
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
        # Get next reference number
        last = db.engine.execute('SELECT MAX(app_ref_no) FROM candidates').scalar()
        app_ref_no = (last + 1) if last else 50001
        fields = [
            'date_of_call', 'interview_type', 'client', 'source', 'source_type',
            'candidate_name', 'mobile', 'email', 'gender', 'age', 'location',
            'qualification', 'position', 'department', 'hr_comments', 'hr_status',
            'client_interview_date', 'interview_attended', 'not_attended_comments',
            'client_status', 'client_comments', 'final_status', 'comments'
        ]
        values = [request.form.get(f, '') for f in fields]
        params = [app_ref_no, session['username']] + values
        placeholders = ','.join(['%s'] * (len(params)))
        columns = ','.join(['app_ref_no', 'recruiter'] + fields)
        sql = f"INSERT INTO candidates ({columns}) VALUES ({placeholders})"
        db.engine.execute(sql, tuple(params))
        return redirect(url_for('dashboard'))
    return render_template('add_candidate.html')

@app.route('/view_candidates', methods=['GET', 'POST'])
def view_candidates():
    if 'username' not in session:
        return redirect(url_for('login'))
    # Filters
    name_filter = request.form.get('candidate_name', '').strip() if request.method == 'POST' else request.args.get('candidate_name','').strip()
    mobile_filter = request.form.get('mobile_number', '').strip() if request.method == 'POST' else request.args.get('mobile_number','').strip()
    position_filter = request.form.get('position', '').strip() if request.method == 'POST' else request.args.get('position','').strip()
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    # Base query
    base_sql = 'SELECT * FROM candidates WHERE 1=1'
    params = []
    if session['role'] != 'admin':
        base_sql += ' AND recruiter = %s'
        params.append(session['username'])
    if name_filter:
        base_sql += ' AND candidate_name ILIKE %s'
        params.append(f'%{name_filter}%')
    if mobile_filter:
        base_sql += ' AND mobile ILIKE %s'
        params.append(f'%{mobile_filter}%')
    if position_filter:
        base_sql += ' AND position ILIKE %s'
        params.append(f'%{position_filter}%')
    # Count total
    count_sql = f'SELECT COUNT(*) FROM ({base_sql}) AS sub'
    total = db.engine.execute(count_sql, tuple(params)).scalar()
    # Fetch paginated
    paginated_sql = base_sql + ' ORDER BY id DESC LIMIT %s OFFSET %s'
    result = db.engine.execute(paginated_sql, tuple(params + [per_page, offset]))
    candidates = result.fetchall()
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
    base_sql = 'SELECT * FROM candidates WHERE 1=1'
    params = []
    if session['role'] != 'admin':
        base_sql += ' AND recruiter = %s'
        params.append(session['username'])
    name_filter = request.args.get('candidate_name','').strip()
    mobile_filter = request.args.get('mobile_number','').strip()
    position_filter = request.args.get('position','').strip()
    if name_filter:
        base_sql += ' AND candidate_name ILIKE %s'
        params.append(f'%{name_filter}%')
    if mobile_filter:
        base_sql += ' AND mobile ILIKE %s'
        params.append(f'%{mobile_filter}%')
    if position_filter:
        base_sql += ' AND position ILIKE %s'
        params.append(f'%{position_filter}%')
    data = db.engine.execute(base_sql, tuple(params)).fetchall()
    df = pd.DataFrame(data, columns=data[0].keys() if data else [])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Candidates')
    output.seek(0)
    return send_file(output, download_name='candidates.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
