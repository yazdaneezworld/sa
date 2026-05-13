import os, sys
sys.path.append(os.path.abspath('.'))
from app import app, db
from models import Permit

with app.app_context():
    test_permit = Permit(
        permit_number='TEST123',
        name='اختبار',
        issue_date='2024-01-01',
        expiry_date='2025-01-01',
        id_number='1234567890',
        nationality='سعودي',
        gender='ذكر',
        dob='1990-01-01',
        company='شركة اختبار',
        authority='جهة اختبار',
        purpose='اختبار',
        purpose_desc='اختبار إضافة تصريح'
    )
    db.session.add(test_permit)
    db.session.commit()
    print(test_permit.uuid)
