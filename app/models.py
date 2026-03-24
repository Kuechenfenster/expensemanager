from app import db
from datetime import datetime
import json

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    vendor = db.Column(db.String(100))
    invoice_filename = db.Column(db.String(255))
    ocr_text = db.Column(db.Text)
    ocr_confidence = db.Column(db.Float)  # Store OCR confidence score
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'vendor': self.vendor,
            'invoice_filename': self.invoice_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_all_categories():
        cats = Category.query.order_by(Category.name).all()
        return [cat.name for cat in cats]
    
    @staticmethod
    def get_default_categories():
        defaults = ['Transport', 'Meals', 'Hotel', 'Mobile Phone', 'Office Supplies', 'Software', 'Other']
        
        for cat_name in defaults:
            if not Category.query.filter_by(name=cat_name).first():
                cat = Category(name=cat_name, is_default=True)
                db.session.add(cat)
        db.session.commit()
        
        return Category.get_all_categories()
    
    @staticmethod
    def add_custom_category(name):
        name = name.strip()
        if not name:
            return False, "Category name cannot be empty"
        
        existing = Category.query.filter(db.func.lower(Category.name) == name.lower()).first()
        if existing:
            return False, "Category already exists"
        
        cat = Category(name=name, is_default=False)
        db.session.add(cat)
        db.session.commit()
        return True, cat.name

class InvoicePattern(db.Model):
    """Store invoice patterns for OCR improvement"""
    __tablename__ = 'invoice_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), index=True)  # Normalized vendor name
    pattern_type = db.Column(db.String(20))  # 'amount', 'date', 'vendor'
    pattern_text = db.Column(db.Text)  # The text pattern found
    context_before = db.Column(db.String(200))  # Text before the value
    context_after = db.Column(db.String(200))  # Text after the value
    success_count = db.Column(db.Integer, default=1)  # How many times this pattern worked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def learn_pattern(vendor, pattern_type, value, full_text):
        """Learn from corrected invoice data"""
        # Find context around the value
        value_pos = full_text.lower().find(str(value).lower())
        if value_pos == -1:
            return
        
        context_before = full_text[max(0, value_pos-50):value_pos].strip()
        context_after = full_text[value_pos+len(str(value)):value_pos+len(str(value))+50].strip()
        
        # Normalize vendor name
        vendor_key = vendor.lower().strip() if vendor else 'unknown'
        
        # Check if similar pattern exists
        existing = InvoicePattern.query.filter_by(
            vendor_name=vendor_key,
            pattern_type=pattern_type
        ).first()
        
        if existing:
            existing.success_count += 1
            existing.last_used = datetime.utcnow()
        else:
            pattern = InvoicePattern(
                vendor_name=vendor_key,
                pattern_type=pattern_type,
                pattern_text=str(value),
                context_before=context_before,
                context_after=context_after
            )
            db.session.add(pattern)
        
        db.session.commit()
    
    @staticmethod
    def get_patterns_for_vendor(vendor):
        """Get learned patterns for a vendor"""
        if not vendor:
            return []
        vendor_key = vendor.lower().strip()
        return InvoicePattern.query.filter_by(vendor_name=vendor_key).order_by(
            InvoicePattern.success_count.desc()
        ).all()

class OCRExtraction(db.Model):
    """Store OCR extractions with corrections for audit and learning"""
    __tablename__ = 'ocr_extractions'
    
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'))
    original_amount = db.Column(db.Float)
    corrected_amount = db.Column(db.Float)
    original_date = db.Column(db.String(20))
    corrected_date = db.Column(db.String(20))
    original_vendor = db.Column(db.String(100))
    corrected_vendor = db.Column(db.String(100))
    full_text = db.Column(db.Text)  # Full OCR text
    confidence_score = db.Column(db.Float)
    was_corrected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    expense = db.relationship('Expense', backref='ocr_correction')
