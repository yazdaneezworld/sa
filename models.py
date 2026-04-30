from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid
from datetime import datetime

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Permit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    permit_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.String(20))
    expiry_date = db.Column(db.String(20))
    id_number = db.Column(db.String(50))
    nationality = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    company = db.Column(db.String(150))
    authority = db.Column(db.String(100))
    purpose = db.Column(db.String(100))
    purpose_desc = db.Column(db.String(200))
    photo_path = db.Column(db.String(200))
    qr_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HealthCertificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    cert_type = db.Column(db.Integer, nullable=False) # 1: Madinah, 2: Makkah, 3: Unified, 4: Riyadh
    cert_number = db.Column(db.String(50))
    name = db.Column(db.String(100), nullable=False)
    id_number = db.Column(db.String(50))
    gender = db.Column(db.String(20)) # Mainly for Riyadh/Unified
    nationality = db.Column(db.String(50))
    profession = db.Column(db.String(100))
    issue_date = db.Column(db.String(20))
    expiry_date = db.Column(db.String(20))
    edu_program_type = db.Column(db.String(100)) # e.g. منشآت الغذاء
    edu_program_expiry = db.Column(db.String(20))
    place_of_issue = db.Column(db.String(100)) # For Riyadh
    photo_path = db.Column(db.String(200))
    qr_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
