from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash,session
import face_recognition
import os
import uuid
import shutil
import requests
import csv
import json

app = Flask(__name__)
app.secret_key = "super_secure_party_pix_secret_2024" # Required for flashing messages

UPLOAD_FOLDER = "uploads"
MATCH_FOLDER = "matches"
DATASET_FOLDER = "wedding_photos"
USER_DB = "users.csv"


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MATCH_FOLDER, exist_ok=True)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1359406881914884147/jkynHq0DsAZA__f7IqqtRU9w1IrzU1R-8v1pzis9cZcY5D0G-P6yUonDgePUdqkwMylh"


@app.route('/')
def home():
    # session.pop('_flashes', None)  # Clear any flash messages
    session.pop('user', None)      # Log out user if they were logged in
    return render_template('index.html')

@app.route('/')
def error():
    return render_template('index.html')

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

    # Read the user data
    user_data = None
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['email'] == email:
                # Convert events and activity from stringified JSON
                row['events'] = json.loads(row['events']) if row['events'] else []
                row['activity'] = json.loads(row['activity']) if row['activity'] else []
                user_data = row
                break

    return render_template('user.html', user_data=user_data)




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
    with open('users.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users[row['email']] = row['password']
    return users


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    users = load_users()  # Returns a dictionary { email: password }

    if email not in users:
        flash('No account found with this email.', 'error')
        return redirect(url_for('error') + '#loginModal')

    if users[email] != password:
        flash('Incorrect password. Please try again.', 'error')
        return redirect(url_for('error') + '#loginModal')

    # If all is well
    session['user'] = email
    flash('Logged in successfully!', 'success')
    return redirect(url_for('userlogged'))
    


@app.route("/register", methods=["POST"])
def register():
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
            writer.writerow(["email", "password"])

    # Check if user already exists
    with open(USER_DB, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["email"] == email:
                flash("User already exists.", "error")
                return redirect(url_for('error') + '#registerModal')
                

    # Save new user
    with open(USER_DB, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([email, password])

    flash("Registration successful! You can now log in.", "success")
    return redirect(url_for('home') + '#loginModal')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('_flashes', None)
    return redirect(url_for('home'))

    
@app.route('/matches/<filename>')
def matched_file(filename):
    return send_from_directory(MATCH_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

