from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash,session , Response
import face_recognition
import os
import uuid
import shutil
import requests
import csv
import json
import re
import zipfile
from io import BytesIO
from flask import send_file
import pandas as pd
from functools import wraps


app = Flask(__name__)
app.secret_key = "super_secure_party_pix_secret_2024" # Required for flashing messages

UPLOAD_FOLDER = "uploads"
MATCH_FOLDER = "matches"
TEMP_GUEST_PHOTOS_FOLDER = "static/temp_guest_photos"
DATASET_FOLDER = "wedding_photos"
USER_DB = "users.csv"
PENDING_FILE = "pending_tokens.csv"
USER_DATA_FILE = "user_data.csv"
BASE_FOLDER_PATH = './'  # Relative path to the current directory


# Secure admin path (random)
SECURE_ADMIN_PATH = "admin-9f3k29dj2ks"
USERNAME = "admin"
PASSWORD = "admin12"
ALLOWED_IPS = ['127.0.0.1']  # Set your allowed IPs here

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_GUEST_PHOTOS_FOLDER, exist_ok=True)

DISCORD_WEBHOOK_URL = "enter your discord webhook here"

TEMP_GUEST_PHOTOS_FOLDER = "static/temp_guest_photos"

    
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
                        "token": row["token"],
                        "photo_uploaded":row['photo_uploaded']
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

