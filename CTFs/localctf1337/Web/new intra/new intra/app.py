import os
import uuid
import random
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(64)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per minute"],
    storage_uri="memory://"
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

COALITIONS = [
    {"name": "The Alliance", "color": "#33C47F", "cover": "https://cdn.intra.42.fr/coalition/cover/46/alliance_background.jpg", "icon": "M353.2,241.3c-12.8,4.3-25.6,10-37,17.1c35.6,28.5,59.8,69.7,62.6,116.7c0,5.7,0,10,0,15.7 c0,14.2-1.4,28.5-5.7,41.3c-10,38.4-34.2,72.6-65.5,95.4c-15.7,11.4-32.7,19.9-51.2,24.2c-15.7,4.3-29.9,7.1-45.5,7.1 c-92.5,0-167.9-75.4-167.9-166.5c0-44.1,17.1-85.4,48.4-116.7c-1.4-17.1-2.8-32.7-2.8-47v-1.4C37.2,265.5,7.3,325.3,7.3,389.3 c0,112.4,92.5,204.9,204.9,204.9c31.3,0,62.6-7.1,91.1-21.3c17.1-8.5,34.2-19.9,48.4-32.7c39.9-35.6,62.6-84,65.5-136.6 c0-5.7,0-8.5,0-14.2c0-15.7-1.4-29.9-5.7-44.1C403,305.4,383.1,269.8,353.2,241.3z M522.5,227.1c0,15.7-1.4,31.3-4.3,45.5c31.3,31.3,48.4,72.6,48.4,116.7c0,92.5-75.4,166.5-167.9,166.5c-14.2,0-28.5-1.4-42.7-5.7 c-11.4,10-24.2,18.5-37,27c25.6,10,51.2,15.7,79.7,15.7c112.4,0,204.9-91.1,204.9-204.9C603.7,325.3,573.8,265.5,522.5,227.1z M398.7,184.4c-31.3,0-62.6,7.1-91.1,21.3c-17.1,8.5-34.2,19.9-48.4,32.7c-31.3,28.5-52.7,65.5-61.2,106.7 c-2.8,14.2-4.3,28.5-4.3,44.1c0,4.3,0,8.5,0,14.2c2.8,51.2,25.6,99.6,64,135.2c12.8-4.3,25.6-10,37-17.1 c-28.5-22.8-49.8-54.1-58.4-89.7c-2.8-14.2-5.7-28.5-5.7-42.7c0-5.7,0-10,0-15.7c5.7-48.4,31.3-92.5,71.2-121 c15.7-11.4,32.7-19.9,51.2-24.2c15.7-4.3,29.9-7.1,45.5-7.1c21.3,0,42.7,4.3,61.2,11.4v-5.7c0-11.4-1.4-24.2-4.3-34.2 C438.6,187.2,418.6,184.4,398.7,184.4z M306.2,396.5c-21.3,0-42.7-4.3-61.2-11.4v5.7c0,11.4,1.4,24.2,4.3,34.2 c17.1,5.7,37,8.5,56.9,8.5c19.9,0,39.9-2.8,58.4-8.5c2.8-11.4,4.3-22.8,4.3-34.2v-7.1C347.5,392.2,327.6,396.5,306.2,396.5z M306.2,23.6c-108.2,0-197.8,84-204.9,192.1c0,5.7,0,8.5,0,12.8c0,15.7,1.4,29.9,5.7,44.1c10,47,37,88.2,74,118.1v-1.4 c0-14.2,1.4-29.9,4.3-44.1c-25.6-27-42.7-64-47-101.1c0-5.7,0-10,0-15.7c0-14.2,1.4-28.5,5.7-41.3C162.5,113.2,229.4,62,306.2,62 S450,113.2,468.5,187.2c2.8,14.2,5.7,27,5.7,41.3c0,5.7,0,10,0,15.7c-2.8,38.4-19.9,74-47,101.1c2.8,14.2,4.3,29.9,4.3,44.1v1.4 c38.4-29.9,65.5-71.2,75.4-118.1c2.8-15.7,5.7-29.9,5.7-44.1c0-4.3,0-8.5,0-14.2C504,107.5,413,23.6,306.2,23.6z M212.3,184.4c-19.9,0-39.9,2.8-58.4,8.5c-2.8,11.4-4.3,22.8-4.3,34.2v7.1c19.9-8.5,41.3-11.4,61.2-11.4c14.2,0,28.5,1.4,42.7,5.7 c11.4-10,24.2-18.5,37-27C266.4,190.1,239.3,184.4,212.3,184.4z"},
    {"name": "The Order", "color": "#f5bc39", "cover": "https://cdn.intra.42.fr/coalition/cover/47/order_background.jpg", "icon": "M305.5,568.6L181.7,496v-86.8l123.8,72.6l152.3-88.2l74-42.7v85.4L305.5,568.6L305.5,568.6z M79.2,172.9l125.2-72.6l72.6,44.1l-123.8,71.2l-1.4,263.3l-72.6-42.7C79.2,436.3,79.2,172.9,79.2,172.9z M305.5,163l89.7,52.7 l32.7,18.5v140.9l-123.8,71.2l-121-71.2V232.7L305.5,163L305.5,163z M530.4,172.9v143.7l-74,42.7V215.6l-47-27L314,131.7l-81.1-49.8 l71.2-41.3L530.4,172.9z M305.5,6.4L49.3,155.9v298.9l256.2,149.4l256.2-149.4V155.9L305.5,6.4L305.5,6.4z"},
    {"name": "The Assembly", "color": "#e74c3c", "cover": "https://cdn.intra.42.fr/coalition/cover/48/assembly_background.jpg", "icon": "M532.8,531.5c61.2-61.2,65.5-156.6,12.8-223.5c-4.3-4.3-7.1-8.5-12.8-14.2l-14.2-14.2L334.9,97.4 c-4.3,2.8-7.1,7.1-11.4,10l-10,10l199.3,199.3c4.3,4.3,8.5,10,14.2,15.7c39.9,54.1,34.2,132.4-14.2,179.3 c-25.6,25.6-61.2,39.9-96.8,39.9c-28.5,0-55.5-8.5-78.3-24.2L325,540c-2.8,2.8-7.1,5.7-10,8.5c28.5,21.3,64,32.7,99.6,32.7 C458.7,581.3,501.4,564.2,532.8,531.5L532.8,531.5z M494.3,313.7l-185,185L295.1,513c-4.3,2.8-10,8.5-15.7,12.8 c-24.2,17.1-52.7,27-82.5,27c-37,0-71.2-14.2-96.8-39.9c-47-47-54.1-122.4-15.7-176.5l-12.8-12.8c-2.8-2.8-5.7-7.1-8.5-10 c-49.8,66.9-42.7,159.4,15.7,217.8c31.3,31.3,74,48.4,118.1,48.4c38.4,0,75.4-12.8,103.9-37c4.3-4.3,8.5-7.1,14.2-12.8l14.2-14.2 L512.8,335c-2.8-4.3-7.1-7.1-10-11.4L494.3,313.7L494.3,313.7z M101.5,295.2c-4.3-4.3-8.5-10-14.2-15.7 c-39.9-54.1-34.2-132.4,14.2-179.3c25.6-25.6,59.8-39.9,96.8-39.9c28.5,0,55.5,8.5,78.3,24.2l12.8-12.8c2.8-2.8,7.1-5.7,10-8.5 c-28.5-21.3-64-32.7-99.6-32.7c-44.1,0-86.8,17.1-118.1,48.4c-61.2,61.2-65.5,156.6-12.8,223.5c4.3,4.3,7.1,8.5,12.8,14.2 l197.8,197.8c4.3-2.8,7.1-7.1,11.4-10l10-10l-185-185L101.5,295.2L101.5,295.2z M296.5,80.3c5.7-5.7,10-8.5,14.2-12.8 c28.5-24.2,65.5-37,103.9-37c44.1,0,86.8,17.1,118.1,48.4c58.4,59.8,65.5,152.3,15.7,219.2c-2.8-2.8-5.7-7.1-8.5-10l-12.8-14.2 c38.4-54.1,31.3-129.5-15.7-176.5c-25.6-25.6-59.8-39.9-96.8-39.9c-29.9,0-58.4,10-82.5,27c-5.7,5.7-11.4,10-15.7,14.2L117.2,298 l-10-10c-2.8-2.8-5.7-7.1-8.5-10L296.5,80.3L296.5,80.3z"},
    {"name": "The Federation", "color": "#4180DB", "cover": "https://cdn.intra.42.fr/coalition/cover/45/federation_background.jpg", "icon": "M323.8,497.3l-12.4,21l-5,7.4l-4.9-7.4l-14.8-23.5l-29.6-48.2L121.2,220.6c-2.5,12.4-3.7,24.7-3.7,35.8 c0,7.4,0,16.1,1.2,24.7l77.8,127.3l42,70.4L306.5,590l60.5-98.9C352.2,493.6,337.4,496.1,323.8,497.3L323.8,497.3z M320.1,487.4 h-24.7l-21-35.8c11.1,1.2,21,2.5,32.1,2.5c14.8,0,29.7-1.2,44.5-4.9c25.9-6.2,50.7-17.3,72.9-33.4c43.2-32.1,72.9-79.1,80.3-131 l34.6-53.1c1.2,8.6,1.2,18.5,1.2,27.2c0,100.1-65.5,187.8-163.1,218.7C358.4,482.5,339.9,486.2,320.1,487.4L320.1,487.4z M148.4,136.5c-16.1,19.8-27.2,43.2-34.6,68c-4.9,16.1-7.4,34.6-7.4,51.9c0,8.7,0,18.5,1.2,27.2c7.4,51.9,35.8,100.1,79.1,131 l34.6,56.8C132.3,436.8,73,352.8,73,257.6c0-14.8,1.2-29.7,3.7-43.3c3.7-18.5,8.7-37.1,17.3-54.4c5-7.4,8.7-16.1,13.6-23.5H148.4 L148.4,136.5z M606.8,92.1l-71.7,118.6l-42,69.2l-77.8,127.3c-17.3,12.4-35.8,21-55.6,27.2L498,210.7l29.6-48.2l16.1-27.2l4.9-8.7 h-38.3c-7.4-12.4-16.1-23.5-25.9-33.4v-1.2H606.8L606.8,92.1z M4.2,92l391.2,0.1c16.1,9.9,30.9,19.8,44.5,33.4H64.3l4.9,8.6 l14.8,24.7C77.9,172.4,73,186,69.3,199.5L4.2,92z M213.8,80.9h-59.3c42-34.6,95.1-54.4,150.8-54.4c60.5,0,118.6,22.2,161.9,64.3 c13.6,13.6,25.9,28.4,35.8,43.2c4.9,7.4,9.9,16.1,12.4,21l-21,35.8c-8.7-23.5-21-45.7-38.3-65.5C440,108.1,420.2,92.1,398,80.9 c-28.4-14.8-60.5-22.2-92.7-22.2C274.4,58.7,242.3,67.3,213.8,80.9z"},
]

