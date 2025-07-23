from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telefone')
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])

class PackageForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    destination = StringField('Destino', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[DataRequired()])
    price = FloatField('Preço', validators=[DataRequired()])
    duration = IntegerField('Duração (dias)', validators=[DataRequired()])
    category = SelectField('Categoria', choices=[
        ('praia', 'Praia'),
        ('aventura', 'Aventura'),
        ('família', 'Família'),
        ('romântico', 'Romântico'),
        ('cidade', 'Cidade'),
        ('lua-de-mel', 'Lua de Mel')
    ], validators=[DataRequired()])
    image_url = StringField('URL da Imagem', validators=[DataRequired()])
    includes = TextAreaField('O que está incluso', validators=[DataRequired()])
    hotel = StringField('Hospedagem', validators=[DataRequired()])
    transport = StringField('Transporte', validators=[DataRequired()])
    featured = BooleanField('Pacote em destaque')

# Database initialization
def init_db():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Packages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            destination TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            duration INTEGER NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT NOT NULL,
            includes TEXT NOT NULL,
            hotel TEXT NOT NULL,
            transport TEXT NOT NULL,
            featured BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            travelers INTEGER NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            payment_installments INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (package_id) REFERENCES packages (id)
        )
    ''')
    
    # Cart table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            travelers INTEGER NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (package_id) REFERENCES packages (id)
        )
    ''')
    
    # Insert sample data
    cursor.execute('SELECT COUNT(*) FROM packages')
    if cursor.fetchone()[0] == 0:
        sample_packages = [
            ('Pacote Completo - Cancún', 'Cancún, México', 'Desfrute das praias paradisíacas de Cancún com tudo incluso. Resort 5 estrelas, transfers e passeios inclusos. Uma experiência inesquecível no Caribe mexicano com águas cristalinas e areia branca.', 2899.99, 7, 'praia', 'https://images.pexels.com/photos/1371360/pexels-photo-1371360.jpeg?auto=compress&cs=tinysrgb&w=800', 'All Inclusive, Transfers, Passeios, Seguro Viagem', 'Resort Grand Oasis Cancún 5*', 'Aéreo + Transfers', 1),
            ('Rio de Janeiro Completo', 'Rio de Janeiro, Brasil', 'Conheça a Cidade Maravilhosa! Cristo Redentor, Pão de Açúcar, Copacabana e muito mais. Inclui passeios aos principais pontos turísticos e experiências únicas na cidade mais icônica do Brasil.', 1299.99, 5, 'cidade', 'https://images.pexels.com/photos/351448/pexels-photo-351448.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Passeios, Café da manhã, Transfers', 'Hotel Copacabana Palace 5*', 'Aéreo', 1),
            ('Aventura na Chapada Diamantina', 'Chapada Diamantina, Brasil', 'Trilhas, cachoeiras e paisagens deslumbrantes na Chapada Diamantina. Para os amantes da natureza e aventura. Inclui guia especializado e equipamentos para trilhas.', 899.99, 4, 'aventura', 'https://images.pexels.com/photos/1646953/pexels-photo-1646953.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Guia, Transfers, Equipamentos', 'Pousada Villa Serrana 4*', 'Terrestre', 0),
            ('Disney Orlando - Família', 'Orlando, EUA', 'A magia da Disney para toda família! Ingressos para 4 parques e hospedagem em resort oficial. Viva momentos mágicos com Mickey, Minnie e todos os personagens Disney.', 4299.99, 10, 'família', 'https://images.pexels.com/photos/164133/pexels-photo-164133.jpeg?auto=compress&cs=tinysrgb&w=800', 'Ingressos Disney, Hospedagem, Transfers, Fast Pass', 'Disney Grand Floridian Resort 5*', 'Aéreo + Transfers', 1),
            ('Paris Romântico', 'Paris, França', 'A cidade do amor! Torre Eiffel, Louvre, passeio de barco no Sena e muito romantismo. Inclui jantar romântico e passeios pelos pontos mais icônicos de Paris.', 3799.99, 8, 'romântico', 'https://images.pexels.com/photos/338515/pexels-photo-338515.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Passeios, Café da manhã, Jantar romântico', 'Hotel Le Meurice 5*', 'Aéreo', 1),
            ('Maldivas Paradise', 'Maldivas', 'O paraíso na Terra! Bangalôs sobre a água cristalina e experiência inesquecível. Resort exclusivo com spa, mergulho e gastronomia internacional.', 6999.99, 7, 'lua-de-mel', 'https://images.pexels.com/photos/1483053/pexels-photo-1483053.jpeg?auto=compress&cs=tinysrgb&w=800', 'Bangalô sobre a água, All Inclusive, Spa, Mergulho', 'Centara Ras Fushi Resort 5*', 'Aéreo + Hidroavião', 1),
            ('Fernando de Noronha', 'Fernando de Noronha, Brasil', 'Paraíso ecológico brasileiro com praias cristalinas e vida marinha exuberante. Inclui mergulho com golfinhos e passeios ecológicos únicos.', 2499.99, 5, 'praia', 'https://images.pexels.com/photos/1450353/pexels-photo-1450353.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Passeios, Taxa ambiental, Mergulho', 'Pousada Maravilha 4*', 'Aéreo', 0),
            ('Machu Picchu Místico', 'Cusco, Peru', 'Explore as ruínas incas e a cultura ancestral do Peru em uma jornada inesquecível. Inclui trem panorâmico e guia especializado em história inca.', 1899.99, 6, 'aventura', 'https://images.pexels.com/photos/2356045/pexels-photo-2356045.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Guia, Ingressos, Transfers, Trem', 'Hotel Monasterio Cusco 5*', 'Aéreo + Trem', 0),
            ('Búzios Relax', 'Búzios, Brasil', 'Charme e sofisticação na Península de Búzios. Praias paradisíacas, gastronomia refinada e vida noturna agitada. O destino perfeito para relaxar.', 899.99, 4, 'praia', 'https://images.pexels.com/photos/1320684/pexels-photo-1320684.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, Café da manhã, City tour, Transfer', 'Pousada Casas Brancas 5*', 'Terrestre', 0),
            ('Nova York Urbano', 'Nova York, EUA', 'A cidade que nunca dorme! Times Square, Central Park, Estátua da Liberdade e Broadway. Viva a experiência completa da Big Apple.', 3299.99, 7, 'cidade', 'https://images.pexels.com/photos/466685/pexels-photo-466685.jpeg?auto=compress&cs=tinysrgb&w=800', 'Hospedagem, City tour, Ingressos, Transfers', 'The Plaza Hotel 5*', 'Aéreo', 1)
        ]
        
        cursor.executemany('''
            INSERT INTO packages (title, destination, description, price, duration, category, image_url, includes, hotel, transport, featured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_packages)
    
    # Create admin user
    cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('admin@cvc.com',))
    if cursor.fetchone()[0] == 0:
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (email, password_hash, name, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin@cvc.com', admin_password, 'Administrador CVC', 1))
    
    conn.commit()
    conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name, is_admin=False):
        self.id = id
        self.email = email
        self.name = name
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[3], user_data[5])
    return None

# Routes
@app.route('/')
def home():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    # Get featured packages
    cursor.execute('SELECT * FROM packages WHERE featured = 1 ORDER BY created_at DESC LIMIT 6')
    featured_packages = cursor.fetchall()
    
    # Get all packages
    cursor.execute('SELECT * FROM packages ORDER BY created_at DESC')
    all_packages = cursor.fetchall()
    
    conn.close()
    
    return render_template('home.html', featured_packages=featured_packages, all_packages=all_packages)

@app.route('/search')
def search():
    destination = request.args.get('destination', '')
    category = request.args.get('category', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    query = 'SELECT * FROM packages WHERE 1=1'
    params = []
    
    if destination:
        query += ' AND (destination LIKE ? OR title LIKE ?)'
        params.extend([f'%{destination}%', f'%{destination}%'])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if min_price:
        query += ' AND price >= ?'
        params.append(min_price)
    
    if max_price:
        query += ' AND price <= ?'
        params.append(max_price)
    
    query += ' ORDER BY price ASC'
    
    cursor.execute(query, params)
    packages = cursor.fetchall()
    conn.close()
    
    return render_template('search.html', packages=packages, search_params=request.args)

@app.route('/package/<int:package_id>')
def package_detail(package_id):
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM packages WHERE id = ?', (package_id,))
    package = cursor.fetchone()
    conn.close()
    
    if not package:
        flash('Pacote não encontrado!', 'error')
        return redirect(url_for('home'))
    
    return render_template('package_detail.html', package=package)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    package_id = request.form.get('package_id')
    travelers = request.form.get('travelers', 1)
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    
    if not check_in or not check_out:
        flash('Por favor, selecione as datas de check-in e check-out!', 'error')
        return redirect(url_for('package_detail', package_id=package_id))
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    # Check if item already in cart
    cursor.execute('SELECT * FROM cart WHERE user_id = ? AND package_id = ?', 
                   (current_user.id, package_id))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE cart SET travelers = ?, check_in = ?, check_out = ? 
            WHERE user_id = ? AND package_id = ?
        ''', (travelers, check_in, check_out, current_user.id, package_id))
    else:
        cursor.execute('''
            INSERT INTO cart (user_id, package_id, travelers, check_in, check_out)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, package_id, travelers, check_in, check_out))
    
    conn.commit()
    conn.close()
    
    flash('Pacote adicionado ao carrinho!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, p.title, p.destination, p.price, p.image_url, p.duration
        FROM cart c
        JOIN packages p ON c.package_id = p.id
        WHERE c.user_id = ?
    ''', (current_user.id,))
    cart_items = cursor.fetchall()
    conn.close()
    
    total = sum(item[7] * item[3] for item in cart_items)  # price * travelers
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', (cart_id, current_user.id))
    conn.commit()
    conn.close()
    
    flash('Item removido do carrinho!', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, p.title, p.destination, p.price, p.image_url, p.duration
        FROM cart c
        JOIN packages p ON c.package_id = p.id
        WHERE c.user_id = ?
    ''', (current_user.id,))
    cart_items = cursor.fetchall()
    conn.close()
    
    if not cart_items:
        flash('Carrinho vazio!', 'error')
        return redirect(url_for('home'))
    
    total = sum(item[7] * item[3] for item in cart_items)
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    payment_method = request.form.get('payment_method')
    installments = request.form.get('installments', 1)
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    # Get cart items
    cursor.execute('''
        SELECT c.*, p.price
        FROM cart c
        JOIN packages p ON c.package_id = p.id
        WHERE c.user_id = ?
    ''', (current_user.id,))
    cart_items = cursor.fetchall()
    
    if not cart_items:
        flash('Carrinho vazio!', 'error')
        return redirect(url_for('home'))
    
    # Create bookings
    for item in cart_items:
        total_price = item[7] * item[3]  # price * travelers
        cursor.execute('''
            INSERT INTO bookings (user_id, package_id, travelers, check_in, check_out, 
                                total_price, payment_method, payment_installments, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed')
        ''', (current_user.id, item[2], item[3], item[4], item[5], 
              total_price, payment_method, installments))
    
    # Clear cart
    cursor.execute('DELETE FROM cart WHERE user_id = ?', (current_user.id,))
    
    conn.commit()
    conn.close()
    
    flash('Pagamento processado com sucesso! Suas reservas foram confirmadas.', 'success')
    return redirect(url_for('profile'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('travel_booking.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3], user_data[5])
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Email ou senha incorretos!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        conn = sqlite3.connect('travel_booking.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Email já cadastrado!', 'error')
        else:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, phone)
                VALUES (?, ?, ?, ?)
            ''', (name, email, password_hash, phone))
            conn.commit()
            flash('Cadastro realizado com sucesso!', 'success')
            conn.close()
            return redirect(url_for('login'))
        
        conn.close()
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, p.title, p.destination, p.image_url
        FROM bookings b
        JOIN packages p ON b.package_id = p.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    ''', (current_user.id,))
    bookings = cursor.fetchall()
    conn.close()
    
    return render_template('profile.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE bookings SET status = 'cancelled' 
        WHERE id = ? AND user_id = ? AND status = 'confirmed'
    ''', (booking_id, current_user.id))
    
    if cursor.rowcount > 0:
        flash('Reserva cancelada com sucesso!', 'success')
    else:
        flash('Não foi possível cancelar a reserva!', 'error')
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('profile'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Acesso negado!', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM packages ORDER BY created_at DESC')
    packages = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM bookings WHERE status = "confirmed"')
    total_bookings = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(total_price) FROM bookings WHERE status = "confirmed"')
    total_revenue = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin.html', packages=packages, 
                         total_bookings=total_bookings, total_users=total_users, 
                         total_revenue=total_revenue)

