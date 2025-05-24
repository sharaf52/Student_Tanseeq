from flask import Flask, render_template, request, redirect, url_for, flash, send_file, json ,jsonify ,session
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
import io
import arabic_reshaper
from flask import send_file
import pandas as pd
import os
import pymysql
from flask import Response
from bidi.algorithm import get_display
import arabic_reshaper
import logging
import openpyxl
from datetime import datetime
# Route لإنشاء وطباعة PDF يدعم العربية
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from flask import send_file
import io
app = Flask(__name__)
app.secret_key = "secret123"
# إعداد الاتصال بقاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/student_tanseeq'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# تعريف جدول الطلاب
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    national_id = db.Column(db.String(14), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    certificate_type = db.Column(db.String(50), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    division = db.Column(db.String(50), nullable=False)
    choices = db.Column(db.String(255), nullable=False)
# تعريف جدول التوايخ
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
# تعريف جدول الادمن
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='admin')
    can_upload_excel = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=False)
    can_upload_results = db.Column(db.Boolean, default=False)
    can_delete_all_students = db.Column(db.Boolean, default=False)
    can_edit_limits = db.Column(db.Boolean, default=False)
    can_manage_dates = db.Column(db.Boolean, default=False)
    can_manage_permissions = db.Column(db.Boolean, default=False)
    can_edit_student = db.Column(db.Boolean, default=False)
    can_print_student = db.Column(db.Boolean, default=False)
    can_delete_student = db.Column(db.Boolean, default=False)
# إنشاء قاعدة البيانات والجداول
with app.app_context():
    db.create_all()
# دالة لتنسيق النصوص العربية
def fix_arabic(text):
    return get_display(arabic_reshaper.reshape(text))
# تسجيل الخط العربي
pdfmetrics.registerFont(TTFont('ArabicFont', 'static/SHARAF1.ttf'))
# الصفحة الرئيسيه
@app.route('/')
def home():
    return render_template('index.html')
#رفع البيانات من ملف الاكسل
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    try:
        file = request.files['excel_file']
        if not file:
            flash("❌ لم يتم اختيار ملف!", "danger")
            return redirect(url_for('admin_dashboard'))

        df = pd.read_excel(file)

        required_columns = ['name', 'national_id', 'certificate_type', 'total_score', 'percentage', 'division']
        if not all(col in df.columns for col in required_columns):
            flash("❌ تأكد من أن الملف يحتوي على الأعمدة المطلوبة!", "danger")
            return redirect(url_for('admin_dashboard'))

        count = 0
        for _, row in df.iterrows():
            national_id = str(row['national_id']).strip()
            if not Student.query.filter_by(national_id=national_id).first():
                student = Student(
                    name=row['name'],
                    national_id=national_id,
                    certificate_type=row['certificate_type'],
                    total_score=row['total_score'],
                    percentage=row['percentage'],
                    division=row['division'],
                    phone="",           # الهاتف فارغ
                    choices=""          # الرغبات لسه الطالب هيختارها
                )
                db.session.add(student)
                count += 1

        db.session.commit()
        flash(f"✅ تم رفع {count} طالب بنجاح!", "success")
    except Exception as e:
        db.session.rollback()
        flash("❌ حدث خطأ أثناء رفع البيانات!", "danger")
    return redirect(url_for('super_admin_dashboard'))
#فريق العمل
@app.route('/team')
def team():
    return render_template('team.html')

