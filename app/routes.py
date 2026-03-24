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
    """API: Get all expenses with optional filters"""
    query = Expense.query
    
    # Apply filters if provided
    category = request.args.get('category')
    month = request.args.get('month')  # Format: YYYY-MM
    
    if category:
        query = query.filter_by(category=category)
    
    if month:
        try:
            year, mon = month.split('-')
            query = query.filter(
                db.extract('year', Expense.date) == int(year),
                db.extract('month', Expense.date) == int(mon)
            )
        except:
            pass
    
    expenses = query.order_by(Expense.date.desc()).all()
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
    """API: Get expense summary statistics with filters"""
    query = Expense.query
    
    # Apply filters
    category = request.args.get('category')
    month = request.args.get('month')  # Format: YYYY-MM
    
    if category:
        query = query.filter_by(category=category)
    
    if month:
        try:
            year, mon = month.split('-')
            query = query.filter(
                db.extract('year', Expense.date) == int(year),
                db.extract('month', Expense.date) == int(mon)
            )
        except:
            pass
    
    expenses = query.all()
    categories = Category.get_default_categories()
    
    # Calculate monthly totals
    monthly_totals = {}
    for exp in expenses:
        month_key = exp.date.strftime('%Y-%m')
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + exp.amount
    
    summary = {
        'total': sum(e.amount for e in expenses),
        'count': len(expenses),
        'by_category': {cat: sum(e.amount for e in expenses if e.category == cat) for cat in categories},
        'monthly_totals': monthly_totals,
        'recent': [e.to_dict() for e in query.order_by(Expense.date.desc()).limit(5).all()]
    }
    
    return jsonify(summary)

# Category API endpoints
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """API: Get all categories"""
    categories = Category.get_default_categories()
    return jsonify({'success': True, 'categories': categories})

@app.route('/api/categories', methods=['POST'])
def add_category():
    """API: Add a new custom category"""
    try:
        data = request.get_json() or request.form
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Category name is required'}), 400
        
        success, result = Category.add_custom_category(name)
        if success:
            return jsonify({'success': True, 'category': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/categories/<name>', methods=['DELETE'])
def delete_category(name):
    """API: Delete a custom category"""
    try:
        success, result = Category.delete_category(name)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/months')
def get_available_months():
    """API: Get list of months with expenses"""
    try:
        # Get all unique year-month combinations
        dates = db.session.query(Expense.date).distinct().all()
        months = set()
        for (date,) in dates:
            months.add(date.strftime('%Y-%m'))
        
        # Sort descending (newest first)
        sorted_months = sorted(list(months), reverse=True)
        
        return jsonify({
            'success': True,
            'months': sorted_months
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