@app.route('/admin/add_package', methods=['GET', 'POST'])
@login_required
def add_package():
    if not current_user.is_admin:
        flash('Acesso negado!', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        destination = request.form.get('destination')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        duration = int(request.form.get('duration'))
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        includes = request.form.get('includes')
        hotel = request.form.get('hotel')
        transport = request.form.get('transport')
        featured = bool(request.form.get('featured'))
        
        conn = sqlite3.connect('travel_booking.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO packages (title, destination, description, price, duration, 
                                category, image_url, includes, hotel, transport, featured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, destination, description, price, duration, category, 
              image_url, includes, hotel, transport, featured))
        conn.commit()
        conn.close()
        
        flash('Pacote adicionado com sucesso!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('add_package.html')

@app.route('/admin/edit_package/<int:package_id>', methods=['GET', 'POST'])
@login_required
def edit_package(package_id):
    if not current_user.is_admin:
        flash('Acesso negado!', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM packages WHERE id = ?', (package_id,))
    package = cursor.fetchone()
    
    if not package:
        flash('Pacote não encontrado!', 'error')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        destination = request.form.get('destination')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        duration = int(request.form.get('duration'))
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        includes = request.form.get('includes')
        hotel = request.form.get('hotel')
        transport = request.form.get('transport')
        featured = bool(request.form.get('featured'))
        
        cursor.execute('''
            UPDATE packages SET title=?, destination=?, description=?, price=?, 
                              duration=?, category=?, image_url=?, includes=?, 
                              hotel=?, transport=?, featured=?
            WHERE id=?
        ''', (title, destination, description, price, duration, category, 
              image_url, includes, hotel, transport, featured, package_id))
        conn.commit()
        conn.close()
        
        flash('Pacote atualizado com sucesso!', 'success')
        return redirect(url_for('admin'))
    
    conn.close()
    return render_template('edit_package.html', package=package)

@app.route('/admin/delete_package/<int:package_id>')
@login_required
def delete_package(package_id):
    if not current_user.is_admin:
        flash('Acesso negado!', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM packages WHERE id = ?', (package_id,))
    conn.commit()
    conn.close()
    
    flash('Pacote removido com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/api/cart_count')
@login_required
def cart_count():
    conn = sqlite3.connect('travel_booking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM cart WHERE user_id = ?', (current_user.id,))
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({'count': count})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)