#اضافة التواريخ
@app.route('/settings', methods=['GET', 'POST'])
def update_settings():
    settings = Settings.query.first()

    if request.method == 'POST':
        try:
            # التحقق من وجود البيانات المطلوبة
            if not request.form.get('start_date') or not request.form.get('end_date'):
                flash("❌ يرجى إدخال تاريخ البداية والنهاية", "danger")
                return redirect(url_for('update_settings'))

            # تحويل التواريخ مع التحقق من الصحة
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

            # التحقق من أن تاريخ البداية قبل النهاية
            if start_date >= end_date:
                flash("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية", "danger")
                return redirect(url_for('update_settings'))

            if settings:
                settings.start_date = start_date
                settings.end_date = end_date
            else:
                settings = Settings(start_date=start_date, end_date=end_date)
                db.session.add(settings)

            db.session.commit()
            flash("✅ تم حفظ التواريخ بنجاح", "success")

        except ValueError:
            flash("❌ تنسيق التاريخ غير صحيح. يرجى استخدام الصيغة YYYY-MM-DD", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ حدث خطأ أثناء حفظ التواريخ: {str(e)}", "danger")

        return redirect(url_for('update_settings'))

    # عرض الصفحة مع التواريخ الحالية
    return render_template('settings.html', settings=settings)
#استعلام عن القبول في الكلية
@app.route('/check_id', methods=['GET', 'POST'])
def check_student_id():
    if request.method == 'POST':
        national_id = request.form['national_id'].strip()
        student = Student.query.filter_by(national_id=national_id).first()

        if not student:
            flash("⚠️ الرقم القومي غير مسجل في قاعدة البيانات!", "danger")
            return redirect(url_for('check_student_id'))  # إعادة التوجيه إلى نفس الصفحة لإعادة إدخال الرقم القومي

        # التحقق من الفترة الزمنية أولاً
        settings = Settings.query.first()
        today = datetime.now()

        if not settings:
            return render_template("not_allowed.html",
                                   message="⛔ الفترة الزمنية غير محددة بعد، يرجى التواصل مع الإدارة")

        if today < settings.start_date:
            return render_template("not_allowed.html",
                                   message=f"⏳ تسجيل الرغبات سيبدأ في {settings.start_date.strftime('%Y-%m-%d')}")

        if today > settings.end_date:
            return render_template("not_allowed.html",
                                   message=f"⌛ انتهت فترة تسجيل الرغبات في {settings.end_date.strftime('%Y-%m-%d')}")

        # إذا كانت الفترة مناسبة، تحقق من حالة الطالب
        if student.choices:
            # إذا كانت الرغبات غير فارغة، التوجيه لصفحة "تم التسجيل من قبل"
            return render_template('already_registered.html', student=student)

        # إذا كانت الرغبات فارغة، التوجيه إلى صفحة التسجيل
        return render_template('register.html', student=student)

    return render_template('check_id.html')
@app.route('/register_dates/<national_id>', methods=['GET', 'POST'])
def register_dates(national_id):
    settings = Settings.query.first()
    today = datetime.now()

    if not settings:
        return render_template("not_allowed.html",
                               message="الفترة غير محددة بعد، يرجى الرجوع للإدارة")

    if today < settings.start_date:
        return render_template("not_allowed.html",
                               message=f"تسجيل الرغبات سيبدأ في {settings.start_date.strftime('%Y-%m-%d')}")

    if today > settings.end_date:
        return render_template("not_allowed.html",
                               message=f"انتهت فترة تسجيل الرغبات في {settings.end_date.strftime('%Y-%m-%d')}")

    return render_template("register.html", national_id=national_id)
# صفحة تسجيل الطالب
@app.route('/register/<national_id>', methods=['GET', 'POST'])
def register_student(national_id):
    student = Student.query.filter_by(national_id=national_id).first()
    if not student:
        flash("❌ الطالب غير موجود في قاعدة البيانات!", "danger")
        return redirect(url_for('home'))
    if request.method == 'POST':
        try:
            phone = request.form['phone'].strip()
            selected_choices = request.form.getlist('choices')
            # التحقق من عدد الرغبات
            if len(selected_choices) != 5:
                flash("⚠️ يجب اختيار 5 رغبات فقط!", "danger")
                return redirect(url_for('register_student', national_id=national_id))
            # تنظيف الرغبات وإزالة الفراغات
            choices_str = ', '.join([choice.strip() for choice in selected_choices if choice.strip()])
            # تحديث بيانات الطالب
            student.phone = phone
            student.choices = choices_str
            db.session.commit()
            return redirect(url_for('registration_success',
                                    name=student.name,
                                    national_id=student.national_id,
                                    phone=student.phone,
                                    certificate_type=student.certificate_type,
                                    total_score=student.total_score,
                                    percentage=student.percentage,
                                    division=student.division,
                                    choices=choices_str.split(',')))
        except Exception as e:
            db.session.rollback()
            flash("❌ فشل التحديث، حاول مرة أخرى!", "danger")
    return render_template('register.html', student=student)

@app.route('/success', methods=['GET', 'POST'])
def registration_success():
    name = request.args.get('name')
    national_id = request.args.get('national_id')
    phone = request.args.get('phone')
    certificate_type = request.args.get('certificate_type')
    total_score = request.args.get('total_score')
    percentage = request.args.get('percentage')
    division = request.args.get('division')
    choices = request.args.getlist('choices')
    # إنشاء كائن student وهمي
    student = Student(
        name=name,
        national_id=national_id,
        phone=phone,
        certificate_type=certificate_type,
        total_score=total_score,
        percentage=percentage,
        division=division,
        choices=choices
    )
    return render_template('success.html', student=student)

# صفحة تسجيل دخول الأدمن
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # تأكد إنك بتستخدم تشفير للكلمة السرية لو استخدمت hash
        admin = Admin.query.filter_by(username=username, password=password).first()

        if admin:
            session['admin_id'] = admin.id
            session['username'] = admin.username
            session['role'] = admin.role

            session['permissions'] = {
                'can_upload_excel': admin.can_upload_excel,
                'can_export': admin.can_export,
                'can_upload_results': admin.can_upload_results,
                'can_delete_all_students': admin.can_delete_all_students,
                'can_edit_limits': admin.can_edit_limits,
                'can_manage_dates': admin.can_manage_dates,

                # الصلاحيات الجديدة:
                'can_manage_permissions': admin.can_manage_permissions,
                'can_edit_student': admin.can_edit_student,
                'can_print_student': admin.can_print_student,
                'can_delete_student': admin.can_delete_student
            }

            return redirect(url_for('super_admin_dashboard'))  # أو أي صفحة رئيسية عندك
        else:
            flash("بيانات الدخول غير صحيحة", "danger")

    return render_template("login.html")
# --- إدارة الأدمنات ---
@app.route('/manage_permissions')
def manage_permissions():
    if not session.get('permissions', {}).get('can_manage_permissions'):
        flash("❌ ليس لديك صلاحية الوصول", "danger")
        return redirect(url_for('super_admin_dashboard'))

    admins = Admin.query.all()
    return render_template("manage_permissions.html", admins=admins)

@app.route('/admin/edit/<int:admin_id>', methods=['GET', 'POST'])
def edit_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)

    if request.method == 'POST':
        # تعديل الاسم
        new_username = request.form['username']
        if new_username != admin.username:
            existing_admin = Admin.query.filter_by(username=new_username).first()
            if existing_admin:
                flash("⚠️ اسم المستخدم موجود بالفعل", "danger")
                return redirect(url_for('edit_admin', admin_id=admin_id))
            admin.username = new_username

        # تعديل الباسورد (فقط لو المستخدم كتب باسورد جديد)
        new_password = request.form['password']
        if new_password:
            admin.password = new_password  # يفضل تشفيره قبل الحفظ

        # تعديل الصلاحيات
        admin.can_upload_excel = 'can_upload_excel' in request.form
        admin.can_export = 'can_export' in request.form
        admin.can_upload_results = 'can_upload_results' in request.form
        admin.can_delete_all_students = 'can_delete_all_students' in request.form
        admin.can_edit_limits = 'can_edit_limits' in request.form
        admin.can_manage_dates = 'can_manage_dates' in request.form
        admin.can_manage_permissions = 'can_manage_permissions' in request.form
        admin.can_edit_student = 'can_edit_student' in request.form
        admin.can_delete_student = 'can_delete_student' in request.form
        admin.can_print_student = 'can_print_student' in request.form

        db.session.commit()
        flash("✅ تم تعديل بيانات الأدمن", "success")
        return redirect(url_for('manage_permissions'))

    return render_template("edit_admin.html", admin=admin)

