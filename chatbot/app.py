from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS 
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Enhanced CORS configuration
CORS(app, 
     resources={
         r"/*": {
             "origins": ["http://localhost:8000", "http://localhost:5005"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }
     })

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'  # Change this in production

db = SQLAlchemy(app)

# User model
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, email, password):
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

# JWT token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(email=data['email']).first()
        except:
            return jsonify({'error': 'Token is invalid'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# Create DB tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return "Backend is running"

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 409

    new_user = User(email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Create JWT token
    token = jwt.encode({
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'email': user.email
    }), 200

@app.route('/protected', methods=['GET'])
@token_required
def protected_route(current_user):
    return jsonify({
        'message': f'Hello {current_user.email}!',
        'email': current_user.email
    })

@app.route('/rasa-webhook', methods=['POST'])
@token_required
def rasa_webhook(current_user):
    data = request.get_json()
    
    # Forward to Rasa with the authenticated email as sender_id
    import requests
    response = requests.post(
        'http://localhost:5005/webhooks/rest/webhook',
        json={
            "sender": current_user.email,  # This becomes tracker.sender_id in Rasa
            "message": data.get('message', '')
        }
    )
    
    return jsonify(response.json())

@app.route('/home')
def serve_home():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
    return send_from_directory('../frontend', 'home.html')


if __name__ == '__main__':
    app.run(debug=True)