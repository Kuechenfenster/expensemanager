from app import db
from datetime import datetime

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
        """Get all categories (default + custom)"""
        cats = Category.query.order_by(Category.name).all()
        return [cat.name for cat in cats]
    
    @staticmethod
    def get_default_categories():
        """Get or create default categories"""
        defaults = ['Transport', 'Meals', 'Hotel', 'Mobile Phone', 'Office Supplies', 'Software', 'Other']
        
        # Ensure defaults exist in database
        for cat_name in defaults:
            if not Category.query.filter_by(name=cat_name).first():
                cat = Category(name=cat_name, is_default=True)
                db.session.add(cat)
        db.session.commit()
        
        return Category.get_all_categories()
    
    @staticmethod
    def add_custom_category(name):
        """Add a new custom category"""
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
    
    @staticmethod
    def delete_category(name):
        """Delete a custom category (not default)"""
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            return False, "Category not found"
        if cat.is_default:
            return False, "Cannot delete default category"
        
        db.session.delete(cat)
        db.session.commit()
        return True, "Category deleted"
