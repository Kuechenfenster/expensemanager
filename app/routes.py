from flask import render_template, request, jsonify, send_from_directory
from app import app, db
from app.models import Expense, Category, InvoicePattern, OCRExtraction
from app.ocr import process_invoice
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.get_default_categories()
    return render_template('index.html', expenses=expenses, categories=categories)

@app.route('/analytics')
def analytics():
    categories = Category.get_default_categories()
    expenses = Expense.query.all()
    
    total = sum(e.amount for e in expenses)
    count = len(expenses)
    by_category = {cat: sum(e.amount for e in expenses if e.category == cat) for cat in categories}
    
    monthly = {}
    for exp in expenses:
        month = exp.date.strftime('%Y-%m')
        monthly[month] = monthly.get(month, 0) + exp.amount
    
    return render_template('analytics.html', 
                         total=total, count=count, 
                         by_category=by_category, monthly=monthly,
                         categories=categories)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
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
    try:
        data = request.form
        
        expense = Expense(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            amount=float(data['amount']),
            category=data['category'],
            description=data.get('description', ''),
            vendor=data.get('vendor', '')
        )
        
        # Handle invoice file or filename from form
        invoice_filename = None
        
        # Check if new file uploaded
        if 'invoice' in request.files:
            file = request.files['invoice']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                invoice_filename = filename
        
        # If no file uploaded, check for filename from review workflow
        if not invoice_filename:
            invoice_filename = request.form.get('invoice_filename')
            # Verify the file actually exists
            if invoice_filename:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], invoice_filename)
                if not os.path.exists(filepath):
                    invoice_filename = None  # File doesn't exist, don't save reference
        
        expense.invoice_filename = invoice_filename
        
        db.session.add(expense)
        db.session.commit()
        
        # Handle OCR correction data if provided
        ocr_data = request.form.get('ocr_data')
        if ocr_data:
            ocr_info = json.loads(ocr_data)
            ocr_extraction = OCRExtraction(
                expense_id=expense.id,
                original_amount=ocr_info.get('original_amount'),
                corrected_amount=expense.amount,
                original_date=ocr_info.get('original_date'),
                corrected_date=expense.date.isoformat(),
                original_vendor=ocr_info.get('original_vendor'),
                corrected_vendor=expense.vendor,
                full_text=ocr_info.get('full_text', ''),
                was_corrected=ocr_info.get('was_corrected', False)
            )
            db.session.add(ocr_extraction)
            
            # Learn from corrections
            if expense.vendor and ocr_extraction.full_text:
                InvoicePattern.learn_pattern(
                    expense.vendor, 'amount', expense.amount, 
                    ocr_extraction.full_text
                )
                InvoicePattern.learn_pattern(
                    expense.vendor, 'date', expense.date,
                    ocr_extraction.full_text
                )
            
            db.session.commit()
        
        return jsonify({'success': True, 'expense': expense.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    try:
        expense = Expense.query.get_or_404(id)
        if expense.invoice_filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(expense.invoice_filename))
            if os.path.exists(filepath):
                os.remove(filepath)
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload', methods=['POST'])
def upload_invoice():
    """Upload and process invoice - returns extracted data for review"""
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
        
        # Process OCR
        ocr_result = process_invoice(filepath)
        
        # Try to improve with learned patterns if vendor detected
        if ocr_result.get('vendor'):
            patterns = InvoicePattern.get_patterns_for_vendor(ocr_result['vendor'])
            for pattern in patterns:
                if pattern.pattern_type == 'amount' and not ocr_result.get('amount'):
                    # Could use patterns to improve detection
                    pass
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'extracted_data': {
                'amount': ocr_result.get('amount'),
                'date': ocr_result.get('date'),
                'vendor': ocr_result.get('vendor'),
                'raw_text': ocr_result.get('raw_text', '')[:1000]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded invoice files"""
    safe_filename = secure_filename(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.get_default_categories()
    return jsonify({'categories': categories})

@app.route('/api/categories', methods=['POST'])
def add_category():
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
    try:
        dates = db.session.query(Expense.date).distinct().all()
        months = sorted(set(d.strftime('%Y-%m') for (d,) in dates), reverse=True)
        return jsonify({'success': True, 'months': months})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/summary')
def get_summary():
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
    
    return jsonify({'total': total, 'count': len(expenses), 
                    'by_category': by_category, 'monthly': monthly})
