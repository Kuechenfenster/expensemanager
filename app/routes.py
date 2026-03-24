from flask import render_template, request, jsonify, send_from_directory
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
    """Main expenses page"""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.get_default_categories()
    return render_template('index.html', expenses=expenses, categories=categories)

@app.route('/analytics')
def analytics():
    """Analytics page with summary"""
    categories = Category.get_default_categories()
    expenses = Expense.query.all()
    
    # Calculate stats
    total = sum(e.amount for e in expenses)
    count = len(expenses)
    by_category = {cat: sum(e.amount for e in expenses if e.category == cat) for cat in categories}
    
    # Monthly breakdown
    monthly = {}
    for exp in expenses:
        month = exp.date.strftime('%Y-%m')
        monthly[month] = monthly.get(month, 0) + exp.amount
    
    return render_template('analytics.html', 
                         total=total, 
                         count=count, 
                         by_category=by_category,
                         monthly=monthly,
                         categories=categories)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get expenses with optional filters"""
    query = Expense.query
    category = request.args.get('category')
    month = request.args.get('month')
    
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
    """Add new expense"""
    try:
        data = request.form
        
        expense = Expense(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            amount=float(data['amount']),
            category=data['category'],
            description=data.get('description', ''),
            vendor=data.get('vendor', '')
        )
        
        if 'invoice' in request.files:
            file = request.files['invoice']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                expense.invoice_filename = filename
                
                ocr_result = process_invoice(filepath)
                expense.ocr_text = ocr_result['raw_text']
                if not expense.vendor and ocr_result['vendor']:
                    expense.vendor = ocr_result['vendor']
        
        db.session.add(expense)
        db.session.commit()
        return jsonify({'success': True, 'expense': expense.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    """Delete expense"""
    try:
        expense = Expense.query.get_or_404(id)
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
    """Upload and process invoice with OCR"""
    try:
        if 'invoice' not in request.files:
            return jsonify({'success': False, 'error': 'No file'}), 400
        
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
        
        ocr_result = process_invoice(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'extracted_data': {
                'amount': ocr_result['amount'],
                'date': ocr_result['date'] if ocr_result['date'] else None,
                'vendor': ocr_result['vendor']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.get_default_categories()
    return jsonify({'categories': categories})

@app.route('/api/categories', methods=['POST'])
def add_category():
    """Add custom category"""
    try:
        data = request.get_json() or request.form
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name required'}), 400
        
        success, result = Category.add_custom_category(name)
        if success:
            return jsonify({'success': True, 'category': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/months')
def get_months():
    """Get months with expenses"""
    try:
        dates = db.session.query(Expense.date).distinct().all()
        months = sorted(set(d.strftime('%Y-%m') for (d,) in dates), reverse=True)
        return jsonify({'success': True, 'months': months})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/summary')
def get_summary():
    """Get summary with filters"""
    query = Expense.query
    category = request.args.get('category')
    month = request.args.get('month')
    
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
    
    total = sum(e.amount for e in expenses)
    by_category = {cat: sum(e.amount for e in expenses if e.category == cat) for cat in categories}
    
    monthly = {}
    for exp in expenses:
        month_key = exp.date.strftime('%Y-%m')
        monthly[month_key] = monthly.get(month_key, 0) + exp.amount
    
    return jsonify({
        'total': total,
        'count': len(expenses),
        'by_category': by_category,
        'monthly': monthly
    })
