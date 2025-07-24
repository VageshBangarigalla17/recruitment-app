
import sqlite3

# Connect to database (creates file if it doesn't exist)
conn = sqlite3.connect('recruitment.db')
c = conn.cursor()

# ❗ Drop candidates table if exists (starting fresh)
c.execute('DROP TABLE IF EXISTS candidates')

# ✅ Create candidates table with App Ref No and full structure
c.execute('''
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_ref_no INTEGER,
    recruiter TEXT,
    date_of_call TEXT,
    interview_type TEXT,
    client TEXT,
    source TEXT,
    source_type TEXT,
    candidate_name TEXT,
    mobile TEXT,
    email TEXT,
    gender TEXT,
    age TEXT,
    location TEXT,
    qualification TEXT,
    position TEXT,
    department TEXT,
    hr_comments TEXT,
    hr_status TEXT,
    client_interview_date TEXT,
    interview_attended TEXT,
    not_attended_comments TEXT,
    client_status TEXT,
    client_comments TEXT,
    final_status TEXT,
    comments TEXT
)
''')

# ✅ Create users table if not exists
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
''')

# ✅ Insert default users (admin + 5 recruiters)
users = [
    ('ADYAHR', 'pass123', 'admin'),
    ('Veena', 'pass123', 'recruiter'),
    ('Rani', 'pass123', 'recruiter'),
    ('Tasneem', 'pass123', 'recruiter'),
    ('Harsha Teja', 'pass123', 'recruiter'),
    ('Vasam Shiva', 'pass123', 'recruiter'),
]

# Insert only if not already exists
for user in users:
    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', user)
    except sqlite3.IntegrityError:
        continue

conn.commit()
conn.close()

print("✅ Fresh database created with App Ref No support.")
