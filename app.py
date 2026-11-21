"""Un-Jobless - Rerun: a small, working job board built with Flask + SQLite."""
import os
import re
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DATABASE", os.path.join(BASE_DIR, "unjobless.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

CATEGORIES = ["Technology", "Design", "Data", "Marketing", "Sales",
              "Finance", "Hospitality", "Education", "Other"]
JOB_TYPES = ["Full-time", "Part-time", "Internship", "Freelance"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    location    TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'Other',
    job_type    TEXT NOT NULL DEFAULT 'Full-time',
    salary_min  INTEGER NOT NULL DEFAULT 0,
    salary_max  INTEGER NOT NULL DEFAULT 0,
    address     TEXT NOT NULL DEFAULT '',
    phone       TEXT NOT NULL DEFAULT '',
    experience  TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    phone      TEXT NOT NULL DEFAULT '',
    message    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

SEED_JOBS = [
    ("Software Developer", "Tech Solutions", "Phnom Penh", "Technology", "Full-time", 800, 1200,
     "#12A, Russian Federation Blvd, Phnom Penh", "+855 23 888 111",
     "1+ years of coding experience (fresh graduates welcome!)",
     "We are looking for a junior developer to help build and maintain Python web applications. Great teamwork skills required."),
    ("Web Designer", "Creative Studio", "Remote", "Design", "Freelance", 500, 800,
     "Work from home (office located in BKK1, Phnom Penh)", "+855 15 999 222",
     "No experience required, but you must have a portfolio of design samples.",
     "Design beautiful websites and user interfaces. Experience with Figma or Photoshop is a big plus!"),
    ("Data Analyst", "Insight Analytics", "Phnom Penh", "Data", "Full-time", 700, 1100,
     "Floor 5, Vattanac Capital Tower, Monivong Blvd", "+855 12 444 555",
     "2+ years working with Excel formulas or basic data tools.",
     "Clean, analyze, and present company data to stakeholders. You must understand basic Excel."),
    ("Marketing Intern", "Mekong Goods", "Phnom Penh", "Marketing", "Internship", 150, 250,
     "St. 242, Daun Penh, Phnom Penh", "+855 17 321 654",
     "Students welcome. Good written English and Khmer.",
     "Help run our Facebook and Telegram pages, write short posts, and report weekly results to the team."),
    ("Barista", "Angkor Beans Cafe", "Siem Reap", "Hospitality", "Part-time", 250, 350,
     "Pub Street area, Siem Reap", "+855 96 777 123",
     "Training provided. Friendly and punctual.",
     "Prepare coffee and tea, serve guests, and keep the bar clean. Weekend shifts available."),
    ("English Teacher", "Bright Future School", "Phnom Penh", "Education", "Full-time", 600, 900,
     "Street 271, Tuol Kork, Phnom Penh", "+855 11 555 987",
     "Bachelor's degree and a teaching certificate (TEFL or similar).",
     "Teach English to primary students, prepare lessons, and meet with parents once a month."),
]


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO jobs (title, company, location, category, job_type, salary_min, salary_max,"
            " address, phone, experience, description, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [j + (now(),) for j in SEED_JOBS],
        )
    db.commit()
    db.close()


init_db()


# ---------------------------------------------------------------- helpers
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["CATEGORIES"] = CATEGORIES
app.jinja_env.globals["JOB_TYPES"] = JOB_TYPES


@app.before_request
def protect_posts():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        token = session.get("_csrf", "")
        if not token or not secrets.compare_digest(token, sent):
            abort(400)


@app.template_filter("salary")
def salary_filter(job):
    lo, hi = job["salary_min"], job["salary_max"]
    if lo and hi:
        return f"${lo:,} – ${hi:,} / month"
    if lo or hi:
        return f"${(lo or hi):,} / month"
    return "Salary not listed"


@app.template_filter("ago")
def ago_filter(iso):
    try:
        days = (datetime.utcnow() - datetime.fromisoformat(iso)).days
    except ValueError:
        return ""
    if days <= 0:
        return "Posted today"
    if days == 1:
        return "Posted yesterday"
    return f"Posted {days} days ago"


def to_int(value):
    digits = re.sub(r"[^\d]", "", value or "")
    return int(digits) if digits else 0


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------- public pages
@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    category = request.args.get("category", "").strip()
    job_type = request.args.get("job_type", "").strip()
    sort = request.args.get("sort", "newest")

    sql = "SELECT * FROM jobs WHERE active = 1"
    params = []
    if q:
        like = f"%{q}%"
        sql += " AND (title LIKE ? OR company LIKE ? OR location LIKE ? OR description LIKE ?)"
        params += [like, like, like, like]
    if location:
        sql += " AND location = ?"
        params.append(location)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if job_type:
        sql += " AND job_type = ?"
        params.append(job_type)
    sql += " ORDER BY salary_max DESC, id DESC" if sort == "salary" else " ORDER BY id DESC"

    db = get_db()
    jobs = db.execute(sql, params).fetchall()
    locations = [r["location"] for r in db.execute(
        "SELECT DISTINCT location FROM jobs WHERE active = 1 ORDER BY location")]
    filtered = any([q, location, category, job_type])
    return render_template("index.html", jobs=jobs, locations=locations, q=q,
                           location=location, category=category, job_type=job_type,
                           sort=sort, filtered=filtered)


@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = get_db().execute("SELECT * FROM jobs WHERE id = ? AND active = 1", (job_id,)).fetchone()
    if job is None:
        abort(404)
    return render_template("detail.html", job=job, form={}, errors=[])


@app.route("/job/<int:job_id>/apply", methods=["POST"])
def apply(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ? AND active = 1", (job_id,)).fetchone()
    if job is None:
        abort(404)
    if request.form.get("website"):  # honeypot: real people leave this empty
        return redirect(url_for("job_detail", job_id=job_id))

    form = {k: request.form.get(k, "").strip() for k in ("name", "email", "phone", "message")}
    errors = []
    if len(form["name"]) < 2:
        errors.append("Enter your full name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", form["email"]):
        errors.append("Enter a valid email address, like name@example.com.")
    if len(form["message"]) > 2000:
        errors.append("Keep your message under 2,000 characters.")
    if errors:
        return render_template("detail.html", job=job, form=form, errors=errors), 400

    db.execute("INSERT INTO applications (job_id, name, email, phone, message, created_at)"
               " VALUES (?,?,?,?,?,?)",
               (job_id, form["name"], form["email"], form["phone"], form["message"], now()))
    db.commit()
    flash(f"Application sent to {job['company']}. Good luck, {form['name'].split()[0]}!", "ok")
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/post", methods=["GET", "POST"])
def post_job():
    fields = ("title", "company", "location", "category", "job_type", "salary_min",
              "salary_max", "address", "phone", "experience", "description")
    if request.method == "GET":
        return render_template("post.html", form={"category": "Other", "job_type": "Full-time"}, errors=[])

    form = {k: request.form.get(k, "").strip() for k in fields}
    errors = []
    if len(form["title"]) < 3:
        errors.append("Enter a job title.")
    if len(form["company"]) < 2:
        errors.append("Enter the company name.")
    if not form["location"]:
        errors.append("Enter a location, or type Remote.")
    if form["category"] not in CATEGORIES:
        errors.append("Pick a category from the list.")
    if form["job_type"] not in JOB_TYPES:
        errors.append("Pick a job type from the list.")
    if len(form["description"]) < 30:
        errors.append("Describe the job in at least 30 characters.")
    lo, hi = to_int(form["salary_min"]), to_int(form["salary_max"])
    if lo and hi and lo > hi:
        errors.append("Minimum salary can't be higher than maximum salary.")
    if errors:
        return render_template("post.html", form=form, errors=errors), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO jobs (title, company, location, category, job_type, salary_min, salary_max,"
        " address, phone, experience, description, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (form["title"], form["company"], form["location"], form["category"], form["job_type"],
         lo, hi, form["address"], form["phone"], form["experience"], form["description"], now()))
    db.commit()
    flash("Your job is live.", "ok")
    return redirect(url_for("job_detail", job_id=cur.lastrowid))


# ---------------------------------------------------------------- admin
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["admin"] = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/admin") else url_for("admin"))
        error = "Wrong password. Try again."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    jobs = db.execute(
        "SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) AS apps"
        " FROM jobs j ORDER BY j.id DESC").fetchall()
    applications = db.execute(
        "SELECT a.*, j.title AS job_title, j.company FROM applications a"
        " JOIN jobs j ON j.id = a.job_id ORDER BY a.id DESC").fetchall()
    return render_template("admin.html", jobs=jobs, applications=applications)


@app.route("/admin/job/<int:job_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle(job_id):
    db = get_db()
    db.execute("UPDATE jobs SET active = 1 - active WHERE id = ?", (job_id,))
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/job/<int:job_id>/delete", methods=["POST"])
@admin_required
def admin_delete_job(job_id):
    db = get_db()
    db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    db.commit()
    flash("Job deleted along with its applications.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/application/<int:app_id>/delete", methods=["POST"])
@admin_required
def admin_delete_application(app_id):
    db = get_db()
    db.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    db.commit()
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(400)
def bad_request(_e):
    return render_template("404.html", bad=True), 400


if __name__ == "__main__":
    if ADMIN_PASSWORD == "admin123":
        print("NOTE: using the default admin password. Set ADMIN_PASSWORD before going online.")
    app.run(debug=True)
