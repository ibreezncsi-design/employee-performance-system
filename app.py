from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
from psycopg2.extras import DictCursor
import smtplib
from email.message import EmailMessage

# Cursor متوافق مع نمط الاستعلامات القديم في المشروع
class FluentDictCursor(DictCursor):
    def execute(self, query, vars=None):
        super().execute(query, vars)
        return self

from datetime import datetime
import pandas as pd
from flask import send_file

app = Flask(__name__)
ALLOWED_USERS = {
    "Huda@ncsi.gov.om": {
        "password": "Huda2026",
        "name": "هدى",
        "role": "user"
    },

    "aismaili@ncsi.gov.om": {
        "password": "Aismaili2026",
        "name": "أحلام",
        "role": "user"
    },

    "hbuloshi@ncsi.gov.om": {
        "password": "Hbuloshi2026",
        "name": "هود",
        "role": "user"
    },

    "Aisha.Rashid@ncsi.gov.om": {
        "password": "Aisha2026",
        "name": "عايشة",
        "role": "user"
    },

    "almuhannad@ncsi.gov.om": {
        "password": "Muhannad2026",
        "name": "مهند",
        "role": "user"
    },

    "B.Ghassani@ncsi.gov.om": {
        "password": "Ghassani2026",
        "name": "بلقيس",
        "role": "user"
    },

    "fbuloshi@ncsi.gov.om": {
        "password": "Fbuloshi2026",
        "name": "فاطمة",
        "role": "user"
    },

    "ibreez@ncsi.gov.om": {
        "password": "Admin2026!",
        "name": "إبريز",
        "role": "admin"
    },

    "mmsharfi@ncsi.gov.om": {
        "password": "Admin2026!",
        "name": "محفوظ",
        "role": "admin"
    }
}
app.secret_key = os.environ.get("SECRET_KEY", "employee_secret_key")


def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg2.connect(
        database_url,
        cursor_factory=FluentDictCursor
    )

