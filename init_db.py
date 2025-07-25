from app import app, db
from sqlalchemy import Column, Integer, String, Text

# --- Define Models ---
class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    app_ref_no = Column(Integer)
    recruiter = Column(String)
    date_of_call = Column(String)
    interview_type = Column(String)
    client = Column(String)
    source = Column(String)
    source_type = Column(String)
    candidate_name = Column(String)
    mobile = Column(String)
    email = Column(String)
    gender = Column(String)
    age = Column(String)
    location = Column(String)
    qualification = Column(String)
    position = Column(String)
    department = Column(String)
    hr_comments = Column(Text)
    hr_status = Column(String)
    client_interview_date = Column(String)
    interview_attended = Column(String)
    not_attended_comments = Column(Text)
    client_status = Column(String)
    client_comments = Column(Text)
    final_status = Column(String)
    comments = Column(Text)

class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

# --- Initialize Database within App Context ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # --- Seed Default Users ---
        default_users = [
            User(username='ADYAHR', password='pass123', role='admin'),
            User(username='Veena', password='pass123', role='recruiter'),
            User(username='Rani', password='pass123', role='recruiter'),
            User(username='Tasneem', password='pass123', role='recruiter'),
            User(username='Harsha Teja', password='pass123', role='recruiter'),
            User(username='Vasam Shiva', password='pass123', role='recruiter'),
        ]
        for u in default_users:
            if not User.query.filter_by(username=u.username).first():
                db.session.add(u)
        db.session.commit()
        print("✅ PostgreSQL database initialized with user and candidate tables.")
