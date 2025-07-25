import os
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
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
        query = text('SELECT * FROM users WHERE username = :username AND password = :password')
        result = db.session.execute(query, {'username': username, 'password': password})
        user = result.fetchone()
        if user:
            session['username'] = user.username
            session['role'] = user.role
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
        last = db.session.execute(text('SELECT MAX(app_ref_no) FROM candidates')).scalar()
        app_ref_no = (last + 1) if last else 50001
        fields = [
            'date_of_call', 'interview_type', 'client', 'source', 'source_type',
            'candidate_name', 'mobile', 'email', 'gender', 'age', 'location',
            'qualification', 'position', 'department', 'hr_comments', 'hr_status',
            'client_interview_date', 'interview_attended', 'not_attended_comments',
            'client_status', 'client_comments', 'final_status', 'comments'
        ]
        values = [request.form.get(f, '') for f in fields]
        params = {'app_ref_no': app_ref_no, 'recruiter': session['username']}
        for i, f in enumerate(fields):
            params[f] = values[i]
        placeholders = ', '.join(f':{k}' for k in ['app_ref_no', 'recruiter'] + fields)
        columns = ', '.join(['app_ref_no', 'recruiter'] + fields)
        sql = f"INSERT INTO candidates ({columns}) VALUES ({placeholders})"
        db.session.execute(text(sql), params)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_candidate.html')

@app.route('/view_candidates', methods=['GET', 'POST'])
def view_candidates():
    if 'username' not in session:
        return redirect(url_for('login'))

    name_filter = request.form.get('candidate_name', '').strip() if request.method == 'POST' else request.args.get('candidate_name','').strip()
    mobile_filter = request.form.get('mobile_number', '').strip() if request.method == 'POST' else request.args.get('mobile_number','').strip()
    position_filter = request.form.get('position', '').strip() if request.method == 'POST' else request.args.get('position','').strip()

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    base_sql = 'SELECT * FROM candidates WHERE 1=1'
    params = {}

    if session['role'] != 'admin':
        base_sql += ' AND recruiter = :recruiter'
        params['recruiter'] = session['username']
    if name_filter:
        base_sql += ' AND candidate_name ILIKE :name_filter'
        params['name_filter'] = f'%{name_filter}%'
    if mobile_filter:
        base_sql += ' AND mobile ILIKE :mobile_filter'
        params['mobile_filter'] = f'%{mobile_filter}%'
    if position_filter:
        base_sql += ' AND position ILIKE :position_filter'
        params['position_filter'] = f'%{position_filter}%'

    count_sql = f'SELECT COUNT(*) FROM ({base_sql}) AS sub'
    total = db.session.execute(text(count_sql), params).scalar()

    paginated_sql = base_sql + ' ORDER BY id DESC LIMIT :limit OFFSET :offset'
    params['limit'] = per_page
    params['offset'] = offset
    result = db.session.execute(text(paginated_sql), params)
    candidates = result.fetchall()
    total_pages = (total + per_page - 1) // per_page if total else 1

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
    params = {}

    if session['role'] != 'admin':
        base_sql += ' AND recruiter = :recruiter'
        params['recruiter'] = session['username']

    name_filter = request.args.get('candidate_name','').strip()
    mobile_filter = request.args.get('mobile_number','').strip()
    position_filter = request.args.get('position','').strip()

    if name_filter:
        base_sql += ' AND candidate_name ILIKE :name_filter'
        params['name_filter'] = f'%{name_filter}%'
    if mobile_filter:
        base_sql += ' AND mobile ILIKE :mobile_filter'
        params['mobile_filter'] = f'%{mobile_filter}%'
    if position_filter:
        base_sql += ' AND position ILIKE :position_filter'
        params['position_filter'] = f'%{position_filter}%'

    data = db.session.execute(text(base_sql), params).fetchall()

    if data:
        df = pd.DataFrame(data, columns=data[0].keys())
    else:
        df = pd.DataFrame(columns=[
            'app_ref_no', 'recruiter', 'date_of_call', 'interview_type', 'client', 'source', 'source_type',
            'candidate_name', 'mobile', 'email', 'gender', 'age', 'location',
            'qualification', 'position', 'department', 'hr_comments', 'hr_status',
            'client_interview_date', 'interview_attended', 'not_attended_comments',
            'client_status', 'client_comments', 'final_status', 'comments'
        ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Candidates')
    output.seek(0)
    return send_file(output, download_name='candidates.xlsx', as_attachment=True)

# ✅ NEW ROUTE: Edit Candidate
@app.route('/edit_candidate/<int:candidate_id>', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the candidate from DB
    result = db.session.execute(
        text('SELECT * FROM candidates WHERE id = :id'),
        {'id': candidate_id}
    )
    candidate = result.fetchone()
    if not candidate:
        return "Candidate not found", 404

    if request.method == 'POST':
        fields = [
            'date_of_call', 'interview_type', 'client', 'source', 'source_type',
            'candidate_name', 'mobile', 'email', 'gender', 'age', 'location',
            'qualification', 'position', 'department', 'hr_comments', 'hr_status',
            'client_interview_date', 'interview_attended', 'not_attended_comments',
            'client_status', 'client_comments', 'final_status', 'comments'
        ]
        updates = {field: request.form.get(field, '') for field in fields}
        set_clause = ', '.join([f"{field} = :{field}" for field in fields])
        updates['id'] = candidate_id
        sql = text(f"UPDATE candidates SET {set_clause} WHERE id = :id")
        db.session.execute(sql, updates)
        db.session.commit()
        return redirect(url_for('view_candidates'))

    return render_template('edit_candidate.html', candidate=candidate)

if __name__ == '__main__':
    app.run(debug=True)
