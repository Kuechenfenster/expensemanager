import datetime
from app import db

# Currencies configuration - HKD is default
CURRENCIES = {
    'HKD': {'symbol': 'HK$', 'name': 'Hong Kong Dollar'},
    'EUR': {'symbol': '€', 'name': 'Euro'},
    'USD': {'symbol': '$', 'name': 'US Dollar'},
    'CNY': {'symbol': '¥', 'name': 'Chinese Yuan'},
    'NZD': {'symbol': 'NZ$', 'name': 'New Zealand Dollar'},
    'AUD': {'symbol': 'A$', 'name': 'Australian Dollar'}
}

# Category colors for analytics
CATEGORY_COLORS = [
    '#3498db',  # Blue
    '#e74c3c',  # Red
    '#2ecc71',  # Green
    '#f39c12',  # Orange
    '#9b59b6',  # Purple
    '#1abc9c',  # Teal
    '#e91e63',  # Pink
    '#ff5722',  # Deep Orange
    '#795548',  # Brown
    '#607d8b',  # Gray
]

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def get_default_categories():
        defaults = ['Transport', 'Meals', 'Hotel', 'Mobile', 'Office', 'Other']
        return defaults

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='HKD')  # Changed from EUR to HKD
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    vendor = db.Column(db.String(100))
    invoice_filename = db.Column(db.String(200))
    ocr_text = db.Column(db.Text)
    ocr_confidence = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # New field
    user = db.relationship('User', backref='expenses')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'amount': self.amount,
            'currency': self.currency,
            'category': self.category,
            'description': self.description,
            'vendor': self.vendor,
            'invoice_filename': self.invoice_filename,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Unknown'
        }

class InvoicePattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor = db.Column(db.String(100), nullable=False)
    pattern_type = db.Column(db.String(50), nullable=False)  # 'amount', 'date', 'vendor'
    pattern = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class OCRExtraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'))
    extracted_data = db.Column(db.JSON)
    corrected_data = db.Column(db.JSON)
    correction_made = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
