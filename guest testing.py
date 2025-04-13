import os
import face_recognition
import shutil
from flask import Flask, render_template, request, session, redirect
import csv 
import json

app = Flask(__name__)
app.secret_key = 'secret-key'

TEMP_GUEST_PHOTOS_FOLDER = "static/temp_guest_photos"

if not os.path.exists(TEMP_GUEST_PHOTOS_FOLDER):
    os.makedirs(TEMP_GUEST_PHOTOS_FOLDER)



# Debug logging function
def debug_log(message):
    print(f"[DEBUG] {message}")


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
        debug_log(f"📁 Created event photo folder at: {event_photos_folder}")

    debug_log(f"📤 Loading guest image from: {guest_image_path}")
    guest_image = face_recognition.load_image_file(guest_image_path)
    guest_encoding = face_recognition.face_encodings(guest_image)

    if len(guest_encoding) == 0:
        debug_log("❌ No face found in the guest image.")
        return [], "No face found in the image."

    guest_encoding = guest_encoding[0]
    matching_photos = []

    debug_log("🔍 Starting to compare with host photos...")
    
    if not os.path.exists(photo_folder):
        debug_log(f"⚠️ Photo folder does not exist: {photo_folder}")
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
                debug_log(f"📊 Comparing to {filename} → Accuracy: {accuracy}")

                if accuracy >= 0.6:
                    debug_log(f"✅ Match found: {filename} (Accuracy: {accuracy})")
                    match_found = True
                    break

            if match_found:
                shutil.copy(image_path, os.path.join(event_photos_folder, filename))
                matching_photos.append(filename)

    debug_log(f"🎯 Total matches found: {len(matching_photos)}")
    return matching_photos, None if matching_photos else "No matching photos found in the event."


@app.route('/guest/<event_id>', methods=['GET', 'POST'])
def guest_view(event_id):
    error = None
    selected_event = None
    photo_uploaded = False
    matching_photos = []

    debug_log(f"🔎 Checking for event: {event_id}")

    with open('user_data.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_events = json.loads(row['events']) if row['events'] else []
            for event in all_events:
                if event['id'] == event_id:
                    selected_event = event
                    debug_log(f"✅ Event found: {selected_event}")
                    break
            if selected_event:
                break

    if not selected_event:
        debug_log("❌ Event not found.")
        return "Event not found", 404

    unlocked_key = f'unlocked_{event_id}'

    # Password handling
    if request.method == 'POST' and not session.get(unlocked_key):
        password_entered = request.form.get('password')
        correct_password = selected_event.get('password', 'WD1234')
        debug_log(f"🔐 Entered password: {password_entered}")
        if password_entered == correct_password:
            session[unlocked_key] = True
            debug_log("✅ Password correct. Access granted.")
        else:
            error = "Incorrect password."
            debug_log("❌ Incorrect password.")
            return render_template(
                'guest_combined.html',
                selected_event=selected_event,
                require_password=True,
                error=error
            )

    if not session.get(unlocked_key):
        debug_log("🔒 Password not yet entered. Showing password prompt.")
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
            debug_log(f"📤 Guest photo uploaded to: {guest_image_path}")

            matching_photos, error_msg = find_matching_photos_and_transfer(guest_image_path, event_id)
            photo_uploaded = True

            if error_msg:
                error = error_msg
                debug_log(f"❌ Error after matching: {error}")
            else:
                debug_log("✅ Matching completed with results.")

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
    debug_log("👁 Viewing event page without photo uploaded.")
    return render_template(
        'guest_combined.html',
        selected_event=selected_event,
        require_password=False,
        error=None,
        photo_uploaded=photo_uploaded,
        photos=matching_photos,
        upload_disabled=False
    )



import zipfile
from io import BytesIO
from flask import send_file

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


if __name__ == '__main__':
    app.run(debug=True)
