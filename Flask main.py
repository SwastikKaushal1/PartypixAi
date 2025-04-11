from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash,session
import face_recognition
import os
import uuid
import shutil
import requests
import csv
import json
import re

app = Flask(__name__)
app.secret_key = "super_secure_party_pix_secret_2024" # Required for flashing messages

UPLOAD_FOLDER = "uploads"
MATCH_FOLDER = "matches"
DATASET_FOLDER = "wedding_photos"
USER_DB = "users.csv"
PENDING_FILE = "pending_tokens.csv"
USER_DATA_FILE = "user_data.csv"



os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MATCH_FOLDER, exist_ok=True)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1359406881914884147/jkynHq0DsAZA__f7IqqtRU9w1IrzU1R-8v1pzis9cZcY5D0G-P6yUonDgePUdqkwMylh"


def send_token_embed(username, tier):
    embed = {
        "title": "🎟️ New Token Tier Application",
        "description": f"**User:** `{username}`\n**Tier Requested:** `{tier}`",
        "color": 0x5865F2
    }

    payload = {
        "content": "<@751334414914420767> A new token request has been submitted!",
        "embeds": [embed]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print("Failed to send webhook:", e)

@app.route('/')
def home():
    # session.pop('_flashes', None)  # Clear any flash messages
    session.pop('user', None)      # Log out user if they were logged in
    return render_template('index.html')

@app.route('/')
def error():
    return render_template('index.html')



@app.route("/events")
def events():
    if 'user' not in session:
        return redirect("/login")

    user_email = session['user']
    show_form = request.args.get("show_form") == "1"
    message = request.args.get("message", "")
    error = request.args.get("error", "")
    token_data = {}

    # Get user tokens
    with open(USER_DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == user_email:
                token_data = json.loads(row['tokens']) if row['tokens'] else {}
                break

    # Get user events from events.csv
    event_list = []
    try:
        with open("events.csv", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['email'] == user_email:
                    event_list.append({
                        "id": row["id"],
                        "title": row["name"],
                        "desc": row["desc"],
                        "token": row["token"]
                    })
    except FileNotFoundError:
        event_list = []

    return render_template("user.html",
                           page="events",
                           token_data=token_data,
                           show_form=show_form,
                           message=message,
                           error=error,
                           events=event_list)


@app.route('/delete_event/<event_id>', methods=['POST'])
def delete_event(event_id):
    user_email = session.get('user')
    if not user_email:
        return redirect('/dashboard?page=events')

    photo_path_to_delete = None
    updated_events = []

    # 1. Remove from events.csv and store the photo_path to delete
    with open("events.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("id") == event_id:
                photo_path_to_delete = row.get("photo_path")
            else:
                updated_events.append(row)

    # Save updated events
    if updated_events:
        with open("events.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=updated_events[0].keys())
            writer.writeheader()
            writer.writerows(updated_events)
    else:
        open("events.csv", "w").close()  # Clear file if empty

    # 2. Remove from user's events in user_data.csv
    updated_user_rows = []
    with open(USER_DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == user_email:
                event_list = json.loads(row['events']) if row['events'] else []
                event_list = [e for e in event_list if e.get('id') != event_id]
                row['events'] = json.dumps(event_list)
            updated_user_rows.append(row)

    with open(USER_DATA_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=updated_user_rows[0].keys())
        writer.writeheader()
        writer.writerows(updated_user_rows)

    # 3. Delete the folder using actual photo_path
    if photo_path_to_delete and os.path.exists(photo_path_to_delete):
        shutil.rmtree(photo_path_to_delete)

    return redirect("/events?message=Event deleted successfully!")


@app.route('/rename_event/<event_id>', methods=['POST'])
def rename_event(event_id):
    new_title = request.form.get('new_title', '').strip()
    user_email = session.get('user')

    if not new_title or not user_email:
        return redirect('/dashboard?page=events')

    # 1. Update events.csv
    updated_events = []
    with open('events.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] == event_id:
                row['name'] = new_title  # Assuming 'name' is the title
            updated_events.append(row)

    with open('events.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=updated_events[0].keys())
        writer.writeheader()
        writer.writerows(updated_events)

    # 2. Update user_data.csv
    updated_user_data = []
    with open('user_data.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == user_email:
                events = json.loads(row['events']) if row['events'] else []
                for event in events:
                    if event.get('id') == event_id:
                        event['title'] = new_title
                row['events'] = json.dumps(events)
            updated_user_data.append(row)

    with open('user_data.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=updated_user_data[0].keys())
        writer.writeheader()
        writer.writerows(updated_user_data)

    return redirect("/events?message=Event renammed successfully!")



@app.route("/create_event", methods=["POST"])
def create_event():
    if 'user' not in session:
        return redirect("/login")

    user_email = session['user']
    name = request.form.get("eve_name")
    desc = request.form.get("eve_desc")
    token = request.form.get("eve_token")

    # Load all user data
    with open(USER_DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        user_rows = list(reader)

    token_data = {}
    for row in user_rows:
        if row['email'] == user_email:
            token_data = json.loads(row['tokens']) if row['tokens'] else {}
            break
    else:
        return redirect("/events?error=notokens")

    if token_data.get(token, 0) < 1:
        return redirect("/events?error=invalid_token")

    # Deduct token
    token_data[token] -= 1

    # Generate unique event ID
    event_id = str(uuid.uuid4())[:8]

    # Create photo folder with event ID and sanitized email
    safe_email = user_email.replace("@", "_at_").replace(".", "_")
    photo_folder_name = f"{event_id}_{safe_email}"
    photo_folder_path = os.path.join("Photos_data", photo_folder_name)
    os.makedirs(photo_folder_path, exist_ok=True)

    # Save event to global events.csv with email and folder path
    event_file = "events.csv"
    with open(event_file, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["id", "email", "name", "desc", "token", "photo_path"])
        writer.writerow([event_id, user_email, name, desc, token, photo_folder_path])

    # Update user_data.csv (tokens + embedded events list)
    for row in user_rows:
        if row['email'] == user_email:
            row['tokens'] = json.dumps(token_data)
            current_events = json.loads(row['events']) if row['events'] else []
            current_events.append({
                "id": event_id,
                "title": name,
                "token": token
            })
            row['events'] = json.dumps(current_events)

    with open(USER_DATA_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=user_rows[0].keys())
        writer.writeheader()
        writer.writerows(user_rows)

    return redirect("/events?message=Event created successfully!")






@app.route("/<page>")
def load_page(page):
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('home') + '#loginModal')

    allowed_pages = ['dashboard', 'events', 'support', 'token']
    if page not in allowed_pages:
        return render_template('index.html', page='dashboard')

    email = session['user']
    filepath = 'user_data.csv'
    user_data = {}

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['email'] == email:
                    row['tokens'] = json.loads(row['tokens']) if row['tokens'] else {}
                    row['events'] = json.loads(row['events']) if row['events'] else []
                    row['photos_uploaded'] = int(row['photos_uploaded']) if row['photos_uploaded'] else 0
                    user_data = row
                    break

    token_status_display = ''
    if page == 'token':
        try:
            with open('pending_tokens.csv', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['username'] == email:
                        token_status_display = f'''
                        <div class="token-status-container">
                            <p>⏳ Token Request Pending</p>
                            <p>Tier Applied: <strong>{row["tier_name"]}</strong></p>
                            <p>Status: <strong>{row["status"].capitalize()}</strong></p>
                        </div>
                        '''
                        break
        except FileNotFoundError:
            token_status_display = '<p>No token activity found.</p>'

    return render_template(
        'user.html',
        page=page,
        tokens=user_data.get('tokens', {}),
        photos_uploaded=user_data.get('photos_uploaded', 0),
        events=user_data.get('events', []),
        token_status_display=token_status_display
    )


@app.route('/token')
def token_page():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('home') + '#loginModal')

    username = session['user']
    token_status_display = ''

    # Check if user has a pending token request
    pending_file = 'pending_tokens.csv'
    if os.path.exists(pending_file):
        with open(pending_file, 'r') as f:
            for line in f:
                if line.startswith(username + ','):
                    _, tier, status = line.strip().split(',')
                    token_status_display = f'''
                    <div class="token-status-container">
                      <p><strong>Applied Tier:</strong> {tier}</p>
                      <p><strong>Status:</strong> {status}</p>
                    </div>
                    '''
                    break

    return render_template('user.html', page='token', token_status_display=token_status_display)



@app.route('/user')
def userlogged():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('home') + '#loginModal')

    email = session['user']
    filepath = 'user_data.csv'

    # Create CSV if it doesn't exist
    if not os.path.exists(filepath):
        with open(filepath, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['email', 'tokens', 'photos_uploaded', 'events', 'activity'])
            writer.writeheader()

    user_data = {
        'tokens': {},
        'photos_uploaded': 0,
        'events': [],
        'activity': []
    }

    with open(filepath, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['email'] == email:
                # Parse JSON strings
                user_data['tokens'] = json.loads(row['tokens']) if row['tokens'] else {}
                user_data['photos_uploaded'] = int(row['photos_uploaded']) if row['photos_uploaded'] else 0
                user_data['events'] = json.loads(row['events']) if row['events'] else []
                break

    return render_template(
    'user.html',
    tokens=user_data['tokens'],
    events=user_data['events'],
    activity=user_data['activity'],
    photos_uploaded=user_data['photos_uploaded'],
    page='dashboard'
)





@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['image']
    if not file:
        return "No file uploaded", 400

    filename = str(uuid.uuid4()) + ".jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    guest_image = face_recognition.load_image_file(filepath)
    guest_encoding = face_recognition.face_encodings(guest_image)
    
    if len(guest_encoding) == 0:
        return "No face found in the image", 400

    guest_encoding = guest_encoding[0]
    matches = []

    for img_name in os.listdir(DATASET_FOLDER):
        if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(DATASET_FOLDER, img_name)
            image = face_recognition.load_image_file(img_path)
            encodings = face_recognition.face_encodings(image)
            
            for enc in encodings:
                distance = face_recognition.face_distance([guest_encoding], enc)[0]
                if distance < 0.4:
                    matched_img_path = os.path.join(MATCH_FOLDER, img_name)
                    shutil.copy(img_path, matched_img_path)
                    matches.append(img_name)
                    break

    return render_template("result.html", matches=matches)

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if name and email and message:
        content = {
            "embeds": [
                {
                    "title": "📩 New Contact Form Submission",
                    "fields": [
                        {"name": "Name", "value": name, "inline": False},
                        {"name": "Email", "value": email, "inline": False},
                        {"name": "Message", "value": message, "inline": False}
                    ],
                    "color": 1127128
                }
            ]
        }

        try:
            requests.post(DISCORD_WEBHOOK_URL, json=content)
            flash("Message sent successfully!", "success")
        except Exception as e:
            print(e)
            flash("Failed to send message.", "error")
    else:
        flash("All fields are required!", "error")

    return redirect(url_for("home") + "#contact")

# Read users from CSV
def load_users():
    users = {}
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row["email"]] = {
                    "username": row["username"],
                    "password": row["password"]
                }
    return users



@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    users = load_users()

    if email not in users:
        flash('No account found with this email.', 'error')
        return redirect(url_for('error') + '#loginModal')

    if users[email]['password'] != password:
        flash('Incorrect password. Please try again.', 'error')
        return redirect(url_for('error') + '#loginModal')

    # Save email + username in session
    session['user'] = email
    session['username'] = users[email]['username']

    return redirect(url_for('userlogged'))

    


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for('error') + '#registerModal')

    # Create CSV if it doesn't exist
    if not os.path.exists(USER_DB):
        with open(USER_DB, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "email", "password"])

    # Check if user already exists
    with open(USER_DB, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["email"] == email or row["username"] == username:
                flash("Email or username already exists.", "error")
                return redirect(url_for('error') + '#registerModal')

    # Save new user
    with open(USER_DB, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([username, email, password])

    flash("Registration successful! You can now log in.", "success")
    return redirect(url_for('home') + '#loginModal')


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('_flashes', None)
    return redirect(url_for('home'))



@app.route('/supportloggedin', methods=["POST"])
def contactlogged():
    contact = request.form.get("contactlog")
    message = request.form.get("messagelog")

    if contact and message:
        content = {
            "embeds": [
                {
                    "title": "📩 New Contact Form Submission (Logged in user)",
                    "fields": [
                        {"name": "Email", "value": contact, "inline": False},
                        {"name": "Message", "value": message, "inline": False}
                    ],
                    "color": 1127128
                }
            ]
        }

        try:
            requests.post(DISCORD_WEBHOOK_URL, json=content)
            flash("Your form has been sumbitted, You will be contacted soon","success")
        except Exception as e:
            print(e)
            flash("Failed to send message.", "error")
    else:
        flash("All fields are required!", "error")
    return redirect(url_for('load_page', page='support'))


@app.route("/applytokens", methods=["POST"])
def applytokens():
    if 'user' not in session:
        flash("You must be logged in to apply for tokens.", "warning")
        return redirect(url_for("home"))

    username = session["user"]
    tier_name = request.form.get("tier_name")

    # Check if the user already has a pending request
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0] == username:
                    flash("You already have a pending token application. Wait for admin approval.", "warning")
                    return redirect(url_for("load_page", page="token"))

    # Save the new pending request
    with open(PENDING_FILE, "a", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([username, tier_name, "Pending"])

    # Log activity in user_data.csv
    user_data_file = "user_data.csv"
    updated_rows = []
    activity_logged = False

    if os.path.exists(user_data_file):
        with open(user_data_file, "r", newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            for row in reader:
                if row["email"] == username:
                    # Update activity
                    activity_list = json.loads(row["activity"]) if row["activity"] else []
                    activity_list.append({
                        "type": "token_apply",
                        "tier": tier_name,
                    })
                    row["activity"] = json.dumps(activity_list)
                    activity_logged = True
                updated_rows.append(row)

        if activity_logged:
            with open(user_data_file, "w", newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_rows)

    # Send to Discord
    send_token_embed(username, tier_name)

    flash(f"Successfully applied for the {tier_name} tier! Await admin approval.", "success")
    return redirect(url_for("load_page", page="token"))



@app.route('/matches/<filename>')
def matched_file(filename):
    return send_from_directory(MATCH_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