TITLES = ["Mastermind", "The Hacker", "Philanthropist", "Writer's soul"]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

users = {
    "1": {
        "id": "1",
        "username": "bocal",
        "password": os.urandom(64),
        "bio": "[DEPRECATED]",
        "avatar": "/static/bocal_avatar1.gif",
        "role": "admin",
        "wallet": "9999999999999999",
        "cursus": "bocal",
        "grade": "Staff",
        "evaluation_points": 1337421337,
        "join_date": "Nov 2018",
        "coalition": COALITIONS[0]
    },
    "2": {
        "id": "2",
        "username": "staff",
        "password": os.urandom(64),
        "bio": "[DEPRECATED]",
        "avatar": "/static/bocal_avatar5.gif",
        "role": "admin",
        "wallet": "133713371337",
        "cursus": "staff",
        "grade": "Staff",
        "evaluation_points": 99999,
        "join_date": "Dec 2020",
        "coalition": COALITIONS[1]
    },
    "3": {
        "id": "3",
        "username": "admin",
        "password": os.urandom(64),
        "bio": "Mastermind",
        "avatar": "/static/bocal_avatar3.jpeg",
        "role": "admin",
        "wallet": "4242424242",
        "cursus": "admin",
        "grade": "God",
        "evaluation_points": 1337,
        "join_date": "Jan 2000",
        "coalition": COALITIONS[2]
    },
    "4": {
        "id": "4",
        "username": "test",
        "password": os.urandom(64),
        "bio": "The Hacker",
        "avatar": "/static/bocal_avatar4.jpeg",
        "role": "admin",
        "wallet": "31337",
        "cursus": "test",
        "grade": "Test",
        "evaluation_points": -42,
        "join_date": "Dec 1444",
        "coalition": COALITIONS[3]
    },
    "5": {
        "id": "5",
        "username": "user",
        "password": os.urandom(64),
        "bio": "The Hacker",
        "avatar": "/static/bocal_avatar6.jpg",
        "role": "admin",
        "wallet": "999999",
        "cursus": "user",
        "grade": "User",
        "evaluation_points": 10000,
        "join_date": "May 1937",
        "coalition": COALITIONS[0]
    },
    "6": {
        "id": "6",
        "username": "flag",
        "password": os.urandom(64),
        "bio": "Mastermind",
        "avatar": "/static/bocal_avatar2.jpeg",
        "role": "admin",
        "wallet": "0",
        "cursus": "flag",
        "grade": "Flag Holder",
        "evaluation_points": -6969,
        "join_date": "Feb 1945",
        "coalition": COALITIONS[1]
    }
}

