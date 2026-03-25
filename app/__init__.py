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
from app.models import Expense, Category, InvoicePattern, OCRExtraction

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
                ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR'
            """))
            
            # Ensure new tables exist
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS invoice_patterns (
                    id SERIAL PRIMARY KEY,
                    vendor_name VARCHAR(100),
                    pattern_type VARCHAR(20),
                    pattern_text TEXT,
                    context_before VARCHAR(200),
                    context_after VARCHAR(200),
                    success_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS ocr_extractions (
                    id SERIAL PRIMARY KEY,
                    expense_id INTEGER REFERENCES expenses(id),
                    original_amount FLOAT,
                    corrected_amount FLOAT,
                    original_date VARCHAR(20),
                    corrected_date VARCHAR(20),
                    original_vendor VARCHAR(100),
                    corrected_vendor VARCHAR(100),
                    full_text TEXT,
                    confidence_score FLOAT,
                    was_corrected BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            db.session.commit()
            print("✅ Database schema updated")
        except Exception as e:
            db.session.rollback()
            print(f"Migration note: {e}")
    
    # Initialize default categories
    from app.models import Category
    Category.get_default_categories()

# Import routes at end to avoid circular imports
from app import routes
