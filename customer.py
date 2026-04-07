from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import random

customer_bp = Blueprint('customer', __name__)

from extensions import db
from models import User, Cart, Order, OrderItem, Product, Notification, Feedback


@customer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check by username first
        user = User.query.filter_by(username=username).first()
        if not user:
            # Fallback to checking by email if they typed their email instead
            user = User.query.filter_by(email=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('auth/login.html')

@customer_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('customer.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('customer.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('customer.register'))
        
        user = User(
            username=username,
            email=email,
            phone=phone,
            address=address
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('customer.login'))
    
    return render_template('auth/register.html')

@customer_bp.route('/forgot-password')
def forgot_password():
    return render_template('auth/forget_password.html')

@customer_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@customer_bp.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('shop/profile.html', orders=orders)

@customer_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    current_user.username = request.form.get('username')
    current_user.email = request.form.get('email')
    current_user.phone = request.form.get('phone')
    current_user.address = request.form.get('address')
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('customer.profile'))

@customer_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_pwd = request.form.get('current_password')
    new_pwd = request.form.get('new_password')
    confirm_pwd = request.form.get('confirm_password')
    
    if not current_user.check_password(current_pwd):
        flash('Incorrect current password.', 'danger')
        return redirect(url_for('customer.profile'))
        
    if new_pwd != confirm_pwd:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('customer.profile'))
        
    current_user.set_password(new_pwd)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('customer.profile'))

@customer_bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    # Check if product already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Calculate Free Delivery Progress
    FREE_DELIVERY_THRESHOLD = 50.0
    amount_needed = max(0, FREE_DELIVERY_THRESHOLD - total)
    progress_percentage = min(100, (total / FREE_DELIVERY_THRESHOLD) * 100)
    
    return render_template('shop/cart.html', cart_items=cart_items, total=total, amount_needed=amount_needed, progress_percentage=progress_percentage)

@customer_bp.route('/update-cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    quantity = int(request.form.get('quantity', 0))
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()
    else:
        db.session.delete(cart_item)
        db.session.commit()
    
    flash('Cart updated successfully!', 'success')
    return redirect(url_for('customer.cart'))

@customer_bp.route('/remove-from-cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'success')
    return redirect(url_for('customer.cart'))

@customer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('product_bp.products'))
    
    # Define constants for fees and taxes
    TAX_RATE = 0.10
    
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    DELIVERY_FEE = 0.00 if subtotal > 50 else 5.00
    tax_amount = subtotal * TAX_RATE
    final_total = subtotal + tax_amount + DELIVERY_FEE
    
    if request.method == 'POST':
        # Generate a unique Tracking ID
        tracking_id = f"TRK-{random.randint(10000000, 99999999)}"

        # Apply wallet balance logic
        amount_to_pay = final_total
        if current_user.wallet_balance > 0:
            if current_user.wallet_balance >= amount_to_pay:
                current_user.wallet_balance -= amount_to_pay
                amount_to_pay = 0
            else:
                amount_to_pay -= current_user.wallet_balance
                current_user.wallet_balance = 0

        # Create order
        order = Order(
            user_id=current_user.id,
            total_amount=amount_to_pay, # Only charge what wasn't covered by wallet
            shipping_address=request.form.get('address'),
            phone=request.form.get('phone'),
            status='pending',
            tracking_id=tracking_id
        )
        db.session.add(order)
        db.session.flush()
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            db.session.add(order_item)
            
            # Update product stock
            cart_item.product.stock -= cart_item.quantity
        
        # Clear cart
        Cart.query.filter_by(user_id=current_user.id).delete()
        
        # Increase trust score for successful order
        current_user.successful_orders_count += 1

        db.session.commit()
        
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            title='Order Placed',
            message=f'Your order #{order.id} has been placed successfully!'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('customer.order_confirmation', order_id=order.id))
    
    return render_template('shop/checkout.html', 
                           cart_items=cart_items, 
                           subtotal=subtotal,
                           tax=tax_amount,
                           delivery_fee=DELIVERY_FEE,
                           total=final_total)

@customer_bp.route('/order-confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    return render_template('shop/order_confirmation.html', order=order)

@customer_bp.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('shop/order.html', orders=orders)

@customer_bp.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('shop/shop_notifaction.html', notifications=notifications)

@customer_bp.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    return redirect(url_for('customer.notifications'))

@customer_bp.route('/about')
def about():
    return render_template('shop/about.html')

@customer_bp.route('/contact')
def contact():
    return render_template('shop/contact.html')

@customer_bp.route('/track', methods=['GET', 'POST'])
def track_order():
    tracking_id = request.args.get('id') or request.form.get('tracking_id')
    order = None
    
    if tracking_id:
        order = Order.query.filter_by(tracking_id=tracking_id).first()
        if not order:
            flash('Invalid Tracking ID. Please check and try again.', 'danger')
            
    return render_template('shop/track.html', order=order, search_id=tracking_id)

@customer_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        rating = int(request.form.get('rating', 0))
        order_number = request.form.get('order_number')
        liked_most = request.form.get('liked_most')
        message = request.form.get('message')
        suggestions = request.form.get('suggestions')
        contact_requested = 'contact_requested' in request.form
        
        feedback_entry = Feedback(
            user_id=current_user.id,
            rating=rating,
            order_number=order_number,
            liked_most=liked_most,
            message=message,
            suggestions=suggestions,
            contact_requested=contact_requested
        )
        db.session.add(feedback_entry)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('customer.thank_you'))
    return render_template('shop/feedback.html')

@customer_bp.route('/talk-to-human', methods=['POST'])
@login_required
def talk_to_human():
    order_number = request.form.get('order_number', 'General Inquiry')
    
    # Auto-generate a high-priority support ticket
    support_request = Feedback(
        user_id=current_user.id,
        rating=0, # 0 indicates a support ticket rather than a standard review
        order_number=order_number,
        message="🚨 URGENT: Customer clicked 'Talk to a Human'. Requires immediate assistance.",
        suggestions="System auto-generated: User requested a callback/human intervention.",
        contact_requested=True
    )
    db.session.add(support_request)
    db.session.commit()
    
    flash('Support request received! A human agent will reach out to you shortly.', 'success')
    
    # Redirect back to the page they came from, or profile as a fallback
    return redirect(request.referrer or url_for('customer.profile'))

@customer_bp.route('/thank-you')
def thank_you():
    return render_template('shop/thankyou.html')