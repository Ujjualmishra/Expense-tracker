from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "secret_key"
DB_FILE = "database.db"


# ---------- DATABASE ----------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        monthly_limit REAL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        category TEXT,
        date TEXT,
        note TEXT
    )
    """)

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- PAGES ----------

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard_page():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ---------- AUTH ----------

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    password = hashlib.sha256(data["password"].encode()).hexdigest()

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (data["username"], password)
        )
        conn.commit()
    except:
        return jsonify({"error": "Username exists"}), 400
    finally:
        conn.close()

    return jsonify({"message": "Registered"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    password = hashlib.sha256(data["password"].encode()).hexdigest()

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (data["username"], password)
    ).fetchone()
    conn.close()

    if user:
        session["user_id"] = user["id"]
        return jsonify({"message": "Success"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- EXPENSE ----------

@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    conn.execute("""
        INSERT INTO expenses(user_id,amount,category,date,note)
        VALUES(?,?,?,?,?)
    """, (
        session["user_id"],
        data["amount"],
        data["category"],
        data["date"],
        data["note"]
    ))
    conn.commit()
    conn.close()

    return jsonify({"message": "Added"})


@app.route("/api/set-limit", methods=["POST"])
def set_limit():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    conn.execute(
        "UPDATE users SET monthly_limit=? WHERE id=?",
        (data["limit"], session["user_id"])
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Updated"})


@app.route("/api/dashboard-data")
def dashboard_data():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()

    total = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()["total"] or 0

    limit = conn.execute(
        "SELECT monthly_limit FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()["monthly_limit"] or 0

    conn.close()

    return jsonify({
        "monthly_total": total,
        "limit": limit
    })


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)
