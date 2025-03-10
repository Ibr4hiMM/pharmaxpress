# app.py - main application file
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import datetime
from flask_admin.menu import MenuLink

# Load environment variables
load_dotenv()

# Initialize flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/pharmadb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# -------------------------------------------------------------------
# Define database models
# -------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Forgot password fields
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(100), default='sample1.jpg')  # image filename
    category = db.Column(db.String(50), default='general')  # added category field

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_ordered = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    total = db.Column(db.Float, nullable=False)
    # Shipping information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    # Payment information (store only minimal data)
    card_last4 = db.Column(db.String(4))
    cardholder_name = db.Column(db.String(100))
    # Relationship with order items
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # price at time of purchase

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route('/')
def index():
    # Define a list of featured product names
    featured_names = [
        'C-Ronz, Vitamin C, 1000 Mg, Effervescent - 20 Tablets',
        'Jamieson, Vitamin E, Antioxidant Blends, 400 IU – 30 Capsules',
        'Jamieson, Vitamin B12 1000 Mcg - 100 Sublingual Tablets',
        'Fexofin, 180 Mg, Reduce Allergy Symptoms - 30 Tablets'
    ]
    # Query products whose names are in the featured list
    featured_products = Product.query.filter(Product.name.in_(featured_names)).all()
    return render_template('index.html', products=featured_products)