def send_notification_email(to_email, message):

    try:
        email_address = os.environ.get("EMAIL_ADDRESS")
        email_password = os.environ.get("EMAIL_PASSWORD")

        system_url = "https://employee-performance-system-sse2.onrender.com"

        msg = EmailMessage()
        msg["Subject"] = "إشعار جديد - نظام قياس الأداء"
        msg["From"] = email_address
        msg["To"] = to_email

        msg.set_content(f"""
السلام عليكم ورحمة الله وبركاته،

لديك إشعار جديد في نظام قياس الأداء:

{message}

للدخول إلى النظام:
{system_url}

مع التحية،
نظام قياس الأداء
""")

        msg.add_alternative(f"""
        <html dir="rtl">
            <body style="font-family: Arial; text-align: right;">

                <p>السلام عليكم ورحمة الله وبركاته،</p>

                <p>لديك إشعار جديد في نظام قياس الأداء:</p>

                <h3>{message}</h3>

                <p>يمكنك الدخول إلى النظام لمتابعة التفاصيل:</p>

                <a href="{system_url}"
                   style="
                       background-color: #7c3aed;
                       color: white;
                       padding: 12px 25px;
                       text-decoration: none;
                       border-radius: 8px;
                       display: inline-block;
                   ">
                    الدخول إلى النظام
                </a>

                <br><br>

                <p>
                    مع التحية،<br>
                    نظام قياس الأداء
                </p>

            </body>
        </html>
        """, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(msg)

        print(f"EMAIL SENT TO: {to_email}")

    except Exception as e:
        print(f"EMAIL ERROR: {e}")

def add_notification(c, email, message, work_id=None, evaluation_id=None):

    if work_id:

        c.execute("""
            DELETE FROM notifications
            WHERE user_email = %s
            AND work_id = %s
        """, (
            email,
            work_id
        ))

    if evaluation_id:

        c.execute("""
            DELETE FROM notifications
            WHERE user_email = %s
            AND evaluation_id = %s
        """, (
            email,
            evaluation_id
        ))

    c.execute("""
        INSERT INTO notifications
        (
            user_email,
            message,
            work_id,
            evaluation_id,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        email,
        message,
        work_id,
        evaluation_id,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    send_notification_email(email, message)


def init_db():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS works(
        id SERIAL PRIMARY KEY,
        user_email TEXT,
        year INTEGER,
        period TEXT,
        work_type TEXT,
        work_details TEXT,
        start_date TEXT,
        end_date TEXT,
        actual_days INTEGER,
        target_days INTEGER,
        status TEXT DEFAULT 'pending',
        admin_note TEXT,
        approved_date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS evaluations(
        id SERIAL PRIMARY KEY,
        user_email TEXT,
        year INTEGER,
        period TEXT,
        quality INTEGER,
        teamwork INTEGER,
        continuity INTEGER,
        extra_work INTEGER,
        status TEXT DEFAULT 'pending',
        admin_note TEXT,
        approved_date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS weights(
        id SERIAL PRIMARY KEY,
        metric TEXT,
        year INTEGER,
        period TEXT,
        weight REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id SERIAL PRIMARY KEY,
        user_email TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT,
        work_id INTEGER,
        evaluation_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email in ALLOWED_USERS:

            user = ALLOWED_USERS[email]

            if password == user["password"]:

                session["email"] = email
                session["name"] = user["name"]
                session["role"] = user["role"]

                return redirect("/dashboard")

        error = "بيانات الدخول غير صحيحة"

    return render_template(
        "login.html",
        error=error
    )
@app.route("/works", methods=["GET", "POST"])
def works():

    if "email" not in session:
        return redirect("/")

    if session["role"] == "admin":
        return redirect("/admin")
    
    if request.method == "POST":

        print("POST WORKING")

        year = request.form["year"]
        period = request.form["period"]
        work_type = request.form["work_type"]
        work_details = request.form["work_details"]

        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        target_days = request.form.get("target_days")

        if not year or not period or not work_type or not work_details:
            return "جميع الحقول مطلوبة"

        if work_type in [
            "تقارير إلكترونية",
            "تقارير ورقية",
            "دراسة طلبات"
        ]:

            if not start_date or not end_date or not target_days:
                return "يرجى تعبئة التواريخ والأيام المحددة"
        
        actual_days = None

        if start_date and end_date:

            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            actual_days = (end - start).days + 1

        print(year)
        print(period)
        print(work_type)
        print(work_details)

        conn = get_db()
        c = conn.cursor()

        work_id = request.form.get("work_id")

        if work_id:

            c.execute("""
                UPDATE works
                SET
                    year = %s,
                    period = %s,
                    work_type = %s,
                    work_details = %s,
                    start_date = %s,
                    end_date = %s,
                    actual_days = %s,
                    target_days = %s,
                    status = 'pending',
                    admin_note = NULL
                WHERE id = %s
                AND user_email = %s
            """, (
                year,
                period,
                work_type,
                work_details,
                start_date,
                end_date,
                actual_days,
                target_days,
                work_id,
                session["email"]
            ))

            current_work_id = work_id
            action_message = f"✏️ قام {session['name']} بتعديل عمل"

            print("UPDATE DONE")

        else:

            c.execute("""
                    INSERT INTO works
                    (
                        user_email,
                        year,
                        period,
                        work_type,
                        work_details,
                        start_date,
                        end_date,
                        actual_days,
                        target_days,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
            """, (
                session["email"],
                year,
                period,
                work_type,
                work_details,
                start_date,
                end_date,
                actual_days,
                target_days,
                "pending"
            ))

            print("INSERT DONE")
            current_work_id = c.fetchone()["id"]
            action_message = f"📝 قام {session['name']} بإضافة عمل جديد"

        

        

        for email, info in ALLOWED_USERS.items():

            if info["role"] == "admin":

                add_notification(
                c,
                email,
                action_message,
                current_work_id
            )

        conn.commit()
        conn.close()


        return redirect("/works")

    # ==========================
    # جلب الأعمال للعرض
    # ==========================

    conn = get_db()
    c = conn.cursor()

    if session["role"] == "admin":

        rows = c.execute("""
            SELECT *
            FROM works
            ORDER BY id DESC
        """).fetchall()

    else:

        rows = c.execute("""
            SELECT *
            FROM works
            WHERE user_email = %s
            ORDER BY id DESC
        """, (
            session["email"],
        )).fetchall()


    notifications = c.execute("""
        SELECT *
        FROM notifications
        WHERE user_email = %s
        ORDER BY id DESC
    """, (
        session["email"],
    )).fetchall()

    unread_count = c.execute("""
    SELECT COUNT(*)
    FROM notifications
    WHERE user_email = %s
    AND is_read = 0
    """,(
        session["email"],
    )).fetchone()[0]

    conn.close()
    user_names = {}

    for email, info in ALLOWED_USERS.items():
        user_names[email] = info["name"]

    return render_template(
        "works.html",
        name=session["name"],
        notifications=notifications,
        unread_count=unread_count,
        works=rows,
        user_names=user_names
    )

@app.route("/dashboard")
def dashboard():

    if "email" not in session:
        return redirect("/")

    if session["role"] == "admin":
        return redirect("/admin")

    return redirect("/works")
@app.route("/evaluations", methods=["GET", "POST"])
def evaluations():

    if "email" not in session:
        return redirect("/")

    selected_employee = request.args.get("employee", "الكل")
    selected_period = request.args.get("period", "الكل")
    selected_status = request.args.get("status","الكل")

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":

        year = request.form["year"]
        period = request.form["period"]

        quality = request.form["quality"]
        teamwork = request.form["teamwork"]
        continuity = request.form["continuity"]
        extra_work = request.form["extra_work"]

        evaluation_id = request.form.get("evaluation_id")

        # =================================
        # تعديل تقييم
        # =================================
        if evaluation_id:

            c.execute("""
                UPDATE evaluations
                SET
                    year = %s,
                    period = %s,
                    quality = %s,
                    teamwork = %s,
                    continuity = %s,
                    extra_work = %s,
                    status = 'pending',
                    admin_note = NULL
                WHERE id = %s
                AND user_email = %s
            """, (
                year,
                period,
                quality,
                teamwork,
                continuity,
                extra_work,
                evaluation_id,
                session["email"]
            ))

            # إشعار للإدارة
            for email, info in ALLOWED_USERS.items():

                if info["role"] == "admin":

                    add_notification(
                        c,
                        email,
                        f"✏️ قام {session['name']} بتعديل تقييم",
                        evaluation_id=evaluation_id
                    )

        # =================================
        # إضافة تقييم جديد
        # =================================
        else:

            existing = c.execute("""
                SELECT id
                FROM evaluations
                WHERE user_email = %s
                AND year = %s
                AND period = %s
            """, (
                session["email"],
                year,
                period
            )).fetchone()

            if existing:
                conn.close()
                return "تم إدخال تقييم لهذه الفترة مسبقاً، يمكنك تعديله فقط."

            c.execute("""
                INSERT INTO evaluations
                (
                    user_email,
                    year,
                    period,
                    quality,
                    teamwork,
                    continuity,
                    extra_work,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                session["email"],
                year,
                period,
                quality,
                teamwork,
                continuity,
                extra_work,
                "pending"
            ))

            new_evaluation_id = c.fetchone()["id"]

            # إشعار للإدارة
            for email, info in ALLOWED_USERS.items():

                if info["role"] == "admin":

                    add_notification(
                        c,
                        email,
                        f"📝 قام {session['name']} بإضافة تقييم جديد",
                        evaluation_id=new_evaluation_id
                    )

        conn.commit()

        return redirect("/evaluations")

    # =================================
    # جلب التقييمات
    # =================================

    if session["role"] == "admin":

        query = """
        SELECT *
        FROM evaluations
        WHERE 1=1
        """

        params = []

        if selected_employee != "الكل":
            query += " AND user_email = %s"
            params.append(selected_employee)

        if selected_period != "الكل":
            query += " AND period = %s"
            params.append(selected_period)

        if selected_status != "الكل":
            query += " AND status = %s"
            params.append(selected_status)

        query += " ORDER BY id DESC"

        rows = c.execute(query, params).fetchall()

    else:

        rows = c.execute("""
            SELECT *
            FROM evaluations
            WHERE user_email = %s
            ORDER BY id DESC
        """, (
            session["email"],
        )).fetchall()

    # =================================
    # جلب الإشعارات
    # =================================

    notifications = c.execute("""
        SELECT *
        FROM notifications
        WHERE user_email = %s
        ORDER BY id DESC
    """, (
        session["email"],
    )).fetchall()

    unread_count = c.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_email = %s
        AND is_read = 0
    """, (
        session["email"],
    )).fetchone()[0]

    pending_count = c.execute("""
    SELECT COUNT(*)
    FROM evaluations
    WHERE status = 'pending'
    """).fetchone()[0]

    approved_count = c.execute("""
    SELECT COUNT(*)
    FROM evaluations
    WHERE status = 'approved'
    """).fetchone()[0]

    returned_count = c.execute("""
    SELECT COUNT(*)
    FROM evaluations
    WHERE status = 'returned'
    """).fetchone()[0]

    total_count = c.execute("""
    SELECT COUNT(*)
    FROM evaluations
    """).fetchone()[0]

    conn.close()

    return render_template(
        "evaluations.html",
        rows=rows,
        name=session["name"],
        role=session["role"],
        notifications=notifications,
        unread_count=unread_count,
        pending_count=pending_count,
        approved_count=approved_count,
        returned_count=returned_count,
        total_count=total_count,
        employees={
            email: info["name"]
            for email, info in ALLOWED_USERS.items()
            if info["role"] == "user"
        },
        selected_employee=selected_employee,
        selected_period=selected_period,
        selected_status=selected_status,
        user_names={
            email: info["name"]
            for email, info in ALLOWED_USERS.items()
        }
    )
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/admin")
def admin():

    if "email" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/works")

    selected_employee = request.args.get(
        "employee",
        "الكل"
    )
    selected_period = request.args.get(
    "period",
    "الكل"
)
    selected_status = request.args.get(
    "status",
    "الكل"
)
    selected_work_type = request.args.get("work_type", "الكل")

    conn = get_db()
    c = conn.cursor()

    query = """
    SELECT *
    FROM works
    WHERE 1=1
    """

    params = []

    if selected_employee != "الكل":
        query += " AND user_email = %s"
        params.append(selected_employee)

    if selected_period != "الكل":
        query += " AND period = %s"
        params.append(selected_period)

    if selected_status != "الكل":
        query += " AND status = %s"
        params.append(selected_status)

    if selected_work_type != "الكل":
        query += " AND work_type = %s"
        params.append(selected_work_type)

    query += " ORDER BY id DESC"

    rows = c.execute(
        query,
        params
    ).fetchall()

    notifications = c.execute("""
        SELECT *
        FROM notifications
        WHERE user_email = %s
        ORDER BY id DESC
    """, (
        session["email"],
    )).fetchall()

    unread_count = c.execute("""
    SELECT COUNT(*)
    FROM notifications
    WHERE user_email = %s
    AND is_read = 0
    """, (
        session["email"],
    )).fetchone()[0]

    pending_count = c.execute("""
    SELECT COUNT(*)
    FROM works
    WHERE status = 'pending'
    """).fetchone()[0]

    approved_count = c.execute("""
    SELECT COUNT(*)
    FROM works
    WHERE status = 'approved'
    """).fetchone()[0]

    returned_count = c.execute("""
    SELECT COUNT(*)
    FROM works
    WHERE status = 'returned'
    """).fetchone()[0]

    total_count = c.execute("""
    SELECT COUNT(*)
    FROM works
    """).fetchone()[0]

    conn.close()

    employees = {
        email: info["name"]
        for email, info in ALLOWED_USERS.items()
        if info["role"] == "user"
    }

    return render_template(
        "admin.html",
        works=rows,
        notifications=notifications,
        unread_count=unread_count,
        pending_count=pending_count,
        approved_count=approved_count,
        returned_count=returned_count,
        total_count=total_count,
        employees=employees,
        selected_employee=selected_employee,
        selected_period=selected_period,
        selected_status=selected_status,
        selected_work_type=selected_work_type,
        user_names={
            email: info["name"]
            for email, info in ALLOWED_USERS.items()
        }
    )

@app.route("/export-report")
def export_report():

    if "email" not in session:
        return redirect("/")

    conn = get_db()

    if session["role"] == "admin":

        works_df = pd.read_sql_query(
            "SELECT * FROM works",
            conn
        )

        evaluations_df = pd.read_sql_query(
            "SELECT * FROM evaluations",
            conn
        )

        file_name = "all_data.xlsx"

    else:

        works_df = pd.read_sql_query(
            """
            SELECT *
            FROM works
            WHERE user_email = %s
            """,
            conn,
            params=[session["email"]]
        )

        evaluations_df = pd.read_sql_query(
            """
            SELECT *
            FROM evaluations
            WHERE user_email = %s
            """,
            conn,
            params=[session["email"]]
        )

        file_name = "employee_report.xlsx"

    conn.close()

    with pd.ExcelWriter(file_name) as writer:

        works_df.to_excel(
            writer,
            sheet_name="الأعمال",
            index=False
        )

        evaluations_df.to_excel(
            writer,
            sheet_name="التقييمات",
            index=False
        )

    return send_file(
        file_name,
        as_attachment=True
    )


@app.route("/test-weights")
def test_weights():

    conn = get_db()
    c = conn.cursor()

    rows = c.execute("""
        SELECT *
        FROM weights
    """).fetchall()

    conn.close()

    result = ""

    for row in rows:
        result += f"{row['metric']} - {row['weight']}<br>"

    return result

@app.route("/health")
def health():
    return "APP IS RUNNING"


@app.route("/check-db")
def check_db():
    conn = get_db()
    c = conn.cursor()

    result = []

    for table_name in ["works", "evaluations", "notifications"]:
        result.append(f"<hr>{table_name.upper()} COLUMNS:")

        c.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

        for col in c.fetchall():
            result.append(col["column_name"])

    conn.close()
    return "<br>".join(result)


@app.route("/clear-weights")
def clear_weights():

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM weights")

    conn.commit()
    conn.close()

    return "DONE"

@app.route("/results")
def results():

    selected_year = request.args.get("year", "2026")
    selected_period = request.args.get("period", "الكل")
    selected_employee = request.args.get("employee", "الكل")
    selected_period = request.args.get("period","الكل")

    if "email" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/works")

    conn = get_db()
    c = conn.cursor()

    results = []

    work_metrics = {
        "مشاركة الاستطلاعات": "نسبة الاستطلاعات",
        "مشاركة الاجتماعات": "نسبة الاجتماعات",

        "استمارات مراجعة": "نسبة الاستمارات",

        "تقارير إلكترونية": "نسبة التقارير الإلكترونية",
        "تقارير ورقية": "نسبة التقارير الورقية",

        "تنظيف عينات": "نسبة العينات",

        "إشراف جهات": "نسبة الجهات",

        "دراسة طلبات": "نسبة الطلبات",

        "أعمال مبتكرة": "الأعمال المبتكرة",

        "دورات وأوراق عمل": "الدورات",

        "متابعة برامج و تطبيقات الدائرة": "نسبة متابعة البرامج و التطبيقات"
    }

    for email, info in ALLOWED_USERS.items():

        if info["role"] != "user":
            continue
        if (
            selected_employee != "الكل"
            and email != selected_employee
        ):
            continue
        total_score = 0

        # =====================
        # الأعمال العددية
        # =====================

        for work_type, metric in work_metrics.items():

            if selected_period == "الكل":

                employee_count = c.execute("""
                    SELECT COUNT(*)
                    FROM works
                    WHERE user_email = %s
                    AND work_type = %s
                    AND year = %s
                    AND status = 'approved'
                """, (
                    email,
                    work_type,
                    selected_year
                )).fetchone()[0]

                total_count = c.execute("""
                    SELECT COUNT(*)
                    FROM works
                    WHERE work_type = %s
                    AND year = %s
                    AND status = 'approved'
                """, (
                    work_type,
                    selected_year
                )).fetchone()[0]

            else:

                employee_count = c.execute("""
                    SELECT COUNT(*)
                    FROM works
                    WHERE user_email = %s
                    AND work_type = %s
                    AND year = %s
                    AND period = %s
                    AND status = 'approved'                      
                """, (
                    email,
                    work_type,
                    selected_year,
                    selected_period
                )).fetchone()[0]

                total_count = c.execute("""
                    SELECT COUNT(*)
                    FROM works
                    WHERE work_type = %s
                    AND year = %s
                    AND period = %s
                    AND status = 'approved'
                """, (
                    work_type,
                    selected_year,
                    selected_period
                )).fetchone()[0]

            if total_count > 0:

                weight_row = c.execute("""
                    SELECT weight
                    FROM weights
                    WHERE metric = %s
                """, (metric,)).fetchone()

                if weight_row:

                    total_score += (
                        employee_count / total_count
                    ) * weight_row["weight"]

        # =====================
        # المتوسطات
        # =====================

        average_metrics = {
            "تقارير ورقية": "متوسط أيام إعداد التقرير الورقي",
            "تقارير إلكترونية": "متوسط أيام إعداد التقرير الإلكتروني",
            "دراسة طلبات": "متوسط أيام دراسة الطلبات"
        }

        for work_type, metric in average_metrics.items():

            if selected_period == "الكل":

                avg_row = c.execute("""
                    SELECT
                        AVG(target_days) AS avg_target,
                        AVG(actual_days) AS avg_actual
                    FROM works
                    WHERE user_email = %s
                    AND work_type = %s
                    AND year = %s
                """, (
                    email,
                    work_type,
                    selected_year
                )).fetchone()

            else:

                avg_row = c.execute("""
                    SELECT
                        AVG(target_days) AS avg_target,
                        AVG(actual_days) AS avg_actual
                    FROM works
                    WHERE user_email = %s
                    AND work_type = %s
                    AND year = %s
                    AND period = %s
                """, (
                    email,
                    work_type,
                    selected_year,
                    selected_period
                )).fetchone()

            if (
                avg_row["avg_target"]
                and avg_row["avg_actual"]
                and avg_row["avg_actual"] > 0
            ):

                weight_row = c.execute("""
                    SELECT weight
                    FROM weights
                    WHERE metric = %s
                """, (metric,)).fetchone()

                if weight_row:

                    total_score += (
                        avg_row["avg_target"]
                        / avg_row["avg_actual"]
                    ) * weight_row["weight"]

        # =====================
        # التقييمات
        # =====================

        if selected_period == "الكل":

            eval_row = c.execute("""
                SELECT
                    AVG(quality) AS quality,
                    AVG(teamwork) AS teamwork,
                    AVG(continuity) AS continuity,
                    AVG(extra_work) AS extra_work
                FROM evaluations
                WHERE user_email = %s
                AND year = %s
                AND status = 'approved'
            """, (
                email,
                selected_year
            )).fetchone()

        else:

            eval_row = c.execute("""
                SELECT
                    AVG(quality) AS quality,
                    AVG(teamwork) AS teamwork,
                    AVG(continuity) AS continuity,
                    AVG(extra_work) AS extra_work
                FROM evaluations
                WHERE user_email = %s
                AND year = %s
                AND period = %s
                AND status = 'approved'
            """, (
                email,
                selected_year,
                selected_period
            )).fetchone()

        eval_metrics = {
            "quality": "جودة الأعمال",
            "teamwork": "روح الفريق",
            "continuity": "استمرارية العمل",
            "extra_work": "تقبل الإضافي"
        }

        for field, metric in eval_metrics.items():

            value = eval_row[field]

            if value:

                weight_row = c.execute("""
                    SELECT weight
                    FROM weights
                    WHERE metric = %s
                """, (metric,)).fetchone()

                if weight_row:

                    total_score += (
                        value / 5
                    ) * weight_row["weight"]

        results.append({
            "name": info["name"],
            "email": email,
            "score": round(total_score * 100, 2)
        })

    conn.close()

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return render_template(
        "dashboard.html",
        results=results,
        selected_year=selected_year,
        selected_period=selected_period,
        selected_employee=selected_employee
    )

@app.route("/employee-details")
def employee_details():

    if "email" not in session:
        return redirect("/")

    email = request.args.get("email")

    user_name = ALLOWED_USERS[email]["name"]

    return render_template(
        "employee_details.html",
        user_name=user_name
    )
@app.route("/employee-details-data")
def employee_details_data():

    email = request.args.get("email")
    selected_year = request.args.get("year", "2026")
    selected_period = request.args.get("period", "الكل")

    conn = get_db()
    c = conn.cursor()

    user_name = ALLOWED_USERS[email]["name"]

    work_metrics = {
        "مشاركة الاستطلاعات": "نسبة الاستطلاعات",
        "مشاركة الاجتماعات": "نسبة الاجتماعات",

        "استمارات مراجعة": "نسبة الاستمارات",

        "تقارير إلكترونية": "نسبة التقارير الإلكترونية",
        "تقارير ورقية": "نسبة التقارير الورقية",

        "تنظيف عينات": "نسبة العينات",

        "إشراف جهات": "نسبة الجهات",

        "دراسة طلبات": "نسبة الطلبات",

        "أعمال مبتكرة": "الأعمال المبتكرة",

        "دورات وأوراق عمل": "الدورات",

        "متابعة برامج و تطبيقات الدائرة": "نسبة متابعة البرامج و التطبيقات"
    }
    html = f"""
    <h3 class='mb-3'>{user_name}</h3>

    <table class='table table-bordered table-hover'>
    <thead>
    <tr>
        <th>المعيار</th>
        <th>النسبة</th>
        <th>التفاصيل</th>
    </tr>
    </thead>
    <tbody>
    """

    counter = 0
    total_score = 0
    for work_type, metric in work_metrics.items():

        if selected_period == "الكل":

            works = c.execute("""
                SELECT work_details
                FROM works
                WHERE user_email = %s
                AND work_type = %s
                AND year = %s
                AND status = 'approved'
            """, (
                email,
                work_type,
                selected_year
            )).fetchall()

        else:

            works = c.execute("""
                SELECT work_details
                FROM works
                WHERE user_email = %s
                AND work_type = %s
                AND year = %s
                AND period = %s
                AND status = 'approved'
            """, (
                email,
                work_type,
                selected_year,
                selected_period
            )).fetchall()

        count = len(works)

        if selected_period == "الكل":

            total_count = c.execute("""
                SELECT COUNT(*)
                FROM works
                WHERE work_type = %s
                AND year = %s
                AND status = 'approved'
            """, (
                work_type,
                selected_year
            )).fetchone()[0]

        else:

            total_count = c.execute("""
                SELECT COUNT(*)
                FROM works
                WHERE work_type = %s
                AND year = %s
                AND period = %s
                AND status = 'approved'
            """, (
                work_type,
                selected_year,
                selected_period
            )).fetchone()[0]

        weight_row = c.execute("""
        SELECT weight
        FROM weights
        WHERE metric = %s
        """, (
            metric,
        )).fetchone()

        result_percent = 0

        if total_count > 0 and weight_row:

            result_percent = round(
                (
                    count / total_count
                )
                * weight_row["weight"]
                * 100,
                2
            )
        total_score += result_percent

        details_html = ""

        for row in works:
            details_html += f"• {row['work_details']}<br>"

        collapse_id = f"details_{counter}"
        counter += 1

        html += f"""
        <tr>
            <td>{metric}</td>
            <td>{result_percent}%</td>

            <td>

                <button
                    class="btn btn-sm btn-primary"
                    data-bs-toggle="collapse"
                    data-bs-target="#{collapse_id}"
                >
                    عرض الأعمال
                </button>

                <div
                    id="{collapse_id}"
                    class="collapse mt-2"
                >
                    {details_html if details_html else "لا توجد أعمال"}
                </div>

            </td>

        </tr>
        """
    # ==================================
    # معايير الوقت
    # ==================================

    average_metrics = {
        "تقارير ورقية": "متوسط أيام إعداد التقرير الورقي",
        "تقارير إلكترونية": "متوسط أيام إعداد التقرير الإلكتروني",
        "دراسة طلبات": "متوسط أيام دراسة الطلبات"
    }

    for work_type, metric in average_metrics.items():

        if selected_period == "الكل":

            avg_row = c.execute("""
                SELECT
                    AVG(target_days) AS avg_target,
                    AVG(actual_days) AS avg_actual
                FROM works
                WHERE user_email = %s
                AND work_type = %s
                AND year = %s
            """, (
                email,
                work_type,
                selected_year
            )).fetchone()

        else:

            avg_row = c.execute("""
                SELECT
                    AVG(target_days) AS avg_target,
                    AVG(actual_days) AS avg_actual
                FROM works
                WHERE user_email = %s
                AND work_type = %s
                AND year = %s
                AND period = %s
            """, (
                email,
                work_type,
                selected_year,
                selected_period
            )).fetchone()

        result_percent = 0

        if (
            avg_row["avg_target"]
            and avg_row["avg_actual"]
            and avg_row["avg_actual"] > 0
        ):

            weight_row = c.execute("""
                SELECT weight
                FROM weights
                WHERE metric = %s
            """, (
                metric,
            )).fetchone()

            if weight_row:

                result_percent = round(
                    (
                        avg_row["avg_target"]
                        / avg_row["avg_actual"]
                    )
                    * weight_row["weight"]
                    * 100,
                    2
                )
            total_score += result_percent

        collapse_id = f"time_{counter}"
        counter += 1

        html += f"""
        <tr class="table-warning">

            <td>{metric}</td>

            <td>{result_percent}%</td>

            <td>

                <button
                    class="btn btn-sm btn-warning"
                    data-bs-toggle="collapse"
                    data-bs-target="#{collapse_id}"
                >
                    عرض التفاصيل
                </button>

                <div
                    id="{collapse_id}"
                    class="collapse mt-2"
                >
                    المتوسط المحدد:
                    {round(avg_row["avg_target"] or 0,2)}

                    <br>

                    المتوسط الفعلي:
                    {round(avg_row["avg_actual"] or 0,2)}
                </div>

            </td>

        </tr>
        """
    # ==================================
    # التقييمات
    # ==================================

    if selected_period == "الكل":

        eval_row = c.execute("""
            SELECT
                AVG(quality) AS quality,
                AVG(teamwork) AS teamwork,
                AVG(continuity) AS continuity,
                AVG(extra_work) AS extra_work
            FROM evaluations
            WHERE user_email = %s
            AND year = %s
            AND status = 'approved'
        """, (
            email,
            selected_year
        )).fetchone()

    else:

        eval_row = c.execute("""
            SELECT
                AVG(quality) AS quality,
                AVG(teamwork) AS teamwork,
                AVG(continuity) AS continuity,
                AVG(extra_work) AS extra_work
            FROM evaluations
            WHERE user_email = %s
            AND year = %s
            AND period = %s
            AND status = 'approved'
        """, (
            email,
            selected_year,
            selected_period
        )).fetchone()

    eval_metrics = {
        "quality": "جودة الأعمال",
        "teamwork": "روح الفريق",
        "continuity": "استمرارية العمل",
        "extra_work": "تقبل الإضافي"
    }

    for field, metric in eval_metrics.items():

        value = eval_row[field] or 0

        result_percent = 0

        weight_row = c.execute("""
            SELECT weight
            FROM weights
            WHERE metric = %s
        """, (
            metric,
        )).fetchone()

        if weight_row:

            result_percent = round(
                (
                    value / 5
                )
                * weight_row["weight"]
                * 100,
                2
            )
        total_score += result_percent

        collapse_id = f"eval_{counter}"
        counter += 1

        html += f"""
        <tr class="table-success">

            <td>{metric}</td>

            <td>{result_percent}%</td>

            <td>

                <button
                    class="btn btn-sm btn-success"
                    data-bs-toggle="collapse"
                    data-bs-target="#{collapse_id}"
                >
                    عرض التفاصيل
                </button>

                <div
                    id="{collapse_id}"
                    class="collapse mt-2"
                >
                    متوسط التقييم:
                    {round(value,2)}
                    من 5
                </div>

            </td>

        </tr>
        """

    html += f"""
    <tr class="table-dark">
        <td>
            <strong>النتيجة النهائية</strong>
        </td>

        <td>
            <strong>{round(total_score,2)}%</strong>
        </td>

        <td>
            مجموع جميع المعايير
        </td>
    </tr>
    """

    html += """
    </tbody>
    </table>
    """

    conn.close()

    return html


@app.route("/delete-work/<int:work_id>")
def delete_work(work_id):

    if "email" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM notifications
        WHERE work_id = %s
    """, (work_id,))

    if session["role"] == "admin":
        

        c.execute("""
            DELETE FROM works
            WHERE id = %s
        """, (work_id,))

    else:

        c.execute("""
            DELETE FROM works
            WHERE id = %s
            AND user_email = %s
        """, (
            work_id,
            session["email"]
        ))

    conn.commit()
    conn.close()

    if session["role"] == "admin":
        return redirect("/admin")

    return redirect("/works")


@app.route("/edit-work/<int:work_id>", methods=["GET", "POST"])
def edit_work(work_id):

    if "email" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    if session["role"] == "admin":

        work = c.execute("""
        SELECT *
        FROM works
        WHERE id = %s
        """, (work_id,)).fetchone()

    else:

        work = c.execute("""
        SELECT *
        FROM works
        WHERE id = %s
        AND user_email = %s
        """, (
            work_id,
            session["email"]
        )).fetchone()

    if not work:
        conn.close()
        return "غير مسموح"

    if request.method == "POST":

        c.execute("""
            UPDATE works
            SET work_details = %s
            WHERE id = %s
        """, (
            request.form["work_details"],
            work_id
        ))

        conn.commit()
        conn.close()

        return redirect("/works")

    conn.close()

    return render_template(
        "edit_work.html",
        work=work
    )
@app.route("/delete-evaluation/<int:evaluation_id>")
def delete_evaluation(evaluation_id):

    if "email" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM notifications
        WHERE evaluation_id = %s
    """, (
        evaluation_id,
    ))
    c.execute("""
        DELETE FROM evaluations
        WHERE id = %s
        AND user_email = %s
    """, (
        evaluation_id,
        session["email"]
    ))

    conn.commit()
    conn.close()

    return redirect("/evaluations")
@app.route("/delete-evaluation-admin/<int:evaluation_id>")
def delete_evaluation_admin(evaluation_id):

    if "email" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM notifications
        WHERE evaluation_id = %s
    """, (
        evaluation_id,
    ))
    c.execute("""
        DELETE FROM evaluations
        WHERE id = %s
    """, (evaluation_id,))

    conn.commit()
    conn.close()

    return redirect("/evaluations")






