from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import functools

admin_bp = Blueprint('admin', __name__)

from extensions import db
from models import Product, Category, Order, User, DeliveryPerson, Notification, OrderItem, Feedback, ReturnRequest
from sqlalchemy import func

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/')
@login_required
@admin_required
def admin_home():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    pending_orders = Order.query.filter_by(status='pending').count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(5).all()
    
    # Track pending human support requests
    pending_support = Feedback.query.filter_by(contact_requested=True).count()
    
    # Calculate Top Selling Products
    top_products_query = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(3).all()
    
    max_sold = top_products_query[0].total_sold if top_products_query else 1
    top_products = [
        {
            'name': p.name,
            'sold': p.total_sold,
            'percentage': (p.total_sold / max_sold) * 100 if max_sold > 0 else 0
        }
        for p in top_products_query
    ]
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders,
                         recent_users=recent_users,
                         top_products=top_products,
                         pending_support=pending_support)

@admin_bp.route('/products')
@login_required
@admin_required
def manage_products():
    products = Product.query.all()
    return render_template('admin/manage_product.html', products=products)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Product name is required!', 'danger')
            return redirect(url_for('admin.add_product'))
            
        try:
            price = float(request.form.get('price', 0))
        except (ValueError, TypeError):
            price = 0.0
            
        try:
            stock = int(request.form.get('stock', 0))
        except (ValueError, TypeError):
            stock = 0
            
        category = request.form.get('category')
        
        try:
            product = Product(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category=category
            )
            
            # Handle image upload or URL safely
            image_url = request.form.get('image_url')
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
                    product.image = filename
                else:
                    flash('Invalid image format! Please use PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('admin.add_product'))
            elif image_url:
                product.image = image_url
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while adding the product: {str(e)}', 'danger')
            return redirect(url_for('admin.add_product'))
    
    return render_template('admin/add_product.html', categories=categories)

@admin_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        if not product.name:
            flash('Product name is required!', 'danger')
            return redirect(url_for('admin.edit_product', id=id))
            
        product.description = request.form.get('description')
        product.category = request.form.get('category')
        
        try:
            product.price = float(request.form.get('price', 0))
        except (ValueError, TypeError):
            product.price = 0.0
            
        try:
            product.stock = int(request.form.get('stock', 0))
        except (ValueError, TypeError):
            product.stock = 0
            
        try:
            image_url = request.form.get('image_url')
            # Handle image upload or URL safely
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
                    product.image = filename
                else:
                    flash('Invalid image format! Please use PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('admin.edit_product', id=id))
            elif image_url:
                product.image = image_url
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the product: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_product', id=id))
    
    return render_template('admin/edit_product.html', product=product, categories=categories)

@admin_bp.route('/products/delete/<int:id>')
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/categories')
@login_required
@admin_required
def manage_categories():
    categories = Category.query.all()
    return render_template('admin/prod_category.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if Category.query.filter_by(name=name).first():
        flash('Category already exists!', 'danger')
    else:
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
    
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/categories/delete/<int:id>')
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    delivery_persons = DeliveryPerson.query.all()
    return render_template('admin/order_list.html', orders=orders, delivery_persons=delivery_persons)

@admin_bp.route('/orders/update-status/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(id):
    order = Order.query.get_or_404(id)
    status = request.form.get('status')
    
    order.status = status
    db.session.commit()
    flash(f'Order status updated to {status}!', 'success')
    return redirect(url_for('admin.orders'))

@admin_bp.route('/orders/assign-delivery/<int:id>', methods=['POST'])
@login_required
@admin_required
def assign_delivery_person(id):
    order = Order.query.get_or_404(id)
    dp_id = request.form.get('delivery_person_id')
    if dp_id:
        order.delivery_person_id = int(dp_id)
        db.session.commit()
        flash('Delivery person assigned successfully!', 'success')
    return redirect(url_for('admin.orders'))

@admin_bp.route('/returns/confirm-pickup/<int:return_id>', methods=['POST'])
@login_required
@admin_required
def confirm_return_pickup(return_id):
    # This simulates a delivery driver scanning the return package at the customer's door
    return_req = ReturnRequest.query.get_or_404(return_id)
    user = return_req.user
    
    # Mark as picked up
    return_req.status = 'picked_up'
    
    # THE TRUST ALGORITHM:
    # If the user has >= 3 successful past orders, they get an INSTANT wallet refund
    if user.successful_orders_count >= 3:
        user.wallet_balance += return_req.refund_amount
        return_req.status = 'refunded'
        
        # Notify user of the instant refund
        notification = Notification(
            user_id=user.id,
            title='Instant Refund Issued! 💸',
            message=f'We picked up your return and instantly credited ₹{return_req.refund_amount} to your Store Wallet!'
        )
        db.session.add(notification)
        flash(f'Instant refund of ₹{return_req.refund_amount} issued to {user.username}!', 'success')
    else:
        flash('Item marked as picked up. Refund will be processed after warehouse inspection.', 'info')
        
    db.session.commit()
    return redirect(url_for('admin.orders')) # Or redirect to a dedicated returns page

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/customer_list.html', users=users)

@admin_bp.route('/delivery-persons')
@login_required
@admin_required
def delivery_persons():
    delivery_persons = DeliveryPerson.query.all()
    # Updated to match the exact spelling of your HTML file
    return render_template('admin/develivery_person.html', delivery_persons=delivery_persons)

@admin_bp.route('/delivery-persons/<int:id>')
@login_required
@admin_required
def dp_detailed(id):
    dp = DeliveryPerson.query.get_or_404(id)
    return render_template('admin/dp_detailed.html', dp=dp)

@admin_bp.route('/delivery-persons/add', methods=['POST'])
@login_required
@admin_required
def add_delivery_person():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    vehicle_number = request.form.get('vehicle_number')
    
    dp = DeliveryPerson(
        name=name,
        phone=phone,
        email=email,
        vehicle_number=vehicle_number
    )
    db.session.add(dp)
    db.session.commit()
    flash('Delivery person added successfully!', 'success')
    return redirect(url_for('admin.delivery_persons'))

@admin_bp.route('/delivery-persons/delete/<int:id>')
@login_required
@admin_required
def delete_delivery_person(id):
    dp = DeliveryPerson.query.get_or_404(id)
    db.session.delete(dp)
    db.session.commit()
    flash('Delivery person deleted successfully!', 'success')
    return redirect(url_for('admin.delivery_persons'))

@admin_bp.route('/send-notification', methods=['GET', 'POST'])
@login_required
@admin_required
def send_notification():
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        user_id = request.form.get('user_id')
        
        notification = Notification(
            user_id=user_id if user_id else None,
            title=title,
            message=message
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Notification sent successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/notification.html', users=users)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        # Handle Profile Form Submission
        if 'username' in request.form and 'email' in request.form:
            if request.form.get('username'):
                current_user.username = request.form.get('username')
            if request.form.get('email'):
                current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            
        # Handle Security (Password) Form Submission
        elif 'new_password' in request.form:
            current_pwd = request.form.get('current_password')
            new_pwd = request.form.get('new_password')
            confirm_pwd = request.form.get('confirm_password')
            
            if not current_user.check_password(current_pwd):
                flash('Incorrect current password.', 'danger')
            elif new_pwd != confirm_pwd:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_pwd)
                db.session.commit()
                flash('Password changed successfully!', 'success')
    
    return render_template('admin/setting.html')

@admin_bp.route('/feedback')
@login_required
@admin_required
def feedback():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('admin/feedback_list.html', feedbacks=feedbacks)