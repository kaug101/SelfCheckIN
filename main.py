from flask import Flask, render_template, request, redirect, url_for, session
import os
import json
from checkin_utils import (
    ask_questions,
    save_checkin,
    load_user_checkins,
    generate_openai_feedback,
)
from auth import firebase_login, firebase_signup, send_password_reset_email

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret")

@app.route("/")
def home():
    if "user_email" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        success, id_token = firebase_login(email, password)
        if success:
            session["user_email"] = email
            session["id_token"] = id_token
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Login failed.")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        success, id_token = firebase_signup(email, password)
        if success:
            session["user_email"] = email
            session["id_token"] = id_token
            return redirect(url_for("dashboard"))
        else:
            return render_template("signup.html", error="Signup failed.")
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user_email"])  

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if "user_email" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        answers = json.loads(request.form["answers"])
        score, insights, _ = generate_openai_feedback(answers)
        save_checkin(session["user_email"], answers, score, recommendation=insights)
        return render_template("result.html", insights=insights, score=score)

    questions = ask_questions()
    return render_template("checkin.html", questions=questions)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
