from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)

# Used for login sessions
app.secret_key = "skill_exchange_secret_key"

#database connection

def get_db_connection():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    return connection

#create database and tables

def create_database():

    connection = get_db_connection()

    # Users table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            college TEXT,
            bio TEXT
        )
    """)

    # Skills table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT UNIQUE NOT NULL
        )
    """)

    # User skills table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            skill_id INTEGER,
            skill_type TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(skill_id) REFERENCES skills(id)
        )
    """)

    # Connection requests table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS connection_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


create_database()

#login required

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper

#home route

@app.route("/")
def home():
    return render_template("index.html")

#register route

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form['password']
        hashedpassword = generate_password_hash(password)
        college = request.form["college"]
        bio = request.form["bio"]

        connection = get_db_connection()

        try:

            connection.execute("""
                INSERT INTO users
                (name, email, password, college, bio)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, hashedpassword, college, bio))

            connection.commit()

            flash("Registration successful! Please login.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash("Email already registered.")

        finally:

            connection.close()

    return render_template("register.html")

#login route

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')

    return render_template('login.html')

#reset password route

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')

    if not email:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html')

        if len(password) < 8:
            flash('Password must contain at least 8 characters.')
            return render_template('reset_password.html')

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (hashed_password, email)
        )

        conn.commit()
        conn.close()

        session.pop('reset_email', None)

        flash('Password changed successfully. Please login.')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

#forgot password route

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session['reset_email'] = email
            return redirect(url_for('reset_password'))

        flash('No account found with this email.')

    return render_template('forgot_password.html')

#Logout route

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

