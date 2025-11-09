# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'replace_this_with_a_random_secret'  # change for production


# ---------- DB helper ----------
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',            # change if your mysql user differs
        password='Madhu@12',            # <-- put your MySQL password here
        database='showtimehub'
    )


# ---------- Routes ----------
@app.route('/')
def home():
    # show login page
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or not password:
            flash('All fields required', 'error')
            return redirect(url_for('register'))

        pw_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (name, email, password_hash) VALUES (%s,%s,%s)",
                        (name, email, pw_hash))
            conn.commit()
            flash('Registered — please log in', 'success')
            return redirect(url_for('home'))
        except mysql.connector.IntegrityError:
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    if not email or not password:
        flash('Provide email and password', 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f'Welcome, {user["name"]}', 'success')
            return redirect(url_for('movies'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('home'))
    finally:
        conn.close()


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('home'))


@app.route('/movies')
def movies():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM movies")
        movies = cur.fetchall()
        return render_template('movies.html', movies=movies)
    finally:
        conn.close()


@app.route('/booking/<int:movie_id>', methods=['GET', 'POST'])
def booking(movie_id):
    if 'user_id' not in session:
        flash('Please log in', 'error')
        return redirect(url_for('home'))

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM movies WHERE id=%s", (movie_id,))
        movie = cur.fetchone()
        if not movie:
            flash('Movie not found', 'error')
            return redirect(url_for('movies'))

        # find already booked seats for this movie
        cur.execute("SELECT seats FROM bookings WHERE movie_id=%s AND status='Booked'", (movie_id,))
        rows = cur.fetchall()
        booked = set()
        for r in rows:
            if r['seats']:
                for s in r['seats'].split(','):
                    booked.add(s.strip())

        if request.method == 'POST':
            seats_selected = request.form.get('seats', '').strip()
            if not seats_selected:
                flash('Select seats', 'error')
                return redirect(url_for('booking', movie_id=movie_id))

            seats_list = [s.strip() for s in seats_selected.split(',') if s.strip()]
            # server-side conflict check
            conflict = []
            for seat in seats_list:
                cur.execute("""SELECT COUNT(*) AS cnt FROM bookings
                               WHERE movie_id=%s AND status='Booked' AND FIND_IN_SET(%s, seats)""",
                            (movie_id, seat))
                res = cur.fetchone()
                if res and res['cnt'] > 0:
                    conflict.append(seat)
            if conflict:
                flash('Seats already booked: ' + ','.join(conflict), 'error')
                return redirect(url_for('booking', movie_id=movie_id))

            total = len(seats_list) * movie['price']
            seats_csv = ','.join(seats_list)
            cur.execute("INSERT INTO bookings (user_id, movie_id, seats, total_amount) VALUES (%s,%s,%s,%s)",
                        (session['user_id'], movie_id, seats_csv, total))
            conn.commit()
            booking_id = cur.lastrowid
            flash('Booking confirmed', 'success')
            return redirect(url_for('confirmation', booking_id=booking_id))

        # GET: render template
        return render_template('booking.html', movie=movie, booked=booked)
    finally:
        conn.close()


@app.route('/confirmation/<int:booking_id>')
def confirmation(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT b.*, m.name AS movie_name FROM bookings b
                       JOIN movies m ON b.movie_id=m.id WHERE b.id=%s""", (booking_id,))
        booking = cur.fetchone()
        if not booking:
            flash('Booking not found', 'error')
            return redirect(url_for('movies'))
        return render_template('confirmation.html', booking=booking)
    finally:
        conn.close()


@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT b.*, m.name AS movie_name FROM bookings b
                       JOIN movies m ON b.movie_id=m.id
                       WHERE b.user_id=%s ORDER BY b.booking_time DESC""", (session['user_id'],))
        rows = cur.fetchall()
        return render_template('history.html', bookings=rows)
    finally:
        conn.close()


@app.route('/cancel/<int:booking_id>')
def cancel(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # ensure booking belongs to user
        cur.execute("SELECT user_id FROM bookings WHERE id=%s", (booking_id,))
        r = cur.fetchone()
        if not r:
            flash('Booking not found', 'error')
            return redirect(url_for('history'))
        if r[0] != session['user_id']:
            flash('Cannot cancel others booking', 'error')
            return redirect(url_for('history'))
        cur.execute("UPDATE bookings SET status='Cancelled' WHERE id=%s", (booking_id,))
        conn.commit()
        flash('Booking cancelled', 'info')
        return redirect(url_for('history'))
    finally:
        conn.close()


# Simple admin view (not secured) — you can later add auth
@app.route('/admin')
def admin():
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT b.*, u.name AS user_name, m.name AS movie_name
                       FROM bookings b
                       JOIN users u ON b.user_id=u.id
                       JOIN movies m ON b.movie_id=m.id
                       ORDER BY b.booking_time DESC""")
        rows = cur.fetchall()
        return render_template('admin.html', bookings=rows)
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
