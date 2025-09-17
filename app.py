from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from uuid import uuid4
from supabase import create_client, Client
import os
from config import Config

supabase_url = Config.SUPABASE_URL
supabase_key = Config.SUPABASE_KEY

supabase: Client = create_client(supabase_url, supabase_key)

def fetch_posts():
    resources_response = supabase.table('resources').select("*").execute()
    resources = resources_response.data

    posts = []
    for resource in resources:
        status_response = supabase.table('status_updates').select("*").eq('resource_id', resource['id']).order('created_at', desc=True).limit(1).execute()
        status = status_response.data[0] if status_response.data else None

        # Get upvote count by counting rows
        upvotes_response = supabase.table('upvotes').select('id', count='exact').eq('resource_id', resource['id']).execute()
        upvotes_count = upvotes_response.count if hasattr(upvotes_response, 'count') else len(upvotes_response.data)

        post = {
            'id': resource['id'],
            'title': resource['name'],
            'image_url': resource['image_url'],
            'description': status['status_message'] if status else '',
            'upvotes': upvotes_count,
            'comments': 0,  # Update if you track comments
            'crowd': status['crowd_level'] if status else '',
            'chips': status['chips_available'] if status else '',
            'queue': status['queue_length'] if status else ''
        }
        posts.append(post)
    posts.sort(key=lambda x: x['upvotes'], reverse=True)
    return posts
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']


@app.route('/upvote', methods=['POST'])
def upvote():
    if 'username' not in session:
        return jsonify({'error': 'Login required'}), 401

    resource_id = request.json.get('resource_id')
    user_id = session.get('user_id')  # you'll want to store this at login

    # Prevent double upvote
    result = supabase.table('upvotes').select('*').eq('resource_id', resource_id).eq('user_id', user_id).execute()
    if result.data:
        return jsonify({'error': 'Already upvoted'}), 409

    supabase.table('upvotes').insert({
        'id': str(uuid4()),
        'resource_id': resource_id,
        'user_id': user_id
    }).execute()
    # Return new upvote count
    count = supabase.table('upvotes').select('id', count='exact').eq('resource_id', resource_id).execute().count
    return jsonify({'success': True, 'upvotes': count})

# Supabase configuration
supabase_url: str = app.config['SUPABASE_URL']
supabase_key: str = app.config['SUPABASE_KEY']
supabase: Client = create_client(supabase_url, supabase_key)

# Custom decorator to check if user is logged in
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Custom decorator to check if user is admin
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('indexed'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    posts = fetch_posts()
    return render_template('index.html', posts=posts, username=session.get('username'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = supabase.auth.sign_in_with_password({"email": username, "password": password})
            if user:
                session['username'] = username
                session['is_admin'] = False  # Assuming no admin role for now
                session['user_id'] = user.user.id  # Store user_id in session
                return redirect(url_for('profile'))
            else:
                return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            return render_template('login.html', error=str(e))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = supabase.auth.sign_up({"email": username, "password": password})
            if user:
                session['username'] = username
                session['user_id'] = user.user.id  # Store user_id in session
                return redirect(url_for('profile'))
            else:
                return render_template('register.html', error="Registration failed")
        except Exception as e:
            return render_template('register.html', error=str(e))
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=session['username'])

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/update_post/<post_id>', methods=['POST'])
@login_required
def update_post(post_id):
    description = request.form['description']
    crowd = request.form['crowd']
    chips = request.form['chips']
    queue = request.form['queue']

    # Check if a status update exists for the resource
    status_response = supabase.table('status_updates').select("*").eq('resource_id', post_id).execute()
    status = status_response.data

    if status:
        # Update the existing status update
        supabase.table('status_updates').update({
            'crowd_level': crowd,
            'chips_available': chips,
            'queue_length': queue,
            'status_message': description
        }).eq('resource_id', post_id).execute()
    else:
        # Create a new status update
        supabase.table('status_updates').insert({
            'id': str(uuid4()),
            'resource_id': post_id,
            'crowd_level': crowd,
            'chips_available': chips,
            'queue_length': queue,
            'status_message': description
        }).execute()

    return redirect(url_for('index'))

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        print("create_post function called")
        title = request.form['title']
        description = request.form['description']
        crowd = request.form['crowd']
        chips = request.form['chips']
        queue = request.form['queue']

        # Insert new resource
        resource_data = {
            'id': str(uuid4()),
            'name': title,
        }
        print("Image upload code should not be executed")
        supabase.table('resources').insert(resource_data).execute()

        # Insert initial status update
        status_data = {
            'id': str(uuid4()),
            'resource_id': resource_data['id'],
            'status_message': description,
            'crowd_level': crowd,
            'chips_available': chips,
            'queue_length': queue,
        }
        supabase.table('status_updates').insert(status_data).execute()

        return redirect(url_for('index'))
    return render_template('create_post.html')

if __name__ == '__main__':
    app.run(debug=True)
