from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'expense-manager-secret-key')

# Database configuration - use PostgreSQL if DATABASE_URL is set, otherwise SQLite
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

from app import routes, models

with app.app_context():
    db.create_all()
