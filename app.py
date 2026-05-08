import os
import socket
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import qrcode
from models import db, Admin, Permit, HealthCertificate

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['QR_FOLDER'] = os.path.join('static', 'qrcodes')

PORT = int(os.environ.get('PORT', 8080))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    """Get the LAN IP address of this machine, more robustly."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return '127.0.0.1'

def save_photo_and_qr(photo_file, uuid_str):
    photo_filename = None
    if photo_file and photo_file.filename != '':
        ext = photo_file.filename.split('.')[-1]
        photo_filename = f"{uuid_str}.{ext}"
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        photo_file.save(photo_path)

    # Use request.host_url to get the public domain if running on a server,
    # otherwise fallback to LAN IP for local testing.
    if request:
        base_url = request.host_url.rstrip('/')
        qr_url = f"{base_url}/verify/{uuid_str}"
    else:
        lan_ip = get_lan_ip()
        qr_url = f"http://{lan_ip}:{PORT}/verify/{uuid_str}"
        
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
            dob=request.form.get('dob'),
            company=request.form.get('company'),
            authority=request.form.get('authority'),
            purpose=request.form.get('purpose'),
            purpose_desc=request.form.get('purpose_desc')
        )
        db.session.add(permit)
        db.session.flush()
        
        photo_file = request.files.get('photo')
        if photo_file and not allowed_file(photo_file.filename):
            flash('نوع الملف غير مسموح به. يرجى رفع صورة فقط.')
            return render_template('permit_form.html', permit=permit)

        photo_filename, qr_filename = save_photo_and_qr(photo_file, permit.uuid)
        permit.photo_path = photo_filename
        permit.qr_path = qr_filename
        
        db.session.commit()
        flash('تم إصدار التصريح بنجاح!', 'success')
        return redirect(url_for('view_permit', uuid=permit.uuid))
    return render_template('permit_form.html')

@app.route('/permit/<uuid>/edit', methods=['GET', 'POST'])
@login_required
def edit_permit(uuid):
    permit = Permit.query.filter_by(uuid=uuid).first_or_404()
    if request.method == 'POST':
        permit.permit_number = request.form.get('permit_number')
        permit.name = request.form.get('name')
        permit.issue_date = request.form.get('issue_date')
        permit.expiry_date = request.form.get('expiry_date')
        permit.id_number = request.form.get('id_number')
        permit.nationality = request.form.get('nationality')
        permit.gender = request.form.get('gender')
        permit.dob = request.form.get('dob')
        permit.company = request.form.get('company')
        permit.authority = request.form.get('authority')
        permit.purpose = request.form.get('purpose')
        permit.purpose_desc = request.form.get('purpose_desc')
        
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename != '':
            if not allowed_file(photo_file.filename):
                flash('نوع الملف غير مسموح به.')
                return render_template('permit_form.html', permit=permit)
            photo_filename, qr_filename = save_photo_and_qr(photo_file, permit.uuid)
            permit.photo_path = photo_filename
        
        db.session.commit()
        flash('تم تحديث البيانات بنجاح!', 'success')
        return redirect(url_for('view_permit', uuid=permit.uuid))
    return render_template('permit_form.html', permit=permit)

@app.route('/permit/<uuid>/delete', methods=['POST'])
@login_required
def delete_permit(uuid):
    permit = Permit.query.filter_by(uuid=uuid).first_or_404()
    
    # Delete physical files
    if permit.photo_path:
        photo_full_path = os.path.join(app.config['UPLOAD_FOLDER'], permit.photo_path)
        if os.path.exists(photo_full_path):
            os.remove(photo_full_path)
    
    if permit.qr_path:
        qr_full_path = os.path.join(app.config['QR_FOLDER'], permit.qr_path)
        if os.path.exists(qr_full_path):
            os.remove(qr_full_path)

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
        if photo_file and not allowed_file(photo_file.filename):
            flash('نوع الملف غير مسموح به. يرجى رفع صورة فقط.')
            return render_template('certificate_form.html', cert=cert)

        photo_filename, qr_filename = save_photo_and_qr(photo_file, cert.uuid)
        cert.photo_path = photo_filename
        cert.qr_path = qr_filename
        
        db.session.commit()
        flash('تم إصدار الشهادة بنجاح!', 'success')
        return redirect(url_for('view_certificate', uuid=cert.uuid))
    return render_template('certificate_form.html')

@app.route('/certificate/<uuid>/edit', methods=['GET', 'POST'])
@login_required
def edit_certificate(uuid):
    cert = HealthCertificate.query.filter_by(uuid=uuid).first_or_404()
    if request.method == 'POST':
        cert.cert_type = int(request.form.get('cert_type'))
        cert.cert_number = request.form.get('cert_number')
        cert.name = request.form.get('name')
        cert.id_number = request.form.get('id_number')
        cert.gender = request.form.get('gender')
        cert.nationality = request.form.get('nationality')
        cert.profession = request.form.get('profession')
        cert.issue_date = request.form.get('issue_date')
        cert.expiry_date = request.form.get('expiry_date')
        cert.edu_program_type = request.form.get('edu_program_type')
        cert.edu_program_expiry = request.form.get('edu_program_expiry')
        cert.place_of_issue = request.form.get('place_of_issue')
        
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename != '':
            if not allowed_file(photo_file.filename):
                flash('نوع الملف غير مسموح به.')
                return render_template('certificate_form.html', cert=cert)
            photo_filename, qr_filename = save_photo_and_qr(photo_file, cert.uuid)
            cert.photo_path = photo_filename
            
        db.session.commit()
        flash('تم التحديث بنجاح!', 'success')
        return redirect(url_for('view_certificate', uuid=cert.uuid))
    return render_template('certificate_form.html', cert=cert)

@app.route('/certificate/<uuid>/delete', methods=['POST'])
@login_required
def delete_certificate(uuid):
    cert = HealthCertificate.query.filter_by(uuid=uuid).first_or_404()
    
    # Delete physical files
    if cert.photo_path:
        photo_full_path = os.path.join(app.config['UPLOAD_FOLDER'], cert.photo_path)
        if os.path.exists(photo_full_path):
            os.remove(photo_full_path)
    
    if cert.qr_path:
        qr_full_path = os.path.join(app.config['QR_FOLDER'], cert.qr_path)
        if os.path.exists(qr_full_path):
            os.remove(qr_full_path)

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

with app.app_context():
    db.create_all()
    # Automatic DB migration
    try:
        import sqlite3
        db_path = os.path.join(app.instance_path, 'database.db')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(permit)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'dob' not in cols:
                cursor.execute("ALTER TABLE permit ADD COLUMN dob VARCHAR(20)")
                conn.commit()
            conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

    if not Admin.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = Admin(username='admin', password=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    lan_ip = get_lan_ip()
    print(f"\n{'='*55}")
    print(f"  ✅ السيرفر شغّال بنجاح!")
    print(f"  🖥️  من جهازك  : http://localhost:{PORT}")
    print(f"  📱 من الهاتف  : http://{lan_ip}:{PORT}")
    print(f"{'='*55}\n")
    
    app.run(host='0.0.0.0', port=PORT)

