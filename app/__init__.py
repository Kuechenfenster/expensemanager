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

# Import models before creating tables
from app.models import Expense, Category, User, InvoicePattern, OCRExtraction

# Create all tables/columns on startup
with app.app_context():
    db.create_all()  # Creates new tables and adds missing columns for SQLite

    # Run migrations for PostgreSQL
    if 'postgresql' in str(app.config['SQLALCHEMY_DATABASE_URI']):
        from sqlalchemy import text
        try:
            # Add missing columns for PostgreSQL
            db.session.execute(text("""
                ALTER TABLE expenses
                ADD COLUMN IF NOT EXISTS ocr_confidence FLOAT,
                ADD COLUMN IF NOT EXISTS ocr_text TEXT,
                ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'HKD',
                ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
            """))

            # Create users table if not exists
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            db.session.commit()
            print("✅ Database schema updated")
        except Exception as e:
            print(f"Migration note: {e}")
            db.session.rollback()

# Import routes after app and db are initialized
from app import routes