@app.route("/count-works")
def count_works():

    conn = get_db()
    c = conn.cursor()

    count = c.execute(
        "SELECT COUNT(*) FROM works"
    ).fetchone()[0]

    conn.close()

    return str(count)


@app.route("/edit-work-admin", methods=["POST"])
def edit_work_admin():

    if "email" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/")

    work_id = request.form["work_id"]
    work_details = request.form["work_details"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        UPDATE works
        SET work_details = %s
        WHERE id = %s
    """, (
        work_details,
        work_id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/test")
def test():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'works'
        ORDER BY ordinal_position
    """)

    rows = c.fetchall()
    conn.close()

    return "<br>".join([r["column_name"] for r in rows])


@app.route("/check-status")
def check_status():

    conn = get_db()
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, status
        FROM works

    """).fetchall()

    conn.close()

    return "<br>".join([
        f"{r['id']} - {r['status']}"
        for r in rows
    ])


@app.route("/approve-work/<int:work_id>")
def approve_work(work_id):

    if "email" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
    SELECT user_email, work_type
    FROM works
    WHERE id = %s
    """, (work_id,)).fetchone()

    c.execute("""
        UPDATE works
        SET
            status = 'approved',
            approved_date = %s,
            admin_note = NULL
        WHERE id = %s
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        work_id
    ))

    

    add_notification(
        c,
        row["user_email"],
        f"✅ تم اعتماد العمل: {row['work_type']}",
        work_id
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/return-work", methods=["POST"])
def return_work():

    if session["role"] != "admin":
        return redirect("/")

    work_id = request.form["work_id"]
    admin_note = request.form["admin_note"]
    print("WORK =", work_id)
    print("NOTE =", admin_note)


    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
    SELECT user_email, work_type
    FROM works
    WHERE id = %s
    """, (work_id,)).fetchone()

    c.execute("""
        UPDATE works
        SET
            status = 'returned',
            admin_note = %s
        WHERE id = %s
    """, (
        admin_note,
        work_id
    ))

    

    add_notification(
        c,
        row["user_email"],
        f"🔄 تم إرجاع العمل: {row['work_type']} - الملاحظة: {admin_note}",
        work_id
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/bulk-approve", methods=["POST"])
def bulk_approve():

    if session["role"] != "admin":
        return redirect("/")

    ids = request.form.getlist("selected_works")

    conn = get_db()
    c = conn.cursor()

    for work_id in ids:

        c.execute("""
            UPDATE works
            SET status='approved'
            WHERE id=%s
        """, (work_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/bulk-unapprove", methods=["POST"])
def bulk_unapprove():

    if session["role"] != "admin":
        return redirect("/")

    ids = request.form.getlist("selected_works")

    conn = get_db()
    c = conn.cursor()

    for work_id in ids:

        row = c.execute("""
            SELECT user_email, work_type
            FROM works
            WHERE id = %s
        """, (work_id,)).fetchone()

        c.execute("""
            UPDATE works
            SET
                status = 'pending',
                approved_date = NULL
            WHERE id = %s
        """, (work_id,))

        add_notification(
            c,
            row["user_email"],
            f"❌ تم إلغاء اعتماد العمل: {row['work_type']}",
            work_id=work_id
        )

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/approve-evaluation/<int:evaluation_id>")
def approve_evaluation(evaluation_id):

    if session["role"] != "admin":
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
    SELECT user_email, period
    FROM evaluations
    WHERE id = %s
    """, (evaluation_id,)).fetchone()

    c.execute("""
        UPDATE evaluations
        SET
            status='approved',
            approved_date=%s,
            admin_note=NULL
        WHERE id=%s
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        evaluation_id
    ))



    add_notification(
        c,
    row["user_email"],
    f"✅ تم اعتماد تقييم {row['period']}",
    evaluation_id=evaluation_id
)
    conn.commit()
    conn.close()
    
    return redirect("/evaluations")

@app.route("/return-evaluation", methods=["POST"])
def return_evaluation():

    if session["role"] != "admin":
        return redirect("/")

    evaluation_id = request.form["evaluation_id"]
    admin_note = request.form["admin_note"]



    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
    SELECT user_email, period
    FROM evaluations
    WHERE id = %s
    """, (evaluation_id,)).fetchone()

    c.execute("""
        UPDATE evaluations
        SET
            status='returned',
            admin_note=%s
        WHERE id=%s
    """, (
        admin_note,
        evaluation_id
    ))

    

    add_notification(
        c,
        row["user_email"],
        f"🔄 تم إرجاع تقييم {row['period']} - الملاحظة: {admin_note}",
        evaluation_id=evaluation_id
    )
    conn.commit()
    conn.close()

    return redirect("/evaluations")

@app.route("/test-work/<int:work_id>")
def test_work(work_id):

    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
        SELECT *
        FROM works
        WHERE id = %s
    """, (work_id,)).fetchone()

    conn.close()

    if row is None:
        return f"Work {work_id} NOT FOUND"

    return str(dict(row))