@app.route('/events/view/<event_id>')
def view_event(event_id):
    user_email = session.get('user')
    selected_event = None

    session["eventidoppened"]=event_id
    print(session["eventidoppened"])

    with open('user_data.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == user_email:
                events = json.loads(row['events']) if row['events'] else []
                for event in events:
                    if event['id'] == event_id:
                        selected_event = event
                        break
                break

    return render_template('user.html',page="events", events=events, selected_event=selected_event)


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    user_email = session.get('user')
    event_id = session.get('eventidoppened')  # ✅ From session

    if not user_email or not event_id:
        return redirect('/login')

    uploaded_files = request.files.getlist('photos')

    if not uploaded_files:
        return "No files uploaded", 400

    # Find matching event from CSV
    event = None
    with open('events.csv', newline='', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        for row in reader:
            if row['id'] == event_id and row['email'] == user_email:
                event = row
                break

    if not event:
        return "Event not found", 404

    token = event['token'].lower()

    # Upload limits
    limits = {
        'silver': 50,
        'gold': 100,
        'diamond': 250,
        'plat': 400,
        'royal': 600
    }
    max_uploads = limits.get(token, 50)

    folder_path = f'Photos_data/{event_id}_{user_email}'

    if not os.path.isdir(folder_path):
        return f"Upload folder not found: {folder_path}", 404

    current_files = len([
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ])
    available_slots = max_uploads - current_files

    if available_slots <= 0:
        return f"Upload limit reached for this event ({max_uploads} photos allowed)", 403

    uploaded_count = 0
    for file in uploaded_files:
        if uploaded_count >= available_slots:
            break
        if file.filename:
            file.save(os.path.join(folder_path, file.filename))
            uploaded_count += 1

    # ✅ Update photo_uploaded count in events.csv
    updated_rows = []
    with open('events.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] == event_id and row['email'] == user_email:
                prev_uploaded = int(row.get('photo_uploaded', 0))
                row['photo_uploaded'] = str(prev_uploaded + uploaded_count)
            updated_rows.append(row)

    with open('events.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=updated_rows[0].keys())
        writer.writeheader()
        writer.writerows(updated_rows)

    return redirect(f"/events?message=Uploaded {uploaded_count} photo(s) successfully!")





@app.route('/eventphoto')
def eventphoto():
    if 'user' not in session:
        return redirect('/login')

    event_id = session.get('eventidoppened')
    email=session["user"]
    print(email)

    # Find the selected event
    with open('user_data.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == session['user']:
                all_events = json.loads(row['events']) if row['events'] else []
                for event in all_events:
                    if event['id'] == event_id:
                        selected_event = event
                        break
                break

    # Find photos in the folder
    folder_path = f'Photos_data/{event_id}_{session["user"]}'
    print(folder_path)
    if os.path.exists(folder_path):
        photos = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    return render_template('eventphoto.html', selected_event=selected_event, photos=photos)



@app.route('/photo/<event_id>/<filename>')
def serve_photo(event_id, filename):
    user_email = session['user']
    folder_path = f'Photos_data/{event_id}_{user_email}'
    return send_from_directory(folder_path, filename)

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
    photo_uploaded=0

    # Create photo folder with event ID and sanitized email
    safe_email = user_email
    photo_folder_name = f"{event_id}_{safe_email}"
    photo_folder_path = os.path.join("Photos_data", photo_folder_name)
    os.makedirs(photo_folder_path, exist_ok=True)

    # Save event to global events.csv with email and folder path
    event_file = "events.csv"
    with open(event_file, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["id", "email", "name", "desc", "token", "photo_path","photo_uploaded"])
        writer.writerow([event_id, user_email, name, desc, token, photo_folder_path,photo_uploaded])

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

    if not os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "w", newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["email", "token_name", "status"])  # Add headers if needed

    # Check if the user already has a pending request
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



def get_event_email(event_id):
    with open("events.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["id"] == event_id:
                return row["email"]
    return None


def find_matching_photos_and_transfer(guest_image_path, event_id):
    # Define path where host photos for this specific event are stored
    user_email=get_event_email(event_id)
    photo_folder = os.path.join("C:/Users/richa/Desktop/Weeding project/Photos_data", f"{event_id}_{user_email}")
    event_photos_folder = f"static/event_photos/{event_id}"

    if not os.path.exists(event_photos_folder):
        os.makedirs(event_photos_folder)

    guest_image = face_recognition.load_image_file(guest_image_path)
    guest_encoding = face_recognition.face_encodings(guest_image)

    if len(guest_encoding) == 0:
        return [], "No face found in the image."

    guest_encoding = guest_encoding[0]
    matching_photos = []

    
    if not os.path.exists(photo_folder):
        return [], "Host photo folder not found."

    for filename in os.listdir(photo_folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(photo_folder, filename)
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            match_found = False

            for face_encoding in face_encodings:
                distance = face_recognition.face_distance([guest_encoding], face_encoding)[0]
                accuracy = round(1 - distance, 2)

                if accuracy >= 0.6:
                    match_found = True
                    break

            if match_found:
                shutil.copy(image_path, os.path.join(event_photos_folder, filename))
                matching_photos.append(filename)

    return matching_photos, None if matching_photos else "No matching photos found in the event."


@app.route('/guest/<event_id>', methods=['GET', 'POST'])
def guest_view(event_id):
    error = None
    selected_event = None
    photo_uploaded = False
    matching_photos = []


    with open('user_data.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_events = json.loads(row['events']) if row['events'] else []
            for event in all_events:
                if event['id'] == event_id:
                    selected_event = event
                    break
            if selected_event:
                break

    if not selected_event:
        return "Event not found", 404

    unlocked_key = f'unlocked_{event_id}'

    # Password handling
    if request.method == 'POST' and not session.get(unlocked_key):
        password_entered = request.form.get('password')
        correct_password = selected_event.get('password', 'WD1234')
        if password_entered == correct_password:
            session[unlocked_key] = True
        else:
            error = "Incorrect password."
            return render_template(
                'guest_combined.html',
                selected_event=selected_event,
                require_password=True,
                error=error
            )

    if not session.get(unlocked_key):
        return render_template(
            'guest_combined.html',
            selected_event=selected_event,
            require_password=True,
            error=error
        )

    # Photo upload logic
    if request.method == 'POST' and session.get(unlocked_key):
        guest_image = request.files.get('guest_photo')
        if guest_image:
            guest_image_path = os.path.join(TEMP_GUEST_PHOTOS_FOLDER, guest_image.filename)
            guest_image.save(guest_image_path)

            matching_photos, error_msg = find_matching_photos_and_transfer(guest_image_path, event_id)
            photo_uploaded = True

            if error_msg:
                error = error_msg
            else:
                print("✅ Matching completed with results.")

            return render_template(
                'guest_combined.html',
                selected_event=selected_event,
                require_password=False,
                error=error,
                photo_uploaded=photo_uploaded,
                photos=matching_photos,
                upload_disabled=True
            )

    # Initial state if just viewing or GET request
    return render_template(
        'guest_combined.html',
        selected_event=selected_event,
        require_password=False,
        error=None,
        photo_uploaded=photo_uploaded,
        photos=matching_photos,
        upload_disabled=False
    )




@app.route('/download_all/<event_id>')
def download_all_photos(event_id):
    folder_path = f"static/event_photos/{event_id}"

    if not os.path.exists(folder_path):
        return "No photos found", 404

    # Create a zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(folder_path, filename)
                zip_file.write(full_path, arcname=filename)

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='matching_photos.zip')




#ADMINS LOGICCCCCC


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        if client_ip not in ALLOWED_IPS and '*' not in ALLOWED_IPS:
            return Response("Forbidden: IP not allowed", 403)

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()

        return f(*args, **kwargs)
    return decorated_function


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        "Access denied.\n"
        "You must provide valid credentials.", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )


@app.route(f'/{SECURE_ADMIN_PATH}')
def admin():
    client_ip = request.remote_addr
    print("Client IP:", client_ip)

    if client_ip not in ALLOWED_IPS and '*' not in ALLOWED_IPS:
        return Response("Forbidden: IP not allowed", 403)

    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    return render_template("admin_panel.html")


def is_allowed():
    client_ip = request.remote_addr
    return client_ip in ALLOWED_IPS or '*' in ALLOWED_IPS


def load_requests():
    try:
        with open('pending_tokens.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            if not rows:
                return []

            # Skip the header row and map the remaining rows
            headers = rows[0]  # First row is the header
            data_rows = rows[1:]  # The rest are data rows

            return [dict(zip(headers, row)) for row in data_rows]

    except FileNotFoundError:
        return []




@app.route('/admin-9f3k29dj2ks/dashboard')
@admin_required
def dashboard():
    return render_template('admin_panel.html', active_page='dashboard')

@app.route('/admin-9f3k29dj2ks/users')
@admin_required
def manage_users():
    try:
        users_df = pd.read_csv("users.csv")
    except FileNotFoundError:
        users_df = pd.DataFrame()

    try:
        user_data_df = pd.read_csv("user_data.csv")
    except FileNotFoundError:
        user_data_df = pd.DataFrame()

    users_data = users_df.fillna('').to_dict(orient='records')
    user_data = user_data_df.fillna('').to_dict(orient='records')

    return render_template(
        'admin_panel.html',
        active_page='users',
        users=users_data,
        user_data=user_data
    )

@app.route('/admin-9f3k29dj2ks/events')
@admin_required
def manage_events():
    try:
        events_df = pd.read_csv("events.csv")
    except FileNotFoundError:
        events_df = pd.DataFrame()

    events = events_df.fillna('').to_dict(orient='records')

    return render_template(
        'admin_panel.html',
        active_page='events',
        events=events
    )

@app.route('/admin-9f3k29dj2ks/requests')
@admin_required
def manage_requests():
    requests = load_requests()
    return render_template('admin_panel.html', active_page='requests', requests=requests)

@app.route('/admin-9f3k29dj2ks/folders')
@admin_required
def manage_folders():
    base_dir = os.getcwd()  # root of the project
    exclude_dirs = {'templates', '__pycache__'}

    folders = []
    for entry in os.listdir(base_dir):
        path = os.path.join(base_dir, entry)
        if os.path.isdir(path) and entry not in exclude_dirs:
            folders.append(entry)

    return render_template('admin_panel.html', active_page='folders', folders=folders)



@app.route('/uploads/<path:filename>')
def serve_photo1(filename):
    full_path = os.path.join(app.root_path, filename)  # Removed 'Photos_data'
    directory = os.path.dirname(full_path)
    file = os.path.basename(full_path)

    print(f"[DEBUG] Serving photo - Directory: {directory}, File: {file}")
    return send_from_directory(directory, file)



@app.route('/admin-9f3k29dj2ks/events/images/<event_name>')
def view_event_images(event_name):
    selected_event = None
    try:
        with open("events.csv", mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['name'] == event_name:
                    selected_event = row
                    break
    except Exception as e:
        print(f"[DEBUG] Error reading events.csv: {e}")
        return "Error reading event data.", 500

    if selected_event is None:
        print(f"[DEBUG] Event '{event_name}' not found in events.csv.")
        return "Event not found", 404

    event_image_path = selected_event['photo_path']
    print(f"[DEBUG] Event '{event_name}' image path from CSV: {event_image_path}")

    full_image_path = os.path.join(os.getcwd(), event_image_path)
    print(f"[DEBUG] Absolute image directory path: {full_image_path}")

    if event_image_path and os.path.exists(full_image_path):
        try:
            all_files = os.listdir(full_image_path)
            print(f"[DEBUG] Files in '{full_image_path}': {all_files}")

            image_files = [f for f in all_files if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
            print(f"[DEBUG] Filtered image files: {image_files}")
        except Exception as e:
            print(f"[DEBUG] Error listing image files: {e}")
            return "Error accessing image files.", 500

        return render_template('admin_viewphoto.html', selected_event=selected_event,
                               image_files=image_files, event_image_path=event_image_path)
    else:
        print(f"[DEBUG] Invalid path or no images found at '{full_image_path}'.")
        return "No images found for this event or invalid event path.", 404




ALL_TOKENS = ['Gold', 'Silver', 'Platinum', 'Diamond', 'Royal']

@app.route('/admin-9f3k29dj2ks/requests/action', methods=['POST'])
def handle_token_request():
    print("POST request received at /admin-9f3k29dj2ks/requests/action")
    
    # Debug: Print form data to check what is being sent
    print("Form Data:", request.form)

    # Check if the request is allowed (assuming is_allowed is implemented elsewhere)
    if not is_allowed():
        return "Forbidden", 403

    # Retrieve form data
    email = request.form.get('email')
    token_type = request.form.get('token')
    status = request.form.get('status')
    action = request.form.get('action')  # This will be 'accept' or 'reject'

    # Debug: Check if we are receiving the correct values
    print("Received values - Email:", email, "Token:", token_type, "Status:", status, "Action:", action)

    if not email or not token_type or token_type not in ALL_TOKENS:
        return "Invalid data  , chatgpt issues", 400


    # Load pending token requests
    try:
        pending_df = pd.read_csv("pending_tokens.csv")
    except FileNotFoundError:
        pending_df = pd.DataFrame(columns=["email", "token_type"])

    # Remove the request from the pending list
    pending_df = pending_df[(pending_df['email'] != email) | (pending_df['token_name'] != token_type)]
    pending_df.to_csv("pending_tokens.csv", index=False)

    # Load or create user data
    try:
        df = pd.read_csv("user_data.csv")
    except FileNotFoundError:
        df = pd.DataFrame(columns=["email", "tokens", "photos_uploaded", "events", "activity"])

    found = False
    for i, row in df.iterrows():
        if row['email'] == email:
            found = True

            # Parse tokens
            raw_tokens = row.get('tokens', '').strip()
            try:
                tokens = json.loads(raw_tokens.replace("'", '"')) if raw_tokens else {}
            except json.JSONDecodeError:
                tokens = {}

            # Parse activity
            activity = str(row.get('activity', '')).strip().lower()

            if action == 'accept':
                tokens[token_type] = tokens.get(token_type, 0) + 1
                df.at[i, 'tokens'] = json.dumps(tokens)

            df.at[i, 'activity'] = 'Token has been approved' if action == 'accept' else 'rejected'
            break

    if not found:
        new_tokens = json.dumps({token_type: 1}) if action == 'accept' else json.dumps({})
        df = df._append({
            "email": email,
            "tokens": new_tokens,
            "photos_uploaded": 0,
            "events": "",
            "activity": 'Token has been Approved' if action == 'accept' else 'rejected'
        }, ignore_index=True)

    df.to_csv("user_data.csv", index=False)
    success_message = f"Request {action}ed successfully!"

    requests = load_requests()
    return render_template('admin_panel.html', active_page='requests', requests=requests, success_message=success_message)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