#dashboard route

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db_connection()

    user = connection.execute("""
        SELECT * FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    teaching_skills = connection.execute("""
        SELECT skills.skill_name
        FROM skills
        JOIN user_skills
        ON skills.id = user_skills.skill_id
        WHERE user_skills.user_id = ?
        AND user_skills.skill_type = 'teach'
    """, (session["user_id"],)).fetchall()

    learning_skills = connection.execute("""
        SELECT skills.skill_name
        FROM skills
        JOIN user_skills
        ON skills.id = user_skills.skill_id
        WHERE user_skills.user_id = ?
        AND user_skills.skill_type = 'learn'
    """, (session["user_id"],)).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        user=user,
        teaching_skills=teaching_skills,
        learning_skills=learning_skills
    )

#profile route

@app.route("/profile")
@login_required
def profile():

    connection = get_db_connection()

    user = connection.execute("""
        SELECT * FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    connection.close()

    return render_template("profile.html", user=user)

#edit profile route

@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():

    connection = get_db_connection()

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        college = request.form["college"]
        bio = request.form["bio"]

        connection.execute("""
            UPDATE users
            SET name = ?, email = ?, college = ?, bio = ?
            WHERE id = ?
        """, (
            name,
            email,
            college,
            bio,
            session["user_id"]
        ))

        connection.commit()
        connection.close()

        return redirect(url_for("profile"))

    user = connection.execute("""
        SELECT * FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    connection.close()

    return render_template("edit_profile.html", user=user)


#skills route

@app.route("/skills", methods=["GET", "POST"])
@login_required
def skills():

    if request.method == "POST":

        skill_name = request.form["skill_name"]
        skill_type = request.form["skill_type"]

        connection = get_db_connection()

        skill = connection.execute("""
            SELECT * FROM skills
            WHERE skill_name = ?
        """, (skill_name,)).fetchone()

        if skill:

            skill_id = skill["id"]

        else:

            cursor = connection.execute("""
                INSERT INTO skills (skill_name)
                VALUES (?)
            """, (skill_name,))

            skill_id = cursor.lastrowid

        existing = connection.execute("""
            SELECT * FROM user_skills
            WHERE user_id = ?
            AND skill_id = ?
            AND skill_type = ?
        """, (
            session["user_id"],
            skill_id,
            skill_type
        )).fetchone()

        if not existing:

            connection.execute("""
                INSERT INTO user_skills
                (user_id, skill_id, skill_type)
                VALUES (?, ?, ?)
            """, (
                session["user_id"],
                skill_id,
                skill_type
            ))

            connection.commit()

            flash("Skill added successfully.")

        else:

            flash("Skill already exists.")

        connection.close()

        return redirect(url_for("skills"))

    connection = get_db_connection()

    teaching = connection.execute("""
        SELECT skills.skill_name
        FROM skills
        JOIN user_skills
        ON skills.id = user_skills.skill_id
        WHERE user_skills.user_id = ?
        AND user_skills.skill_type = 'teach'
    """, (session["user_id"],)).fetchall()

    learning = connection.execute("""
        SELECT skills.skill_name
        FROM skills
        JOIN user_skills
        ON skills.id = user_skills.skill_id
        WHERE user_skills.user_id = ?
        AND user_skills.skill_type = 'learn'
    """, (session["user_id"],)).fetchall()

    connection.close()

    return render_template(
        "skills.html",
        teaching=teaching,
        learning=learning
    )

#search route

@app.route("/search")
@login_required
def search():

    skill = request.args.get("skill", "")

    connection = get_db_connection()

    users = []

    if skill:

        users = connection.execute("""
            SELECT DISTINCT users.id,
                   users.name,
                   users.college,
                   users.bio,
                   skills.skill_name
            FROM users
            JOIN user_skills
            ON users.id = user_skills.user_id
            JOIN skills
            ON skills.id = user_skills.skill_id
            WHERE skills.skill_name LIKE ?
            AND user_skills.skill_type = 'teach'
            AND users.id != ?
        """, (
            "%" + skill + "%",
            session["user_id"]
        )).fetchall()

    connection.close()

    return render_template(
        "search.html",
        users=users,
        skill=skill
    )

# send connection request route

@app.route("/connect/<int:user_id>")
@login_required
def connect(user_id):

    connection = get_db_connection()

    existing = connection.execute("""
        SELECT * FROM connection_requests
        WHERE sender_id = ?
        AND receiver_id = ?
    """, (
        session["user_id"],
        user_id
    )).fetchone()

    if not existing:

        connection.execute("""
            INSERT INTO connection_requests
            (sender_id, receiver_id, status)
            VALUES (?, ?, 'pending')
        """, (
            session["user_id"],
            user_id
        ))

        connection.commit()

        flash("Connection request sent.")

    else:

        flash("Request already sent.")

    connection.close()

    return redirect(url_for("search"))

#requests route

@app.route("/requests")
@login_required
def requests():

    connection = get_db_connection()

    received = connection.execute("""
        SELECT connection_requests.id,
               users.name,
               users.email,
               connection_requests.status
        FROM connection_requests
        JOIN users
        ON connection_requests.sender_id = users.id
        WHERE connection_requests.receiver_id = ?
    """, (session["user_id"],)).fetchall()

    sent = connection.execute("""
        SELECT connection_requests.id,
               users.name,
               connection_requests.status
        FROM connection_requests
        JOIN users
        ON connection_requests.receiver_id = users.id
        WHERE connection_requests.sender_id = ?
    """, (session["user_id"],)).fetchall()

    connection.close()

    return render_template(
        "requests.html",
        received=received,
        sent=sent
    )

#accepts request route

@app.route("/accept/<int:request_id>")
@login_required
def accept_request(request_id):

    connection = get_db_connection()

    connection.execute("""
        UPDATE connection_requests
        SET status = 'accepted'
        WHERE id = ?
        AND receiver_id = ?
    """, (
        request_id,
        session["user_id"]
    ))

    connection.commit()
    connection.close()

    flash("Connection accepted.")

    return redirect(url_for("requests"))

#rejects request route

@app.route("/reject/<int:request_id>")
@login_required
def reject_request(request_id):

    connection = get_db_connection()

    connection.execute("""
        UPDATE connection_requests
        SET status = 'rejected'
        WHERE id = ?
        AND receiver_id = ?
    """, (
        request_id,
        session["user_id"]
    ))

    connection.commit()
    connection.close()

    flash("Connection rejected.")

    return redirect(url_for("requests"))

#starts the Flask application

if __name__ == "__main__":
    app.run(debug=True)