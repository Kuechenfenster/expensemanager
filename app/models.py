from app import db
from datetime import datetime

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500))
    vendor = db.Column(db.String(200))
    invoice_filename = db.Column(db.String(300))
    ocr_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'vendor': self.vendor,
            'invoice_filename': self.invoice_filename,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    @staticmethod
    def get_default_categories():
        return ['Transport', 'Meals', 'Hotel', 'Mobile Phone', 'Office Supplies', 'Software', 'Other']