@app.route("/check-work/<int:work_id>")
def check_work(work_id):

    conn = get_db()
    c = conn.cursor()

    row = c.execute("""
        SELECT id,status,admin_note
        FROM works
        WHERE id=%s
    """, (work_id,)).fetchone()

    conn.close()

    if not row:
        return "NOT FOUND"

    return f"""
    ID={row['id']}<br>
    STATUS={row['status']}<br>
    NOTE={row['admin_note']}
    """


@app.route("/bulk-approve-evaluations", methods=["POST"])
def bulk_approve_evaluations():

    if session["role"] != "admin":
        return redirect("/")

    ids = request.form.getlist(
        "selected_evaluations"
    )

    conn = get_db()
    c = conn.cursor()

    for evaluation_id in ids:

        c.execute("""
            UPDATE evaluations
            SET status='approved'
            WHERE id=%s
        """, (
            evaluation_id,
        ))

    conn.commit()
    conn.close()

    return redirect("/evaluations")




@app.route("/add-test-notification")
def add_test_notification():

    add_notification(
        "ibreez@ncsi.gov.om",
        "اختبار إشعار"
    )

    return "DONE"


@app.route("/mark-notifications-read")
def mark_notifications_read():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_email = %s
    """, (
        session["email"],
    ))

    conn.commit()
    conn.close()

    return "OK"


@app.route("/test-notifications")
def test_notifications():

    conn = get_db()
    c = conn.cursor()

    rows = c.execute("""
        SELECT *
        FROM notifications
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    result = ""

    for row in rows:
        result += f"""
        ID={row['id']}<br>
        WORK_ID={row['work_id']}<br>
        EVALUATION_ID={row['evaluation_id']}<br>
        MESSAGE={row['message']}
        <hr>
        """

    return result