@app.route('/admin/delete/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    db.session.delete(admin)
    db.session.commit()
    flash("🗑️ تم حذف الأدمن", "success")
    return redirect(url_for('manage_permissions'))

@app.route('/admin/add', methods=['GET', 'POST'])
def add_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # يفضل تشفيره

        if Admin.query.filter_by(username=username).first():
            flash("⚠️ هذا المستخدم موجود بالفعل", "danger")
            return redirect(url_for('add_admin'))

        new_admin = Admin(
            username=username,
            password=password,
            can_upload_excel='can_upload_excel' in request.form,
            can_export='can_export' in request.form,
            can_upload_results='can_upload_results' in request.form,
            can_delete_all_students='can_delete_all_students' in request.form,
            can_edit_limits='can_edit_limits' in request.form,
            can_manage_dates='can_manage_dates' in request.form,
            can_manage_permissions='can_manage_permissions' in request.form,
            can_edit_student='can_edit_student' in request.form,
            can_delete_student='can_delete_student' in request.form,
            can_print_student='can_print_student' in request.form,
        )
        db.session.add(new_admin)
        db.session.commit()
        flash("✅ تم إضافة الأدمن", "success")
        return redirect(url_for('manage_permissions'))

    permission_fields = [
        'can_upload_excel',
        'can_export',
        'can_upload_results',
        'can_delete_all_students',
        'can_edit_limits',
        'can_manage_dates',
        'can_manage_permissions',
        'can_edit_student',
        'can_delete_student',
        'can_print_student'
    ]

    permission_labels = {
        'can_upload_excel': '📥 رفع إكسل',
        'can_export': '📂 تصدير',
        'can_upload_results': '📤 رفع النتائج',
        'can_delete_all_students': '🧹 حذف كل الطلاب',
        'can_edit_limits': '📊 تعديل الحدود',
        'can_manage_dates': '📅 إدارة التواريخ',
        'can_manage_permissions': '🛠️ إدارة الصلاحيات',
        'can_edit_student': '✏️ تعديل بيانات طالب',
        'can_delete_student': '🗑️ حذف طالب',
        'can_print_student': '🖨️ طباعة بيانات طالب'
    }

    return render_template("add_admin.html", permission_fields=permission_fields, permission_labels=permission_labels)
# صفحة لوحة تحكم الأدمن الرئيسي
@app.route('/super_admin_dashboard')
def super_admin_dashboard():
    students = Student.query.all()  # جلب كل بيانات الطلاب
    return render_template('super_admin.html', students=students)
# حذف
@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash("تم حذف الطالب بنجاح", "success")
    return redirect(url_for('super_admin_dashboard'))
# طباعه
@app.route('/print_student/<int:student_id>')
def print_student(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('print_student.html', student=student)
# تعديل
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        student.name = request.form['name']
        student.national_id = request.form['national_id']
        student.phone = request.form['phone']
        student.certificate_type = request.form['certificate_type']
        student.total_score = request.form['total_score']
        student.percentage = request.form['percentage']
        student.division = request.form['division']
        student.choices = request.form['choices']
        db.session.commit()
        flash("تم تحديث بيانات الطالب بنجاح!", "success")
        return redirect(url_for('super_admin_dashboard'))
    return render_template('edit_student.html', student=student)
# البحث بالرقم القومي
@app.route('/search_student', methods=['POST'])
def search_student():
    national_id = request.form.get("national_id")
    student = Student.query.filter_by(national_id=national_id).first()

    if student:
        return render_template('super_admin.html', students=[student])  # عرض الطالب فقط
    else:
        flash("⚠️ الرقم القومي غير مسجل!", "danger")
        return render_template('super_admin.html')  # الرجوع لنفس الصفحة مع عرض الرسالة
# ملف الاكسل
@app.route('/export_students')
def export_students():
    students = Student.query.all()

    if not students:
        flash("⚠️ لا يوجد بيانات لتصديرها!", "warning")
        return redirect(url_for('super_admin_dashboard'))  # ✅ تأكد إنك بترجع رد فعل

    # تحويل البيانات إلى DataFrame مع فصل الرغبات
    data = []
    for student in students:
        choices = student.choices.split(',')
        choices += [""] * (5 - len(choices))  # ملء الفراغات في حال كانت أقل من 5 رغبات

        data.append({
            "الاسم": student.name,
            "الرقم القومي": student.national_id,
            "الهاتف": student.phone,
            "نوع الشهادة": student.certificate_type,
            "المجموع": student.total_score,
            "النسبة المئوية": student.percentage,
            "الشعبة": student.division,
            "الرغبة 1": choices[0],
            "الرغبة 2": choices[1],
            "الرغبة 3": choices[2],
            "الرغبة 4": choices[3],
            "الرغبة 5": choices[4]
        })

    df = pd.DataFrame(data)

    # تأكد من وجود مجلد exports
    os.makedirs("exports", exist_ok=True)

    # مسار حفظ الملف
    file_path = os.path.join("exports", "students_data.xlsx")

    # حفظ الملف
    df.to_excel(file_path, index=False, engine='openpyxl')

    # التحقق من وجود الملف قبل إرساله
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name="students_data.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        flash("❌ فشل تصدير الملف، الملف غير موجود!", "danger")
        return redirect(url_for('super_admin_dashboard'))

    @app.route('/')
    def home():
        return render_template('index.html')

@app.route('/delete_all_students', methods=['POST'])
def delete_all_students():
    try:
        num_rows_deleted = db.session.query(Student).delete()
        db.session.commit()
        flash(f"تم حذف جميع الطلاب ({num_rows_deleted}) بنجاح ✅", "success")
    except:
        db.session.rollback()
        flash("❌ حدث خطأ أثناء حذف الطلاب!", "danger")
    return redirect(url_for('super_admin_dashboard'))
# الحدود الدنيا
import os
LIMITS_FILE = "limits.json"
# تحميل الحدود الدنيا من الملف
def load_limits():
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}
# حفظ الحدود الدنيا في الملف
def save_limits(limits):
    with open(LIMITS_FILE, "w", encoding="utf-8") as file:
        json.dump(limits, file, ensure_ascii=False, indent=4)
# صفحة إدارة الحدود الدنيا
@app.route("/manage_limits")
def manage_limits():
    limits = load_limits()
    return render_template("limits.html", limits=limits)
# API لحفظ الحدود الدنيا
@app.route("/save_limits", methods=["POST"])
def save_limits_api():
    data = request.json
    save_limits(data)
    return json({"message": "تم حفظ الحدود الدنيا بنجاح!"})

@app.route("/distribute_students", methods=["POST"])
def distribute_students():
    try:
        # تحميل الحدود الدنيا من ملف JSON
        limits = load_limits()
        if not limits:
            return jsonify({
                "status": "error",
                "message": "ملف الحدود الدنيا (limits.json) غير موجود أو فارغ"
            }), 400

        logging.info("\n📂 تحميل الحدود الدنيا:")
        logging.info(limits)

        # جلب بيانات الطلاب من قاعدة البيانات
        students = Student.query.all()
        if not students:
            return jsonify({
                "status": "error",
                "message": "❌ لا يوجد طلاب مسجلين في النظام"
            }), 400

        results = {
            "total": len(students),
            "assigned": 0,
            "not_assigned": 0,
            "assignments": []
        }

        for student in students:
            assigned_department = None
            status = "لم يتم القبول"
            choices = [choice.strip() for choice in student.choices.split(',') if choice.strip()]
            student_division = student.division.strip()

            logging.info(f"\n🔍 طالب: {student.name} - المجموع: {student.total_score} - الشعبة: {student_division}")
            logging.info(f"📌 رغباته: {choices}")

            for choice in choices:
                if choice in limits:
                    matched_division = next(
                        (key for key in limits[choice].keys() if key.strip() == student_division),
                        None
                    )

                    if matched_division:
                        try:
                            min_score = float(limits[choice][matched_division])
                            student_score = float(student.total_score)

                            logging.info(f"🔹 فحص الرغبة: {choice} | الحد الأدنى: {min_score} | مجموع الطالب: {student_score}")

                            if student_score >= min_score:
                                assigned_department = choice
                                status = "تم التوزيع"
                                logging.info(f"✅ الطالب قُبل في: {assigned_department}")
                                break

                        except (ValueError, TypeError) as e:
                            logging.error(f"⚠️ خطأ في قراءة الحدود الدنيا للرغبة: {choice} | خطأ: {e}")
                            continue

            if assigned_department:
                results["assigned"] += 1
            else:
                results["not_assigned"] += 1

            results["assignments"].append({
                "name": student.name,
                "national_id": student.national_id,
                "score": student.total_score,
                "division": student_division,
                "assigned": assigned_department if assigned_department else "❌ لم يتم القبول",
                "status": status,
                "choices": ", ".join(choices) if choices else "لا توجد رغبات"
            })

        return jsonify({
            "status": "success",
            "message": f"تم توزيع {results['assigned']} من أصل {results['total']} طالب",
            "results": results
        })

    except Exception as e:
        logging.error(f"❌ خطأ غير متوقع أثناء التوزيع: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"❌ خطأ غير متوقع أثناء التوزيع: {str(e)}",
            "error_type": e.__class__.__name__
        }), 500

