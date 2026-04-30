import os
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import qrcode
from models import db, Admin, Permit, HealthCertificate

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['QR_FOLDER'] = os.path.join('static', 'qrcodes')
# Base URL for QR codes — set BASE_URL env var in production (e.g. https://myapp.up.railway.app)
BASE_URL = os.environ.get('BASE_URL', None)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QR_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'images'), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Initialize database and default admin
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = Admin(username='admin', password=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Admin.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    total_permits = Permit.query.count()
    total_certs = HealthCertificate.query.count()
    recent_permits = Permit.query.order_by(Permit.created_at.desc()).limit(5).all()
    recent_certs = HealthCertificate.query.order_by(HealthCertificate.created_at.desc()).limit(5).all()
    cert_type_counts = {
        1: HealthCertificate.query.filter_by(cert_type=1).count(),
        2: HealthCertificate.query.filter_by(cert_type=2).count(),
        3: HealthCertificate.query.filter_by(cert_type=3).count(),
        4: HealthCertificate.query.filter_by(cert_type=4).count(),
    }
    return render_template('dashboard.html',
        total_permits=total_permits,
        total_certs=total_certs,
        recent_permits=recent_permits,
        recent_certs=recent_certs,
        cert_type_counts=cert_type_counts
    )

def get_lan_ip():
    """Get the LAN IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def save_photo_and_qr(photo_file, uuid_str):
    photo_filename = None
    if photo_file and photo_file.filename != '':
        ext = photo_file.filename.split('.')[-1]
        photo_filename = f"{uuid_str}.{ext}"
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        photo_file.save(photo_path)

    # Generate QR Code
    # Automatically uses the current server URL (works locally AND on any hosting)
    # e.g. locally: http://192.168.1.5:8080  |  hosted: https://myapp.up.railway.app
    base = request.host_url.rstrip('/')
    qr_url = f"{base}/verify/{uuid_str}"

    qr = qrcode.make(qr_url)
    qr_filename = f"{uuid_str}.png"
    qr_path = os.path.join(app.config['QR_FOLDER'], qr_filename)
    qr.save(qr_path)
    
    return photo_filename, qr_filename

# ── Permits ──────────────────────────────────────────────
@app.route('/permits')
@login_required
def permits_list():
    q = request.args.get('q', '')
    if q:
        permits = Permit.query.filter(
            (Permit.name.ilike(f'%{q}%')) | (Permit.permit_number.ilike(f'%{q}%')) | (Permit.id_number.ilike(f'%{q}%'))
        ).order_by(Permit.created_at.desc()).all()
    else:
        permits = Permit.query.order_by(Permit.created_at.desc()).all()
    return render_template('permits_list.html', permits=permits, q=q)

@app.route('/permit/new', methods=['GET', 'POST'])
@login_required
def new_permit():
    if request.method == 'POST':
        permit = Permit(
            permit_number=request.form.get('permit_number'),
            name=request.form.get('name'),
            issue_date=request.form.get('issue_date'),
            expiry_date=request.form.get('expiry_date'),
            id_number=request.form.get('id_number'),
            nationality=request.form.get('nationality'),
            gender=request.form.get('gender'),
            company=request.form.get('company'),
            authority=request.form.get('authority'),
            purpose=request.form.get('purpose'),
            purpose_desc=request.form.get('purpose_desc')
        )
        db.session.add(permit)
        db.session.flush()
        
        photo_file = request.files.get('photo')
        photo_filename, qr_filename = save_photo_and_qr(photo_file, permit.uuid)
        permit.photo_path = photo_filename
        permit.qr_path = qr_filename
        
        db.session.commit()
        flash('تم إصدار التصريح بنجاح!', 'success')
        return redirect(url_for('view_permit', uuid=permit.uuid))
    return render_template('permit_form.html')

@app.route('/permit/<uuid>/delete', methods=['POST'])
@login_required
def delete_permit(uuid):
    permit = Permit.query.filter_by(uuid=uuid).first_or_404()
    db.session.delete(permit)
    db.session.commit()
    flash('تم حذف التصريح بنجاح.', 'success')
    return redirect(url_for('permits_list'))

# ── Certificates ─────────────────────────────────────────
@app.route('/certificates')
@login_required
def certificates_list():
    q = request.args.get('q', '')
    if q:
        certs = HealthCertificate.query.filter(
            (HealthCertificate.name.ilike(f'%{q}%')) | (HealthCertificate.cert_number.ilike(f'%{q}%')) | (HealthCertificate.id_number.ilike(f'%{q}%'))
        ).order_by(HealthCertificate.created_at.desc()).all()
    else:
        certs = HealthCertificate.query.order_by(HealthCertificate.created_at.desc()).all()
    return render_template('certificates_list.html', certs=certs, q=q)

@app.route('/certificate/new', methods=['GET', 'POST'])
@login_required
def new_certificate():
    if request.method == 'POST':
        cert = HealthCertificate(
            cert_type=int(request.form.get('cert_type')),
            cert_number=request.form.get('cert_number'),
            name=request.form.get('name'),
            id_number=request.form.get('id_number'),
            gender=request.form.get('gender'),
            nationality=request.form.get('nationality'),
            profession=request.form.get('profession'),
            issue_date=request.form.get('issue_date'),
            expiry_date=request.form.get('expiry_date'),
            edu_program_type=request.form.get('edu_program_type'),
            edu_program_expiry=request.form.get('edu_program_expiry'),
            place_of_issue=request.form.get('place_of_issue')
        )
        db.session.add(cert)
        db.session.flush()
        
        photo_file = request.files.get('photo')
        photo_filename, qr_filename = save_photo_and_qr(photo_file, cert.uuid)
        cert.photo_path = photo_filename
        cert.qr_path = qr_filename
        
        db.session.commit()
        flash('تم إصدار الشهادة بنجاح!', 'success')
        return redirect(url_for('view_certificate', uuid=cert.uuid))
    return render_template('certificate_form.html')

@app.route('/certificate/<uuid>/delete', methods=['POST'])
@login_required
def delete_certificate(uuid):
    cert = HealthCertificate.query.filter_by(uuid=uuid).first_or_404()
    db.session.delete(cert)
    db.session.commit()
    flash('تم حذف الشهادة بنجاح.', 'success')
    return redirect(url_for('certificates_list'))

# ── View ──────────────────────────────────────────────────
@app.route('/permit/<uuid>')
@login_required
def view_permit(uuid):
    permit = Permit.query.filter_by(uuid=uuid).first_or_404()
    return render_template('permit_view.html', permit=permit)

@app.route('/certificate/<uuid>')
@login_required
def view_certificate(uuid):
    cert = HealthCertificate.query.filter_by(uuid=uuid).first_or_404()
    return render_template('certificate_view.html', cert=cert)

# ── Public Verify ─────────────────────────────────────────
@app.route('/verify/<uuid>')
def verify(uuid):
    permit = Permit.query.filter_by(uuid=uuid).first()
    if permit:
        return render_template('verify_permit.html', permit=permit)
    
    cert = HealthCertificate.query.filter_by(uuid=uuid).first()
    if cert:
        return render_template('verify_certificate.html', cert=cert)
        
    return render_template('not_found.html'), 404

if __name__ == '__main__':
    lan_ip = get_lan_ip()
    print(f"\n{'='*55}")
    print(f"  ✅ السيرفر شغّال!")
    print(f"  🖥️  من جهازك  : http://localhost:8080")
    print(f"  📱 من الهاتف  : http://{lan_ip}:8080")
    print(f"{'='*55}\n")
    app.run(debug=True, host='0.0.0.0', port=8080)