next_user_id = 7

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per second")
def register():
    global next_user_id
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
        
    for u in users.values():
        if u['username'] == username:
            return jsonify({"error": "Username already taken"}), 400
            
    user_id = str(next_user_id)
    next_user_id += 1

    coalition = random.choice(COALITIONS)
    
    users[user_id] = {
        "id": user_id,
        "username": username,
        "password": password,
        "bio": "The Hacker",
        "avatar": "/static/default.png",
        "role": "user",
        "wallet": "0",
        "cursus": "1337cursus",
        "grade": "Cadet",
        "evaluation_points": 0,
        "join_date": "May 2026",
        "coalition": coalition
    }
    
    session['user_id'] = user_id
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per second")
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    for uid, u in users.items():
        if u['username'] == username and u['password'] == password:
            if u['role'] == 'admin':
                return jsonify({"error": "Use the staff portal to sign in."}), 403
            session['user_id'] = uid
            return jsonify({"success": True})
            
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/staff', methods=['POST'])
@limiter.limit("5 per second")
def api_staff():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    builtin_ids = {'1', '2', '3', '4', '5', '6'}
    for uid, u in users.items():
        if u['username'] == username:
            pw = session.get('bocal_pw', u['password']) if uid in builtin_ids else u['password']
            if pw == password:
                if u['role'] != 'admin':
                    return jsonify({"error": "Use the student portal to sign in."}), 403
                session['user_id'] = uid
                return jsonify({"success": True})
            
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    current_user = users.get(session['user_id'])
    
    search_query = request.args.get('query')
    if search_query:
        found_user = None
        for u in users.values():
            if u['username'].lower() == search_query.lower():
                found_user = u
                break
        if found_user:
            return render_template('dashboard.html', user=current_user, profile_user=found_user, search_query=search_query, is_own_profile=False)
        else:
            return render_template('dashboard.html', user=current_user, profile_user=current_user, search_error=f"There is no such a user under '{search_query}'", is_own_profile=True)
    
    return render_template('dashboard.html', user=current_user, profile_user=current_user, is_own_profile=True)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = users.get(session['user_id'])
    
    if request.method == 'POST':
        password = request.form.get('password')
        bio = request.form.get('bio')
        
        if password:
            if user['id'] == '1':
                session['bocal_pw'] = password
            else:
                user['password'] = password
        if bio and bio in TITLES:
            user['bio'] = bio
        
        if 'avatar_file' in request.files:
            file = request.files['avatar_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{user['id']}_{file.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                user['avatar'] = f"/static/uploads/{filename}"
            
        return redirect(url_for('dashboard'))
        
    return render_template('settings.html', user=user, titles=TITLES)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = users.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/api/profile/<user_id>', methods=['PUT'])
def update_profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404

    builtin_ids = {'1', '2', '3', '4', '5', '6'}
    if user_id != session['user_id'] and user_id not in builtin_ids:
        return jsonify({"error": "You can only modify your own profile"}), 403
        
    data = request.json
    allowed_fields = ['password', 'bio', 'username']
    
    for key in data:
        if key not in allowed_fields:
            return jsonify({"error": f"Field '{key}' is not allowed"}), 403
    
    if 'username' in data:
        new_username = data['username']
        for u in users.values():
            if u['username'].lower() == new_username.lower() and u['id'] != user_id:
                return jsonify({"error": "Username already taken"}), 400
        users[user_id]['username'] = new_username
    
    if 'password' in data:
        session['bocal_pw'] = data['password']
    if 'bio' in data:
        users[user_id]['bio'] = data['bio']
    
    user_data = users[user_id].copy()
    user_data.pop('password', None)
    
    return jsonify({"success": True, "user": user_data})

@app.route('/staff')
def staff():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('staff.html')

@app.route('/flag')
def flag():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return jsonify({"error": "You are not authorized to view this page"}), 403

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    user = users.get(session['user_id'])

    if user['username'] != 'bocal' or user['id'] != '1':
        return render_template('admin.html', error="Access Denied: Only the 'staff' account can view this page", flag=None, user=user)
        
    try:
        with open('flag.txt', 'r') as f:
            flag_content = f.read().strip()
    except FileNotFoundError:
        flag_content = "flag{not_found}"
        
    return render_template('admin.html', flag=flag_content, user=user)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1338, debug=False)