@app.route("/clear-notifications")
def clear_notifications():

    if "email" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM notifications
        WHERE user_email = %s
    """, (
        session["email"],
    ))

    conn.commit()
    conn.close()

    return redirect("/works")


@app.route("/delete-notification/<int:notification_id>")
def delete_notification(notification_id):

    if "email" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM notifications
        WHERE id = %s
        AND user_email = %s
    """, (
        notification_id,
        session["email"]
    ))

    conn.commit()
    conn.close()

    return redirect("/works")


@app.route("/check-notification-columns")
def check_notification_columns():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'notifications'
        ORDER BY ordinal_position
    """)

    rows = c.fetchall()
    conn.close()

    return "<br>".join([r["column_name"] for r in rows])

@app.route("/migrate-old-data")
def migrate_old_data():

    import sqlite3
    from psycopg2.extras import execute_values

    sqlite_conn = sqlite3.connect("users.db")
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = get_db()
    pg_cursor = pg_conn.cursor()

    tables = [
        "users",
        "works",
        "evaluations",
        "weights",
        "notifications"
    ]

    result = []

    try:

        for table in tables:

            rows = sqlite_conn.execute(
                f"SELECT * FROM {table}"
            ).fetchall()

            if not rows:
                result.append(f"{table}: 0")
                continue

            pg_cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))

            pg_columns = [
                row["column_name"]
                for row in pg_cursor.fetchall()
            ]

            common_columns = [
                col
                for col in rows[0].keys()
                if col in pg_columns
            ]

            values = [
                tuple(row[col] for col in common_columns)
                for row in rows
            ]

            columns_sql = ", ".join(common_columns)

            pg_cursor.execute(
                f"DELETE FROM {table}"
            )

            execute_values(
                pg_cursor,
                f"""
                INSERT INTO {table}
                ({columns_sql})
                VALUES %s
                """,
                values
            )

            if "id" in common_columns:

                pg_cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE(
                            (SELECT MAX(id) FROM {table}),
                            1
                        ),
                        true
                    )
                """)

            result.append(
                f"{table}: {len(rows)} migrated"
            )

        pg_conn.commit()

        return "<br>".join(result)

    except Exception as e:

        pg_conn.rollback()

        return f"ERROR: {e}"

    finally:

        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    app.run(debug=True)