@app.route("/download_student_choices", methods=["GET"])
def download_student_choices():
    try:
        # جلب بيانات الطلاب من قاعدة البيانات
        students = Student.query.all()
        if not students:
            return json({
                "status": "error",
                "message": "❌ لا يوجد طلاب مسجلين في النظام"
            }), 400

        # إنشاء ملف Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "نتائج التوزيع"

        # إضافة رؤوس الأعمدة
        ws.append([
            "ID", "الاسم", "الرقم القومي", "رقم الهاتف", "نوع الشهادة",
            "المجموع", "النسبة المئوية", "الشعبة", "الرغبة التي تم القبول فيها"
        ])

        # إضافة بيانات الطلاب مع ترقيم تلقائي
        for index, student in enumerate(students, start=1):
            assigned_department = None
            choices = [choice.strip() for choice in student.choices.split(',') if choice.strip()]
            student_division = student.division  # الشعبة

            for choice in choices:
                # التأكد من مطابقة الرغبة مع الحد الأدنى
                min_score = get_min_score_for_choice(choice, student_division)
                if min_score and student.total_score >= min_score:
                    assigned_department = choice
                    break  # بمجرد القبول، يخرج من الحلقة

            # إذا لم يتم تعيين الطالب في أي رغبة
            if not assigned_department and choices:
                assigned_department = choices[-1]  # آخر رغبة للطالب

            # إضافة بيانات الطالب إلى الملف
            ws.append([
                index,  # ترقيم تلقائي يبدأ من 1
                student.name,
                student.national_id,
                student.phone,
                student.certificate_type,
                student.total_score,
                student.percentage,
                student.division,
                assigned_department  # الرغبة التي تم القبول فيها فقط
            ])

        # حفظ الملف في مجلد مؤقت
        file_path = "students_choices_result.xlsx"
        wb.save(file_path)

        # إرسال الملف للمستخدم
        return send_file(file_path, as_attachment=True, download_name="نتائج_رغبات_الطلاب.xlsx")

    except Exception as e:
        return json({
            "status": "error",
            "message": f"❌ حدث خطأ أثناء إنشاء ملف Excel: {str(e)}",
        }), 500

