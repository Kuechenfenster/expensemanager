from flask import render_template, request, jsonify, redirect, url_for, send_from_directory
from app import app, db
from app.models import Expense, Category
from app.ocr import process_invoice
from werkzeug.utils import secure_filename
from datetime import datetime
import os

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main dashboard page"""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.get_default_categories()
    
    # Calculate totals
    total_amount = sum(e.amount for e in expenses)
    category_totals = {}
    for cat in categories:
        category_totals[cat] = sum(e.amount for e in expenses if e.category == cat)
    
    return render_template('index.html', 
                         expenses=expenses, 
                         categories=categories,
                         total_amount=total_amount,
                         category_totals=category_totals)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """API: Get all expenses"""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return jsonify([e.to_dict() for e in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    """API: Add new expense"""
    try:
        data = request.form
        
        expense = Expense(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            amount=float(data['amount']),
            category=data['category'],
            description=data.get('description', ''),
            vendor=data.get('vendor', '')
        )
        
        # Handle file upload
        if 'invoice' in request.files:
            file = request.files['invoice']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                expense.invoice_filename = filename
                
                # Process OCR
                ocr_result = process_invoice(filepath)
                expense.ocr_text = ocr_result['raw_text']
                
                # Auto-fill if not provided
                if not expense.vendor and ocr_result['vendor']:
                    expense.vendor = ocr_result['vendor']
                if not expense.amount and ocr_result['amount']:
                    expense.amount = ocr_result['amount']
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({'success': True, 'expense': expense.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    """API: Delete expense"""
    try:
        expense = Expense.query.get_or_404(id)
        
        # Delete associated file
        if expense.invoice_filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], expense.invoice_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        db.session.delete(expense)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload', methods=['POST'])
def upload_invoice():
    """API: Upload and process invoice"""
    try:
        if 'invoice' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['invoice']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with OCR
        ocr_result = process_invoice(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'extracted_data': {
                'amount': ocr_result['amount'],
                'date': ocr_result['date'] if ocr_result['date'] else None,
                'vendor': ocr_result['vendor'],
                'raw_text': ocr_result['raw_text'][:500]  # Truncate for response
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/summary')
def get_summary():
    """API: Get expense summary statistics"""
    expenses = Expense.query.all()
    categories = Category.get_default_categories()
    
    summary = {
        'total': sum(e.amount for e in expenses),
        'count': len(expenses),
        'by_category': {cat: sum(e.amount for e in expenses if e.category == cat) for cat in categories},
        'recent': [e.to_dict() for e in Expense.query.order_by(Expense.date.desc()).limit(5).all()]
    }
    
    return jsonify(summary)
