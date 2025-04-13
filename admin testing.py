from flask import Flask, request, Response, render_template ,redirect , url_for , send_from_directory
import os
import pandas as pd
import json
import csv

app = Flask(__name__)

# Secure admin path (random)
SECURE_ADMIN_PATH = "admin-9f3k29dj2ks"
USERNAME = "admin"
PASSWORD = "admin12"
ALLOWED_IPS = ['127.0.0.1']  # Set your allowed IPs here
BASE_FOLDER_PATH = './'  # Relative path to the current directory


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
def dashboard():
    return render_template('admin_panel.html', active_page='dashboard')

@app.route('/admin-9f3k29dj2ks/users')
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
def manage_requests():
    requests = load_requests()
    return render_template('admin_panel.html', active_page='requests', requests=requests)

@app.route('/admin-9f3k29dj2ks/folders')
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
def serve_photo(filename):
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




if __name__ == '__main__':
    app.run(debug=True)