def get_min_score_for_choice(choice, division):
    # هنا نحتاج لجلب الحد الأدنى للرغبة بناءً على الشعبة
    limits = load_limits()  # تحميل الحدود الدنيا
    if choice in limits and division in limits[choice]:
        try:
            return float(limits[choice][division])
        except ValueError:
            return None
    return None

@app.route("/upload_results", methods=["POST"])
def upload_results():
    try:
        # جلب جميع الطلاب من قاعدة البيانات
        students = Student.query.all()
        if not students:
            return json({
                "status": "error",
                "message": "❌ لا يوجد طلاب مسجلين في النظام"
            }), 400

        # تحديث بيانات الطلاب بحذف الرغبات وإضافة الرغبة المقبول بها فقط
        for student in students:
            assigned_department = None
            choices = [choice.strip() for choice in student.choices.split(',') if choice.strip()]
            student_division = student.division  # الشعبة الخاصة بالطالب

            for choice in choices:
                # جلب الحد الأدنى للمجموع لهذه الرغبة
                min_score = get_min_score_for_choice(choice, student_division)
                if min_score and student.total_score >= min_score:
                    assigned_department = choice
                    break  # بمجرد القبول، يخرج من الحلقة

            # إذا لم يتم تعيين الطالب في أي رغبة، نضع له آخر رغبة
            if not assigned_department and choices:
                assigned_department = choices[-1]

            # تحديث قاعدة البيانات بحذف جميع الرغبات والاحتفاظ بالرغبة النهائية فقط
            student.choices = assigned_department  # تحديث الحقل بالرغبة المقبولة فقط

        # حفظ التعديلات في قاعدة البيانات
        db.session.commit()

        return json({
            "status": "success",
            "message": "✅ تم تحديث نتائج الرغبات بنجاح!"
        })

    except Exception as e:
        return json({
            "status": "error",
            "message": f"❌ حدث خطأ أثناء تحديث النتائج: {str(e)}",
        }), 500

