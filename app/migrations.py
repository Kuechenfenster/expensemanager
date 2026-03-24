"""Database migration script to add new columns to existing tables."""
from sqlalchemy import text, create_engine
import os
from app.models import InvoicePattern, OCRExtraction, db

def migrate():
    """Run database migrations."""
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/local.db')
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check if we're using PostgreSQL
        if 'postgresql' in database_url:
            # Add ocr_confidence column to expenses table if missing
            try:
                conn.execute(text("""
                    ALTER TABLE expenses 
                    ADD COLUMN IF NOT EXISTS ocr_confidence FLOAT,
                    ADD COLUMN IF NOT EXISTS ocr_text TEXT
                """))
                print("✅ Added ocr_confidence and ocr_text columns")
            except Exception as e:
                print(f"Info: Columns may already exist: {e}")
                
            # Create invoice_patterns table if missing
            try:
                conn.execute(text("""
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
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_invoice_patterns_vendor 
                    ON invoice_patterns(vendor_name)
                """))
                print("✅ Created invoice_patterns table")
            except Exception as e:
                print(f"Info: invoice_patterns table may exist: {e}")
                
            # Create ocr_extractions table if missing
            try:
                conn.execute(text("""
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
                print("✅ Created ocr_extractions table")
            except Exception as e:
                print(f"Info: ocr_extractions table may exist: {e}")
                
        conn.commit()
    
    # Create all tables using SQLAlchemy (for SQLite and fallback)
    db.create_all()
    print("✅ Database migration complete")

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        migrate()
