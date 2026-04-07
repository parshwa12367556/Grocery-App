from flask import Blueprint, render_template, request

product_bp = Blueprint('product_bp', __name__)

from models import Product, Category

@product_bp.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('q')
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    products = query.all()
    
    # Group products by Super-Categories for the template
    grouped_products = {}
    for p in products:
        cat = p.category or 'Others'
        if cat in ['Fruits', 'Vegetables', 'Dairy', 'Bakery', 'Groceries', 'Beverages', 'Snacks']:
            super_cat = 'Groceries & Food 🍎'
        elif cat in ['Clothing', 'Clothes', 'Fashion', 'Apparel', 'Mens Clothing', 'Womens Clothing']:
            super_cat = 'Clothing & Fashion 👕'
        elif cat in ['Electronics', 'Gadgets', 'Mobiles', 'Computers']:
            super_cat = 'Electronics & Gadgets 💻'
        else:
            super_cat = 'Household & Others 🏠'
            
        if super_cat not in grouped_products:
            grouped_products[super_cat] = []
        grouped_products[super_cat].append(p)
        
    return render_template('shop/product.html', products=products, grouped_products=grouped_products)

@product_bp.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('shop/product_detail.html', product=product)

@product_bp.route('/category/<category_name>')
def category_page(category_name):
    products = Product.query.filter_by(category=category_name).all()
    return render_template('shop/category_page.html', products=products, category=category_name)