def get_min_score_for_choice(choice, division):
    # هنا نحتاج لجلب الحد الأدنى للرغبة بناءً على الشعبة
    limits = load_limits()  # تحميل الحدود الدنيا من قاعدة البيانات أو ملف خارجي
    if choice in limits and division in limits[choice]:
        try:
            return float(limits[choice][division])
        except ValueError:
            return None
    return None

# التأكد من أن الخط SHARAF موجود في مجلد static
@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # تسجيل الخط العربي
    pdfmetrics.registerFont(TTFont('SHARAF', 'static/Air-Strip-Arabic.ttf'))

    # استرجاع بيانات الطالب
    national_id = request.form.get("national_id", "غير متوفر")
    student = Student.query.filter_by(national_id=national_id).first()
    if not student:
        return "❌ الطالب غير موجود في النظام!", 400

    # استرجاع الرغبات من قاعدة البيانات
    choices = student.choices.split(',') if student.choices else []
    choices = [choice.strip() for choice in choices if choice.strip()]  # تنظيف البيانات

    # إعداد PDF في الذاكرة
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # إضافة خلفية صورة مع شفافية
    def draw_watermark(pdf):
        image_path = "static/logo_watermark.png"
        pdf.setFillAlpha(0.1)  # تحديد الشفافية للصورة الخلفية فقط
        pdf.drawImage(image_path, 50, 200, width=500, height=500)  # ضبط الموقع وحجم الصورة

    draw_watermark(pdf)  # إضافة الصورة كخلفية

    # إعداد الخط المخصص
    pdf.setFont("SHARAF", 12)  # تحديد الخط SHARAF

    # مستطيل الإطار العام
    pdf.setStrokeColorRGB(0.2, 0.2, 0.2)
    pdf.setLineWidth(1.5)
    pdf.rect(30, 30, width - 60, height - 60)

    # الشعارين بدون شفافية
    pdf.setFillAlpha(1)  # إزالة الشفافية
    pdf.drawImage('static/image-right.jpg', 50, height - 120, width=90, height=80)
    pdf.drawImage('static/image-left.jpg', width - 135, height - 120, width=80, height=80)

    # بيانات المؤسسة (تأكد من أن النصوص واضحة)
    pdf.setFont("SHARAF", 11)
    pdf.drawRightString(width - 55, height - 135, fix_arabic("جامعة كفر الشيخ"))
    pdf.drawRightString(width - 55, height - 155, fix_arabic("كلية التربية النوعية"))
    pdf.line(40, height - 170, width - 40, height - 170)

    # عنوان التقرير
    pdf.setFont("SHARAF", 16)
    title = fix_arabic("استمارة تسجيل الرغبات")
    title_width = pdf.stringWidth(title, "SHARAF", 16)
    pdf.drawString((width - title_width) / 2, height - 200, title)

    # بيانات الطالب (تأكد من أن النصوص واضحة)
    pdf.setFont("SHARAF", 12)
    y = height - 240
    spacing = 25
    info = [
        ("الاسم", student.name),
        ("الرقم القومي", student.national_id),
        ("رقم الهاتف", student.phone),
        ("نوع الشهادة", student.certificate_type),
        ("المجموع الكلي", student.total_score),
        ("النسبة المئوية", f"{student.percentage}%"),
        ("الشعبة", student.division)
    ]
    for label, value in info:
        text = fix_arabic(f"{label}: {value}")
        pdf.drawRightString(width - 50, y, text)
        y -= spacing

    # عنوان الرغبات
    y -= 10
    pdf.line(50, y, width - 50, y)
    y -= spacing
    pdf.setFont("SHARAF", 14)
    raghbat = fix_arabic("الرغبات المختارة")
    pdf.drawString((width - pdf.stringWidth(raghbat, "SHARAF", 14)) / 2, y, raghbat)
    y -= spacing

    # تحضير بيانات الجدول
    table_data = [[fix_arabic("الرغبة"), fix_arabic("م")]]
    for i, choice in enumerate(choices, 1):
        table_data.append([fix_arabic(choice), str(i)])

    # إعداد الجدول
    table = Table(table_data, colWidths=[width - 180, 50])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'SHARAF'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    # تلوين الصفوف بالتبادل
    for row_num in range(1, len(table_data)):
        bg_color = colors.whitesmoke if row_num % 2 == 0 else colors.lightgrey
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, row_num), (-1, row_num), bg_color),
        ]))

    # رسم الجدول
    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, 70, y - (len(table_data) * 20))
    # إضافة كلمة "توقيع الطالب" مع النقاط على اليسار
    y_signature = y - (len(table_data) * 20) - 20  # تحديد الموقع تحت الجدول
    pdf.setFont("SHARAF", 12)

    # إضافة النقاط أولاً ثم كلمة "توقيع الطالب" على اليسار
    y_signature = y - (len(table_data) * 20) - 20  # تحديد الموقع تحت الجدول
    pdf.setFont("SHARAF", 12)

    # إضافة النقاط على اليسار أولاً
    pdf.drawString(50, y_signature, ".............................")

    # إضافة كلمة "توقيع الطالب" بعد النقاط
    signature_text = fix_arabic("توقيع الطالب:")
    pdf.drawString(50 + pdf.stringWidth(".............................", "SHARAF", 12) + 5, y_signature, signature_text)

    # ملاحظات في النهاية
    y_note = 70
    pdf.setFont("SHARAF", 9)
    note1 = fix_arabic("ملحوظة: يجب علي طباعة هذا التقرير وتسليمة في الكلية لشئون الطلاب")
    note2 = fix_arabic("تأكد من الاختيارات قبل الإرسال.")
    pdf.drawCentredString(width / 2, y_note, note1)
    pdf.drawCentredString(width / 2, y_note - 15, note2)

    # حفظ وتحميل الملف
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Student_Report.pdf", mimetype="application/pdf")

