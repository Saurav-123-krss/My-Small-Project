from flask import Flask, render_template, request, url_for, redirect
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max upload

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

PAGE_SIZES = {
    "A4": {"width_mm": 210, "height_mm": 297},
    "Letter": {"width_mm": 216, "height_mm": 279},
    "4x6": {"width_mm": 102, "height_mm": 152},
    "5x7": {"width_mm": 127, "height_mm": 178},
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visited_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
        (name, email.lower(), password, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password FROM users WHERE email = ?", (email.lower(),))
    row = cur.fetchone()
    conn.close()
    return row


def log_visit():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO visits (visited_at) VALUES (?)", (datetime.utcnow().isoformat(),))
    conn.commit()
    conn.close()


def get_visit_count():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM visits")
    count = cur.fetchone()[0]
    conn.close()
    return count


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def home():
    log_visit()
    visitor_count = get_visit_count()
    return render_template(
        "index.html",
        visitor_count=visitor_count,
        uploaded_image=None,
        selected_prints=4,
        selected_page_size="A4",
        page_sizes=PAGE_SIZES.keys(),
    )


@app.route("/profile", methods=["GET"])
def profile():
    return render_template(
        "profile.html",
        page_title="Profile",
        heading="Your Profile",
        subtitle="Manage your account details and workflow preferences.",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    message = None
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            error = "Please provide both email and password."
        else:
            user = get_user_by_email(email)
            if not user:
                error = "Account not found. Please create an account first."
            elif user[3] != password:
                error = "Incorrect password."
            else:
                return redirect(url_for("home"))

    return render_template(
        "login.html",
        page_title="Login",
        heading="Welcome Back",
        subtitle="Login to continue managing passport photo print workflows.",
        message=message,
        error=error,
    )


@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    message = None
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            error = "All fields are required."
        elif "@" not in email:
            error = "Please enter a valid email address."
        else:
            try:
                create_user(name, email, password)
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                error = "This email is already registered. Please login instead."

    return render_template(
        "create_account.html",
        page_title="Create Account",
        heading="Create Your Account",
        subtitle="Set up your account to save customer workflows.",
        message=message,
        error=error,
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        return redirect(url_for("home"))

    return render_template(
        "signup.html",
        page_title="Sign Up",
        heading="Sign Up",
        subtitle="Quick registration for new users.",
    )


@app.route("/process", methods=["POST"])
def process():
    log_visit()
    visitor_count = get_visit_count()

    prints = int(request.form.get("prints", 4))
    page_size = request.form.get("page_size", "A4")

    file = request.files.get("photo")
    if not file or file.filename == "":
        return render_template(
            "index.html",
            visitor_count=visitor_count,
            error="Please upload a photo first.",
            uploaded_image=None,
            selected_prints=prints,
            selected_page_size=page_size,
            page_sizes=PAGE_SIZES.keys(),
        )

    if not allowed_file(file.filename):
        return render_template(
            "index.html",
            visitor_count=visitor_count,
            error="Invalid file type. Please upload PNG/JPG/JPEG/WEBP.",
            uploaded_image=None,
            selected_prints=prints,
            selected_page_size=page_size,
            page_sizes=PAGE_SIZES.keys(),
        )

    filename = secure_filename(file.filename)
    timestamped_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], timestamped_name)
    file.save(save_path)

    uploaded_image = url_for("static", filename=f"uploads/{timestamped_name}")

    return render_template(
        "index.html",
        visitor_count=visitor_count,
        uploaded_image=uploaded_image,
        selected_prints=prints,
        selected_page_size=page_size,
        page_sizes=PAGE_SIZES.keys(),
        page_meta=PAGE_SIZES.get(page_size, PAGE_SIZES["A4"]),
    )


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

if __name__ == "__main__":
    app.run(debug=True)
