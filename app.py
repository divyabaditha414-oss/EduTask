from flask import Flask, render_template, request, redirect, session
import sqlite3
import math
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = "your_secret_key"
# // path setup//
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# -----------------------
# DATABASE INITIALIZATION
# -----------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            branch TEXT,
            photo TEXT,
            admission_date TEXT,
            status TEXT
        )
    """)
    # //user table//
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
""")

    conn.commit()
    conn.close()

init_db()
# -----------------------
# LOGIN ROUTE
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")
# LOGOUT ROUTE
# -----------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")
# //registration router//
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            conn.close()
            return "Username already exists"

    return render_template("register.html")
# -----------------------
# HOME ROUTE (WITH PAGINATION)
# --
@app.route("/")
def welcome():
    return render_template("welcome.html")
# //dashboard//
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE status='Active'")
    active_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE status='Inactive'")
    inactive_students = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "home.html",
        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students
    )
    # //student router//
@app.route("/students")
def students_page():
    if "user" not in session:
        return redirect("/login")
    page = 1
    total_pages = 1

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    cursor.execute("SELECT branch, COUNT(*) FROM students GROUP BY branch")
    branch_data = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        students=students,
        page=page,
        total_pages=total_pages,
        branch_data=branch_data
    )
# -----------------------
# ADD STUDENT
# -----------------------
@app.route("/add", methods=["GET", "POST"])
def add_student():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        branch = request.form["branch"]
        status = request.form["status"]   # ✅ FIXED

        photo = request.files.get("photo")
        filename = None

        if photo and photo.filename != "":
            import time
            extension = photo.filename.rsplit('.', 1)[1].lower()
            filename = f"{int(time.time())}.{extension}"
            photo_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            photo.save(photo_path)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO students (name, roll, branch, photo, admission_date, status) VALUES (?, ?, ?, ?, date('now'), ?)",
            (name, roll, branch, filename, status)
        )

        conn.commit()
        conn.close()

        return redirect("/students")

    return render_template("add_student.html")
# EDIT STUDENT
# -----------------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    if "user" not in session:
        return redirect("/students")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        branch = request.form["branch"]
        status = request.form.get("status","Active")
        cursor.execute(
            "UPDATE students SET name=?, roll=?, branch=?, status=? WHERE id=?",
            (name, roll, branch, status, id)
        )

        conn.commit()
        conn.close()
        return redirect("/")

    # GET request
    cursor.execute(
        "SELECT name, roll, branch, status FROM students WHERE id=?",
        (id,)
    )
    student = cursor.fetchone()

    conn.close()

    return render_template("edit_student.html", student=student)
# -----------------------
# DELETE STUDENT
# -----------------------
@app.route("/delete/<int:id>")
def delete_student(id):
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/students")
# -----------------------
# RUN APP
# -----------------------
# //export router//
from flask import send_file
import openpyxl
from io import BytesIO
#  //report router//
@app.route("/reports")
def reports():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT branch, COUNT(*) FROM students GROUP BY branch")
    branch_report = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "reports.html",
        branch_report=branch_report,
        total_students=total_students
    )

# //export router//
@app.route("/export")
def export():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, roll, branch FROM students")
    data = cursor.fetchall()
    conn.close()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Students"

    # Header
    sheet.append(["Name", "Roll", "Branch"])

    # Data rows
    for row in data:
        sheet.append(row)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="students.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run()