@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 8  # Show 8 products per page

    if category != 'all' and search:
        query = Product.query.filter(
            (Product.category == category) &
            (Product.name.ilike(f'%{search}%') | Product.description.ilike(f'%{search}%'))
        )
    elif category != 'all':
        query = Product.query.filter_by(category=category)
    elif search:
        query = Product.query.filter(
            Product.name.ilike(f'%{search}%') | Product.description.ilike(f'%{search}%')
        )
    else:
        query = Product.query

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # Get distinct categories from Product table
    distinct_categories = db.session.query(Product.category).distinct().all()
    categories = [cat for (cat,) in distinct_categories]

    return render_template('products.html',
                           products=products,
                           pagination=pagination,
                           category=category,
                           search=search,
                           categories=categories)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        flash('Thank you for your message! We will get back to you soon.')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.')
            return redirect(url_for('signup'))

        # Enforce minimum length of 8 characters
        if len(password) < 8:
            flash('Password must be at least 8 characters long.')
            return redirect(url_for('signup'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            flash('Account created and logged in successfully!')
            return redirect(url_for('checkout') if session.get('cart') else url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.')
            print(e)
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Hardcoded admin credentials
        if email == "admin@admin.com" and password == "admin":
            session['is_admin'] = True
            session['user_id'] = 0  # Dummy admin id
            session['username'] = "admin"
            flash('Logged in as admin!')
            return redirect(url_for('admin.index'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            if 'cart' not in session:
                session['cart'] = {}
            session['is_admin'] = False
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please sign in or sign up to add items to your cart.')
        return redirect(url_for('login'))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    session['cart'] = cart
    flash('Item added to cart!')
    return redirect(request.referrer or url_for('products'))

@app.route('/cart')
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart_items=[], total=0, featured_products=[])

    cart = session['cart']
    cart_items = []
    total = 0

    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            total += item_total

    featured_names = [
        'C-Ronz, Vitamin C, 1000 Mg, Effervescent - 20 Tablets',
        'Jamieson, Vitamin E, Antioxidant Blends, 400 IU – 30 Capsules',
        'Jamieson, Vitamin B12 1000 Mcg - 100 Sublingual Tablets',
        'Fexofin, 180 Mg, Reduce Allergy Symptoms - 30 Tablets'
    ]
    featured_products = Product.query.filter(Product.name.in_(featured_names)).all()

    return render_template('cart.html', cart_items=cart_items, total=total, featured_products=featured_products)

@app.route('/update-cart-item/<int:product_id>', methods=['POST'])
def update_cart_item(product_id):
    if 'cart' not in session:
        return redirect(url_for('cart'))

    action = request.form.get('action')
    cart = session['cart']
    product_id_str = str(product_id)

    if product_id_str in cart:
        if action == 'increase':
            cart[product_id_str] += 1
        elif action == 'decrease':
            if cart[product_id_str] > 1:
                cart[product_id_str] -= 1
            else:
                del cart[product_id_str]

    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/remove-from-cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' not in session:
        return redirect(url_for('cart'))

    cart = session['cart']
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        session['cart'] = cart
        flash('Item removed from cart.')

    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout.')
        return redirect(url_for('login'))

    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty.')
        return redirect(url_for('products'))

    cart = session['cart']
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            total += product.price * quantity

    tax = round(total * 0.15, 2)
    grand_total = round(total + tax, 2)

    return render_template('checkout.html', total=total, tax=tax, grand_total=grand_total)

@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        flash('Please login to checkout.')
        return redirect(url_for('login'))

    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty.')
        return redirect(url_for('products'))

    # Retrieve shipping information
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    address = request.form.get('address')
    city = request.form.get('city')
    province = request.form.get('state')  # your select field name is "state"
    zip_code = request.form.get('zip')
    phone = request.form.get('phone')

    # Retrieve payment information
    card_number = request.form.get('cardNumber')
    name_on_card = request.form.get('nameOnCard')
    card_last4 = card_number.replace(' ', '')[-4:] if card_number else ''

    user_id = session['user_id']
    cart = session['cart']
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            total += product.price * quantity
    tax = round(total * 0.15, 2)
    grand_total = round(total + tax, 2)

    order = Order(
        user_id=user_id,
        total=grand_total,
        first_name=first_name,
        last_name=last_name,
        address=address,
        city=city,
        province=province,
        zip_code=zip_code,
        phone=phone,
        card_last4=card_last4,
        cardholder_name=name_on_card
    )
    db.session.add(order)
    db.session.flush()  # Get order id

    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(order_item)

    db.session.commit()
    session.pop('cart', None)
    session['cart'] = {}

    flash('Your order has been placed successfully!')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        flash('Please login to view orders.')
        return redirect(url_for('login'))

    order = Order.query.get_or_404(order_id)
    order_items = []
    for item in order.items:
        product = db.session.get(Product, item.product_id)
        if product:
            order_items.append({
                'product': product,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.price * item.quantity
            })

    return render_template('order_confirmation.html', order=order, order_items=order_items)

@app.route('/order-history')
def order_history():
    if 'user_id' not in session:
        flash("Please log in to view your order history.")
        return redirect(url_for('login'))

    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.date_ordered.desc()).all()
    return render_template("order_history.html", orders=orders)

# -------------------------------------------------------------------
# Admin Interface Setup (placed after models and routes)
# -------------------------------------------------------------------
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

class AdminModelView(ModelView):
    def is_accessible(self):
        return session.get('is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin = Admin(
    app,
    name='PharmaXPress Admin',
    template_mode='bootstrap3',
    base_template='admin/custom_base.html'
)

admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Product, db.session))
admin.add_view(AdminModelView(Order, db.session))
admin.add_view(AdminModelView(OrderItem, db.session))

# Define the custom Logout menu link
class LogoutMenuLink(MenuLink):
    def is_accessible(self):
        # Only show this link to logged-in admin users
        return session.get('is_admin', False)

# Add the custom logout link to the admin menu
admin.add_link(LogoutMenuLink(name='Logout', url='/logout'))

# -------------------------------------------------------------------
# Create database tables and insert sample products
# -------------------------------------------------------------------
def create_tables():
    # For development only; in production use migrations.
    db.create_all()

    if Product.query.count() == 0:
        sample_products = [
            Product(
                name='C-Ronz, Vitamin C, 1000 Mg, Effervescent - 20 Tablets',
                description='Effervescent Vitamin C tablets to support immune function.',
                price=18.90,
                stock=50,
                category='Vitamins',
                image='c_ronz_vitamin_c_1000mg_20tabs.png'
            ),
            Product(
                name='Jamieson, Vitamin E, Antioxidant Blends, 400 IU – 30 Capsules',
                description='Vitamin E capsules to support antioxidant activity.',
                price=62.00,
                stock=50,
                category='Vitamins',
                image='jamieson_vitamin_e_400iu_30caps.png'
            ),
            Product(
                name='Jamieson, Vitamin B12 1000 Mcg - 100 Sublingual Tablets',
                description='Sublingual tablets for fast absorption, supporting energy and metabolism.',
                price=54.65,
                stock=50,
                category='Vitamins',
                image='jamieson_vitamin_b12_1000mcg_100tabs.png'
            ),
            Product(
                name='Fexofin, 180 Mg, Reduce Allergy Symptoms - 30 Tablets',
                description='Fexofenadine HCl tablets to relieve seasonal allergy symptoms.',
                price=32.50,
                stock=50,
                category='Allergy relief',
                image='fexofin_180mg_30tabs.png'
            ),
            Product(
                name='Claricare, Herbal Tablets, For Allergic Rhinitis Symptoms - 20 Tablets',
                description='Herbal formula designed to alleviate allergic rhinitis symptoms.',
                price=42.00,
                stock=50,
                category='Allergy relief',
                image='claricare_herbal_20tabs.png'
            ),
            Product(
                name='Pananatural, Cough Syrup, For Adults & Childrens - 128 Gm',
                description='Cough syrup formulated to help relieve cough for both adults and children.',
                price=39.00,
                stock=50,
                category='Allergy relief',
                image='pananatural_cough_syrup_128gm.png'
            ),
            Product(
                name='Babyjoy, Baby Diapers, Size 3, Giant Box, 6-12 Kg - 168 Pcs',
                description='Giant box of size 3 baby diapers, suitable for infants weighing 6-12 kg.',
                price=199.96,
                stock=50,
                category='Baby Supplements',
                image='babyjoy_size3_168pcs.png'
            ),
            Product(
                name='Bumble & Bird Stroller Light Grey - 1 Pc',
                description='Lightweight, foldable stroller in grey for convenient travel with your baby.',
                price=875.09,
                stock=50,
                category='Baby Supplements',
                image='bumble_bird_stroller_light_grey.png'
            ),
            Product(
                name='Pampers, Aqua Pure, Baby Wipes, 99% Pure Water - 48 Pcs',
                description='Baby wipes made with 99% pure water, gentle on sensitive skin.',
                price=29.19,
                stock=50,
                category='Baby Supplements',
                image='pampers_aqua_pure_wipes_48pcs.png'
            ),
            Product(
                name='Clear, Men Shampoo, Body & Face Wash, Active Fresh - 400 Ml',
                description='Multi-purpose men’s shampoo, body, and face wash for an active lifestyle.',
                price=28.30,
                stock=50,
                category='Hair Care',
                image='clear_men_shampoo_400ml.png'
            ),
            Product(
                name='Garnier, Ultra Doux, Shampoo, With Rice Water Infusion - 200 Ml',
                description='Nourishing shampoo infused with rice water to gently cleanse and strengthen hair.',
                price=16.32,
                stock=50,
                category='Hair Care',
                image='garnier_ultra_doux_rice_200ml.png'
            ),
            Product(
                name='Loreal, Hair Shampoo, Elvive Hyaluron, For Oily Scalp With Dry Ends - 400 Ml',
                description='Hyaluron-infused shampoo that hydrates dry ends and clarifies oily scalp.',
                price=26.35,
                stock=50,
                category='Hair Care',
                image='loreal_elvive_hyaluron_400ml.png'
            ),
            Product(
                name='Snowhite, Moroccan Soap - 370 Gm',
                description='Purifying Moroccan black soap to nourish and soften skin.',
                price=179.00,
                stock=50,
                category='Skin Care',
                image='snowhite_moroccan_soap_370gm.png'
            ),
            Product(
                name='Head & Shoulders, Shampoo, Smooth & Silky, For A Smooth Hair - 1000 Ml',
                description='Anti-dandruff shampoo designed to keep hair smooth and silky.',
                price=46.95,
                stock=50,
                category='Hair Care',
                image='head_shoulders_smooth_silky_1000ml.png'
            ),
            Product(
                name='Avene, Cream, Xeracalm A.D, Soothing Concentrate - 50 Ml',
                description='Soothing cream specially formulated for sensitive and irritated skin.',
                price=158.70,
                stock=50,
                category='Skin Care',
                image='avene_xeracalm_cream_50ml.png'
            ),
            Product(
                name='La Roche-Posay, Cream, Mela B3, Spf30, Anti-Dark spot - 40 Ml',
                description='Daily cream with SPF30 to reduce dark spots and even out skin tone.',
                price=221.00,
                stock=50,
                category='Skin Care',
                image='la_roche_posay_mela_b3_40ml.png'
            ),
            Product(
                name='Filorga, Time-Filler, Intensive Serum, For Winkles - 30 Ml',
                description='Concentrated anti-wrinkle serum to smooth and plump the skin.',
                price=561.20,
                stock=50,
                category='Skin Care',
                image='filorga_time_filler_serum_30ml.png'
            ),
            Product(
                name='Filorga, Skin-Unify, Even Skin Tone Cream - 50 Ml',
                description='Brightening cream designed to unify and enhance skin tone.',
                price=365.70,
                stock=50,
                category='Skin Care',
                image='filorga_skin_unify_cream_50ml.png'
            ),
            Product(
                name='Jayla, Floral Body Spray, Maze - 200 Ml',
                description='Floral-scented body spray for long-lasting freshness.',
                price=70.00,
                stock=50,
                category='Skin Care',
                image='jayla_floral_body_spray_200ml.png'
            )
        ]
        db.session.add_all(sample_products)
        db.session.commit()

# Create the db tables and insert sample products before running the app
with app.app_context():
    create_tables()

if __name__ == '__main__':
    app.run(debug=True)
