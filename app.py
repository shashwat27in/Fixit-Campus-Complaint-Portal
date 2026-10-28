from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import hmac
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FIXIT_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FIXIT_SECRET_KEY is missing from .env")
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    "@localhost/fixit"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

def staff_login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_staff"):
            return redirect(url_for("staff_login"))
        return view_function(*args, **kwargs)

    return wrapped_view

@app.route("/staff-login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        expected_username = os.getenv("FIXIT_STAFF_USERNAME", "")
        expected_password = os.getenv("FIXIT_STAFF_PASSWORD", "")

        if (
            expected_username
            and expected_password
            and hmac.compare_digest(username, expected_username)
            and hmac.compare_digest(password, expected_password)
        ):
            session.clear()
            session["is_staff"] = True
            return redirect(url_for("staff_dashboard"))

        return render_template(
            "staff_login.html",
            error="Invalid username or password"
        )

    return render_template("staff_login.html")



class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Reported")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

@app.route("/staff-logout", methods=["POST"])
@staff_login_required
def staff_logout():
    session.clear()
    return redirect(url_for("staff_login"))


@app.route("/")
def home():
    return render_template("index.html")
@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        category = request.form.get("category")
        location = request.form.get("location")
        description = request.form.get("description")

        complaint = Complaint(
            user_id=1,
            category=category,
            location=location,
            description=description,
        )

        db.session.add(complaint)
        db.session.flush()

        photo = request.files.get("photo")

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            if filename:
                unique_filename = f"{complaint.id}_{filename}"
                photo_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                photo.save(photo_path)

                attachment = Attachment(
                    complaint_id=complaint.id,
                    file_path=f"uploads/{unique_filename}",
                )
                db.session.add(attachment)

        db.session.commit()

        print("Complaint saved successfully!")
        print("Complaint ID:", complaint.id)

    return render_template("reports/report.html")


@app.route("/my-issues")
def my_issues():
    complaints = Complaint.query.filter_by(user_id=1).order_by(Complaint.created_at.desc()).all()
    return render_template("reports/my_issues.html", complaints=complaints)
@app.route("/issue/<int:issue_id>")
def issue_detail(issue_id):
    complaint = Complaint.query.filter_by(
        id=issue_id,
        user_id=1
    ).first_or_404()

    return render_template(
        "reports/issue_detail.html",
        complaint=complaint
    )
@app.route("/issue/<int:issue_id>/update-status", methods=["POST"])
@staff_login_required
def update_issue_status(issue_id):
    complaint = Complaint.query.get_or_404(issue_id)

    new_status = request.form.get("status")
    allowed_statuses = ["Reported", "In Progress", "Resolved", "Closed"]

    if new_status not in allowed_statuses:
        return "Invalid status", 400

    complaint.status = new_status
    db.session.commit()

    return redirect(url_for("issue_detail", issue_id=complaint.id))
@app.route("/staff-dashboard")
@staff_login_required
def staff_dashboard():
    complaints = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).all()

    return render_template(
        "reports/staff_dashboard.html",
        complaints=complaints
    )
if __name__ == "__main__":
    app.run(debug=True)