@app.route('/inquiry', methods=['GET', 'POST'])
def inquiry():
    if request.method == 'POST':
        national_id = request.form['national_id']
        student = Student.query.filter_by(national_id=national_id).first()

        if student:
            choices_list = student.choices.split(',')  # تحويل الرغبات إلى List

            if len(choices_list) == 5:
                return render_template('inquiry.html', error="لم يتم رفع نتيجة الرغبات.")
            elif len(choices_list) == 1:
                return render_template('inquiry.html', result=student, single_choice=choices_list[0])
            else:
                return render_template('inquiry.html', result=student)

        return render_template('inquiry.html', error="الرقم القومي غير موجود في النظام.")

    return render_template('inquiry.html')

@app.route('/print_pdf/<national_id>', methods=['POST'])
def print_pdf(national_id):
    student = Student.query.filter_by(national_id=national_id).first()
    if student:
        # إنشاء ملف PDF في الذاكرة
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # رسم إطار حول الصفحة
        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(2)
        pdf.rect(30, 30, A4[0] - 60, A4[1] - 60)

        # إضافة الصور داخل الإطار
        image_top_position = A4[1] - 120
        pdf.drawImage('static/image-right.jpg', 50, image_top_position, width=100, height=80)
        pdf.drawImage('static/image-left.jpg', A4[0] - 130, image_top_position, width=80, height=80)

        # إضافة العناوين
        pdf.setFont("ArabicFont", 10)
        pdf.drawRightString(A4[0] - 59, image_top_position - 25, fix_arabic("جامعة كفر الشيخ"))
        pdf.drawRightString(A4[0] - 55, image_top_position - 45, fix_arabic("كلية التربية النوعية"))

        # إضافة الخط الأسود
        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(1)
        pdf.line(40, image_top_position - 65, A4[0] - 40, image_top_position - 65)

        # إضافة عنوان التقرير
        pdf.setFont("ArabicFont", 16)
        title = fix_arabic("نتيجة التنسيق الداخلي")
        title_width = pdf.stringWidth(title, "ArabicFont", 16)
        pdf.drawString((A4[0] - title_width) / 2, image_top_position - 85, title)

        # كتابة بيانات الطالب
        pdf.setFont("ArabicFont", 11)
        y_position = image_top_position - 120
        line_spacing = 30

        data = [
            ("• الاسم:", student.name),
            ("• الرقم القومي:", student.national_id),
            ("• رقم الهاتف:", student.phone),
            ("• نوع الشهادة:", student.certificate_type),
            ("• المجموع الكلي:", str(student.total_score)),
            ("• النسبة المئوية:", f"{student.percentage}%"),
            ("• الرغبة المقبول بها:", student.choices)
        ]

        for label, value in data:
            pdf.drawRightString(A4[0] - 50, y_position, fix_arabic(f"{label} {value}"))
            y_position -= line_spacing

        # إضافة الملاحظة
        pdf.setFont("ArabicFont", 9)
        note = fix_arabic("هذه النتيجة نهائية ولا يمكن تعديلها")
        note_width = pdf.stringWidth(note, "ArabicFont", 9)
        pdf.drawString((A4[0] - note_width)/2, 70, note)

        pdf.save()
        buffer.seek(0)

        return send_file(buffer,
                         as_attachment=True,
                         download_name=f"student_{student.national_id}_result.pdf",
                         mimetype="application/pdf")

    return redirect(url_for('inquiry'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
