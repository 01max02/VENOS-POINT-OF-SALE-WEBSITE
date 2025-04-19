from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from sqlalchemy.sql import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    products = db.relationship('Product', backref='user', lazy=True, cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='user', lazy=True, cascade="all, delete-orphan")
    sales = db.relationship('Sale', backref='user', lazy=True, cascade="all, delete-orphan")

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True, cascade="all, delete-orphan")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'category_id': self.category_id,
            'user_id': self.user_id
        }

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # 'CASH', 'E-WALLET', 'CREDIT_CARD'
    cash_received = db.Column(db.Float, nullable=True)  # Only for cash payments
    change_amount = db.Column(db.Float, nullable=True)  # Only for cash payments
    is_refunded = db.Column(db.Boolean, default=False)
    refund_date = db.Column(db.DateTime, nullable=True)
    refund_reason = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade="all, delete-orphan")

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='SET NULL'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class CashManagement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(20), nullable=False)  # 'PAY_IN' or 'PAY_OUT'
    amount = db.Column(db.Float, nullable=False)
    comment = db.Column(db.String(200), nullable=False)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    starting_cash = db.Column(db.Float, nullable=False)
    closing_cash = db.Column(db.Float, nullable=True)
    is_open = db.Column(db.Boolean, default=True)

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.clear()  # Clear any existing session
            session['user_id'] = user.id
            flash('Login successful!')
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/categories')
def categories():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    categories = Category.query.filter_by(user_id=session['user_id']).all()
    return render_template('categories.html', categories=categories)

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        
        if Category.query.filter_by(name=name, user_id=session['user_id']).first():
            flash('Category already exists')
            return redirect(url_for('add_category'))
        
        category = Category(name=name, user_id=session['user_id'])
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully')
        return redirect(url_for('products'))
    
    return render_template('add_category.html')

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    category_id = request.args.get('category_id', type=int)
    selected_category = None
    
    if category_id:
        selected_category = Category.query.filter_by(id=category_id, user_id=session['user_id']).first_or_404()
        products = Product.query.filter_by(category_id=category_id, user_id=session['user_id']).all()
    else:
        products = Product.query.filter_by(user_id=session['user_id']).all()
    
    categories = Category.query.filter_by(user_id=session['user_id']).all()
    return render_template('products.html', 
                         products=products, 
                         categories=categories,
                         selected_category=selected_category)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category_id = request.form.get('category_id')
        
        if category_id:
            # Verify the category belongs to the current user
            category = Category.query.filter_by(id=category_id, user_id=session['user_id']).first()
            if not category:
                flash('Selected category does not exist or does not belong to you')
                categories = Category.query.filter_by(user_id=session['user_id']).all()
                return render_template('add_product.html', categories=categories)
            category_id = int(category_id)
        else:
            category_id = None
        
        product = Product(
            name=name, 
            price=price, 
            stock=stock, 
            category_id=category_id,
            user_id=session['user_id']
        )
        db.session.add(product)
        try:
            db.session.commit()
            flash('Product added successfully')
            return redirect(url_for('products'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding product')
            return redirect(url_for('add_product'))
    
    # Get only categories belonging to the current user
    categories = Category.query.filter_by(user_id=session['user_id']).all()
    return render_template('add_product.html', categories=categories)

@app.route('/pos')
def pos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all categories for filtering
    categories = Category.query.filter_by(user_id=session['user_id']).all()
    products = Product.query.filter_by(user_id=session['user_id']).all()
    products_list = [{
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'stock': product.stock,
        'category_id': product.category_id,
        'category_name': product.category.name if product.category else 'No Category'
    } for product in products]
    
    return render_template('pos.html', 
                         products=products_list,
                         categories=categories)

@app.route('/create_sale', methods=['POST'])
def create_sale():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    total = data['total']
    items = data['items']
    payment_info = data['payment']
    
    # Verify all products belong to the current user
    for item in items:
        product = Product.query.get(item['product_id'])
        if not product or product.user_id != session['user_id']:
            return jsonify({'error': 'Invalid product'}), 400
        if product.stock < item['quantity']:
            return jsonify({'error': f'Not enough stock for {product.name}'}), 400
    
    # Create sale with payment information
    sale = Sale(
        total=total,
        payment_method=payment_info['method'],
        cash_received=payment_info.get('cashReceived'),
        change_amount=payment_info.get('changeAmount'),
        user_id=session['user_id']
    )
    
    db.session.add(sale)
    db.session.commit()
    
    try:
        for item in items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            product = Product.query.get(item['product_id'])
            product.stock -= item['quantity']
            db.session.add(sale_item)
        
        db.session.commit()
        return {'success': True, 'sale_id': sale.id}
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get sales for current user only
    sales = Sale.query.filter_by(user_id=session['user_id']).order_by(Sale.date.desc()).all()
    
    # Get sale items for each sale
    sales_data = []
    for sale in sales:
        items = SaleItem.query.filter_by(sale_id=sale.id).all()
        sale_items = []
        for item in items:
            product = Product.query.get(item.product_id)
            sale_items.append({
                'product_name': product.name,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.quantity * item.price
            })
        sales_data.append({
            'sale': sale,
            'sale_items': sale_items,
            'total': sale.total
        })
    
    return render_template('sales.html', sales_data=sales_data)

@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    
    sale_items = []
    for item in items:
        product = Product.query.get(item.product_id)
        sale_items.append({
            'product_name': product.name,
            'quantity': item.quantity,
            'price': item.price,
            'total': item.quantity * item.price
        })
    
    return render_template('receipt.html', 
                         sale=sale,
                         items=sale_items,
                         total=sale.total)

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    product = Product.query.get_or_404(id)
    
    # Ensure users can only edit their own products
    if product.user_id != session['user_id']:
        flash('You can only edit your own products')
        return redirect(url_for('products'))
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        category_id = request.form.get('category_id')
        
        if category_id:
            category = Category.query.get(category_id)
            if not category:
                flash('Selected category does not exist')
                categories = Category.query.all()
                return render_template('edit_product.html', product=product, categories=categories)
            product.category_id = int(category_id)
        else:
            product.category_id = None
        
        try:
            db.session.commit()
            flash('Product updated successfully')
            return redirect(url_for('products'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating product')
            return redirect(url_for('edit_product', id=id))
    
    categories = Category.query.all()
    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/refund_sale/<int:sale_id>', methods=['POST'])
def refund_sale(sale_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    sale = Sale.query.get_or_404(sale_id)
    
    if sale.is_refunded:
        return jsonify({'success': False, 'message': 'Sale already refunded'}), 400
    
    try:
        # Get refund reason from request
        data = request.get_json()
        refund_reason = data.get('reason', 'No reason provided')
        
        # Return items to inventory
        sale_items = SaleItem.query.filter_by(sale_id=sale.id).all()
        for item in sale_items:
            product = Product.query.get(item.product_id)
            product.stock += item.quantity
        
        # Mark sale as refunded
        sale.is_refunded = True
        sale.refund_date = datetime.utcnow()
        sale.refund_reason = refund_reason
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Sale refunded successfully',
            'refund_date': sale.refund_date.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sales_report')
def sales_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sales_report.html')

@app.route('/api/sales_report/<date>')
def get_sales_report(date):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # If no date provided or invalid, use current date
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        except (ValueError, TypeError):
            date_obj = datetime.now()
        
        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get current date for comparison
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get the shift for this date
        shift = Shift.query.filter(
            Shift.date == start_of_day
        ).first()
        
        # For past dates, always return historical data
        if start_of_day < current_date:
            starting_cash = shift.starting_cash if shift else 0
        else:
            # For current date, only return data if shift is open
            if not (shift and shift.is_open):
                return jsonify({
                    'starting_cash': 0,
                    'cash_sales': 0,
                    'ewallet_sales': 0,
                    'credit_sales': 0,
                    'refunded_sales': 0,
                    'pay_in_amount': 0,
                    'pay_out_amount': 0,
                    'sales': []
                })
            starting_cash = shift.starting_cash
        
        # Query sales for the specified date
        sales = Sale.query.filter(
            Sale.date.between(start_of_day, end_of_day)
        ).order_by(Sale.date.desc()).all()
        
        # Query cash management transactions for the specified date
        cash_transactions = CashManagement.query.filter(
            CashManagement.date.between(start_of_day, end_of_day)
        ).all()
        
        # Initialize counters
        cash_sales = 0
        ewallet_sales = 0
        credit_sales = 0
        refunded_sales = 0
        pay_in_amount = 0
        pay_out_amount = 0
        
        # Calculate sales totals
        for sale in sales:
            if sale.is_refunded:
                refunded_sales += sale.total
            else:
                if sale.payment_method == 'CASH':
                    cash_sales += sale.total
                elif sale.payment_method == 'E-WALLET':
                    ewallet_sales += sale.total
                elif sale.payment_method == 'CREDIT_CARD':
                    credit_sales += sale.total
        
        # Calculate cash management totals
        for transaction in cash_transactions:
            if transaction.type == 'PAY_IN':
                pay_in_amount += transaction.amount
            else:  # PAY_OUT
                pay_out_amount += transaction.amount
        
        # Prepare sales data for the table
        sales_data = []
        for sale in sales:
            items_count = db.session.query(func.sum(SaleItem.quantity)).filter_by(sale_id=sale.id).scalar() or 0
            
            sales_data.append({
                'id': sale.id,
                'date': sale.date.isoformat(),
                'total': sale.total,
                'payment_method': sale.payment_method,
                'items_count': items_count,
                'is_refunded': sale.is_refunded
            })
        
        return jsonify({
            'starting_cash': starting_cash,
            'cash_sales': cash_sales,
            'ewallet_sales': ewallet_sales,
            'credit_sales': credit_sales,
            'refunded_sales': refunded_sales,
            'pay_in_amount': pay_in_amount,
            'pay_out_amount': pay_out_amount,
            'sales': sales_data,
            'is_past_date': start_of_day < current_date
        })
        
    except Exception as e:
        print(f"Error in get_sales_report: {str(e)}")  # Add logging
        return jsonify({
            'error': 'Error loading sales data',
            'message': str(e)
        }), 400

# Add a default route for sales report
@app.route('/api/sales_report/')
def get_current_sales_report():
    today = datetime.now().strftime('%Y-%m-%d')
    return get_sales_report(today)

@app.route('/api/cash_management', methods=['POST'])
def cash_management():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        # Validate input
        if not all(key in data for key in ['type', 'amount', 'comment']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        if data['type'] not in ['PAY_IN', 'PAY_OUT']:
            return jsonify({'success': False, 'message': 'Invalid transaction type'}), 400
            
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
        
        # Create new cash management record
        transaction = CashManagement(
            type=data['type'],
            amount=amount,
            comment=data['comment']
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cash_management_history/<date>')
def get_cash_management_history(date):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Convert the date string to datetime objects for the start and end of the day
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Query cash management transactions for the specified date
        transactions = CashManagement.query.filter(
            CashManagement.date.between(start_of_day, end_of_day)
        ).order_by(CashManagement.date.desc()).all()
        
        # Format transactions for response
        transactions_data = [{
            'id': t.id,
            'date': t.date.isoformat(),
            'type': t.type,
            'amount': t.amount,
            'comment': t.comment
        } for t in transactions]
        
        return jsonify({
            'transactions': transactions_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/shift_status/current')
def get_current_shift_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get current date without time
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find any open shift for today
        shift = Shift.query.filter(
            Shift.date == current_date,
            Shift.is_open == True
        ).first()
        
        return jsonify({
            'is_open': bool(shift)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/open_shift', methods=['POST'])
def open_shift():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if 'starting_amount' not in data:
            return jsonify({'success': False, 'message': 'Starting amount is required'}), 400
            
        # Get current date without time
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if there's already an open shift
        existing_shift = Shift.query.filter(
            Shift.date == current_date
        ).first()
        
        if existing_shift and existing_shift.is_open:
            return jsonify({
                'success': False,
                'message': 'A shift is already open for this date'
            }), 400
        
        # Create new shift
        new_shift = Shift(
            date=current_date,
            start_time=datetime.now(),
            starting_cash=float(data['starting_amount']),
            is_open=True
        )
        
        db.session.add(new_shift)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error opening shift: {str(e)}")  # Add logging
        return jsonify({'success': False, 'message': f'Error opening shift: {str(e)}'}), 500

@app.route('/api/close_shift', methods=['POST'])
def close_shift():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find the open shift
        shift = Shift.query.filter(
            Shift.date == current_date,
            Shift.is_open == True
        ).first()
        
        if not shift:
            return jsonify({
                'success': False,
                'message': 'No open shift found for this date'
            }), 400
        
        # Close the shift
        shift.end_time = datetime.now()
        shift.closing_cash = float(data['closing_amount'])
        shift.is_open = False
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    product = Product.query.get_or_404(id)
    
    # Ensure users can only delete their own products
    if product.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'You can only delete your own products'}), 403
    
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_category/<int:id>', methods=['POST'])
def delete_category(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    category = Category.query.get_or_404(id)
    
    # Ensure users can only delete their own categories
    if category.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'You can only delete your own categories'}), 403
    
    try:
        # Remove category reference from products
        Product.query.filter_by(category_id=id).update({Product.category_id: None})
        
        # Delete the category
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/verify_password', methods=['POST'])
def verify_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({'success': False, 'message': 'Password is required'}), 400
    
    user = User.query.get(session['user_id'])
    if user and check_password_hash(user.password, password):
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid password'}), 401

def init_db():
    with app.app_context():
        # Create tables only if they don't exist
        db.create_all()
        print("Database checked - existing data preserved!")

if __name__ == '__main__':
    init_db()  # Initialize database before running the app
    app.run(host='127.0.0.1', port=5000, debug=True)
