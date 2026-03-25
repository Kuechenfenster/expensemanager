from flask import render_template, request, jsonify, send_from_directory, Response
from app import app, db
from app.models import Expense, Category, User, InvoicePattern, OCRExtraction, CURRENCIES, CATEGORY_COLORS
from app.ocr import process_invoice
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import json
import csv
import io

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_default_users():
    """Initialize default users if they don't exist"""
    if User.query.count() == 0:
        martina = User(name='Martina')
        sebastian = User(name='Sebastian')
        db.session.add(martina)
        db.session.add(sebastian)
        db.session.commit()
        print("✅ Default users created: Martina, Sebastian")

@app.route('/')
def index():
    init_default_users()
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.get_default_categories()
    users = [user.to_dict() for user in User.query.all()]
    return render_template('index.html', expenses=expenses, categories=categories, 
                         currencies=CURRENCIES, users=users, category_colors=CATEGORY_COLORS)

@app.route('/analytics')
def analytics():
    categories = Category.get_default_categories()
    expenses = Expense.query.all()
    users_list = [user.to_dict() for user in User.query.all()]
    users = User.query.all()  # Keep for relationship queries

    # Calculate totals by currency
    totals_by_currency = {}
    for exp in expenses:
        curr = exp.currency
        totals_by_currency[curr] = totals_by_currency.get(curr, 0) + exp.amount

    by_category = {}
    for cat in categories:
        cat_expenses = [e for e in expenses if e.category == cat]
        by_category[cat] = {
            'amount': sum(e.amount for e in cat_expenses),
            'currency': cat_expenses[0].currency if cat_expenses else 'HKD',
            'count': len(cat_expenses)
        }

    by_user = {}
    for user in users:
        user_expenses = [e for e in expenses if e.user_id == user.id]
        by_user[user.name] = {
            'count': len(user_expenses),
            'total': sum(e.amount for e in user_expenses),
            'currency': user_expenses[0].currency if user_expenses else 'HKD'
        }

    monthly = {}
    for exp in expenses:
        month = exp.date.strftime('%Y-%m')
        if month not in monthly:
            monthly[month] = {}
        monthly[month][exp.currency] = monthly[month].get(exp.currency, 0) + exp.amount

    # Assign colors to categories
    category_colors = {}
    for i, cat in enumerate(categories):
        category_colors[cat] = CATEGORY_COLORS[i % len(CATEGORY_COLORS)]

    return render_template('analytics.html',
                         expenses=expenses,
                         currencies=CURRENCIES,
                         totals_by_currency=totals_by_currency,
                         by_category=by_category,
                         by_user=by_user,
                         monthly=monthly,
                         categories=categories,
                         category_colors=category_colors)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    query = Expense.query
    category = request.args.get('category')
    month = request.args.get('month')
    user_id = request.args.get('user_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

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
    if user_id:
        query = query.filter_by(user_id=int(user_id))

    # Date range filtering
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= from_date)
        except:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= to_date)
        except:
            pass

    expenses = query.order_by(Expense.date.desc()).all()
    return jsonify([exp.to_dict() for exp in expenses])



@app.route('/api/expenses/export', methods=['GET'])
def export_expenses():
    """Export expenses to CSV"""
    query = Expense.query
    category = request.args.get('category')
    user_id = request.args.get('user_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Apply filters
    if category:
        query = query.filter_by(category=category)
    if user_id:
        query = query.filter_by(user_id=int(user_id))
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= from_date)
        except:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= to_date)
        except:
            pass

    expenses = query.order_by(Expense.date.desc()).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Date', 'User', 'Category', 'Vendor', 'Description', 'Currency', 'Amount', 'Invoice File'])

    # Data rows
    for exp in expenses:
        writer.writerow([
            exp.date.strftime('%Y-%m-%d'),
            exp.user.name if exp.user else '',
            exp.category,
            exp.vendor or '',
            exp.description or '',
            exp.currency,
            exp.amount,
            exp.invoice_filename or ''
        ])

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=expenses.csv',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    try:
        data = request.form

        # Get user_id from form
        user_id = data.get('user_id')
        if user_id:
            user_id = int(user_id)

        expense = Expense(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            amount=float(data['amount']),
            currency=data.get('currency', 'HKD'),  # Default to HKD
            category=data['category'],
            description=data.get('description', ''),
            vendor=data.get('vendor', ''),
            user_id=user_id
        )

        # Handle file upload
        if 'invoice' in request.files:
            file = request.files['invoice']
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                expense.invoice_filename = filename

        # Handle invoice filename from review workflow
        if not expense.invoice_filename:
            invoice_filename = data.get('invoice_filename')
            if invoice_filename:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], invoice_filename)
                if os.path.exists(filepath):
                    expense.invoice_filename = invoice_filename

        # Handle OCR data
        ocr_data = data.get('ocr_data')
        if ocr_data:
            try:
                ocr_json = json.loads(ocr_data)
                expense.ocr_text = ocr_json.get('raw_text', '')
                expense.ocr_confidence = ocr_json.get('confidence', 0)
            except:
                pass

        db.session.add(expense)
        db.session.commit()

        return jsonify({'success': True, 'expense': expense.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Category name required'}), 400

    existing = Category.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'error': 'Category already exists'}), 400

    category = Category(name=name, is_custom=True)
    db.session.add(category)
    db.session.commit()

    return jsonify({'success': True, 'category': name})

@app.route('/api/upload', methods=['POST'])
def upload_invoice():
    if 'invoice' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['invoice']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process with OCR
        ocr_result = process_invoice(filepath)

        return jsonify({
            'success': True,
            'filename': filename,
            'ocr': ocr_result
        })

    return jsonify({'success': False, 'error': 'Invalid file type'}), 400

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/expense/<int:id>/invoice')
def get_invoice(id):
    expense = Expense.query.get_or_404(id)
    if expense.invoice_filename:
        return send_from_directory(app.config['UPLOAD_FOLDER'], expense.invoice_filename)
    return jsonify({'error': 'No invoice attached'}), 404
