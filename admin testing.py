from flask import Flask, render_template_string, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this!

# Hardcoded admin access password (safe for local use only)
ACCESS_PASSWORD = "weddingAccess123"

# Template for access lock
ACCESS_LOCK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Access Locked</title></head>
<body>
  <h2>🔐 Enter Access Password</h2>
  <form method="POST">
    <input type="password" name="password" placeholder="Enter password" required />
    <button type="submit">Unlock</button>
    {% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
  </form>
</body>
</html>
"""

# Template for admin panel
ADMIN_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Panel</title></head>
<body>
  <h1>🌸 Welcome to Your Wedding Admin Panel</h1>
  <p>Only you can see this!</p>
  <a href="/logout">Logout</a>
</body>
</html>
"""

@app.route('/access-lock', methods=['GET', 'POST'])
def access_lock():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ACCESS_PASSWORD:
            session['preauth'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = "Incorrect password!"
    return render_template_string(ACCESS_LOCK_HTML, error=error)

@app.route('/rosepanel-x7q29')
def admin_panel():
    if not session.get('preauth'):
        return redirect(url_for('access_lock'))
    return render_template_string(ADMIN_PANEL_HTML)

@app.route('/logout')
def logout():
    session.pop('preauth', None)
    return redirect(url_for('access_lock'))

if __name__ == '__main__':
    app.run(debug=True)
