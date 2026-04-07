from flask import Flask, render_template
import os

from extensions import db, login_manager
from models import User, Product, Category, Cart

# Initialize Flask app
app = Flask(__name__, template_folder='template')
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grocery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/products'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'customer.login'
login_manager.login_message_category = 'info'

# Allowed extensions for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Context processor for cart count
@app.context_processor
def cart_count_processor():
    # This needs to be imported here to avoid circular dependency at startup
    from flask_login import current_user
    if current_user.is_authenticated:
        cart_count = Cart.query.filter_by(user_id=current_user.id).count()
        return dict(cart_count=cart_count)
    return dict(cart_count=0)

# Main route
@app.route('/')
def index():
    products = Product.query.limit(8).all()
    categories = Category.query.all()
    return render_template('shop/index.html', products=products, categories=categories)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('layout/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('layout/500.html'), 500

# Import and register blueprints
from admin import admin_bp
from customer import customer_bp
from product import product_bp

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(customer_bp)
app.register_blueprint(product_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com')
            db.session.add(admin)
            
        # Ensure admin privileges and reset password to default just in case
        admin.is_admin = True
        admin.set_password('admin123')
        
        # Add some categories
        categories = ['Fruits', 'Vegetables', 'Stationeries', 'Groceries', 'Dairy',
                     'Bakery', 'Beverages', 'Snacks', 'Household', 'Personal Care',
                     'Mens Clothing', 'Womens Clothing', 'Electronics']
        for cat in categories:
            if not Category.query.filter_by(name=cat).first():
                db.session.add(Category(name=cat))
        
        db.session.commit()

    app.run(debug=True)
   