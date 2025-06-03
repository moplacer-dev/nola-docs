from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db, ActivityLog
from werkzeug.security import generate_password_hash
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial setup route - only accessible when no admin exists"""
    # Check if any admin already exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    if existing_admin:
        flash('Admin user already exists. Please use the login page.', 'info')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        # Validate required fields
        if not email or not username or not password:
            flash('Email, username, and password are required.', 'error')
            return render_template('auth/setup.html')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/setup.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('auth/setup.html')
        
        try:
            # Create admin user
            admin = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=True,
                is_active=True
            )
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            # Log the admin creation
            ActivityLog.log_activity('admin_created', admin.id, 
                                    {'setup_via': 'web_interface'}, request)
            db.session.commit()
            
            flash('Admin user created successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating admin user: {str(e)}', 'error')
            return render_template('auth/setup.html')
    
    return render_template('auth/setup.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            
            # Log successful login
            ActivityLog.log_activity('user_login', user.id, {'method': 'email'}, request)
            db.session.commit()
            
            # Redirect to intended page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            ActivityLog.log_activity('login_failed', None, {'email': email}, request)
            db.session.commit()
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    ActivityLog.log_activity('user_logout', current_user.id, request=request)
    db.session.commit()
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('index'))

@auth.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        is_admin = bool(request.form.get('is_admin'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/create_user.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('auth/create_user.html')
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        ActivityLog.log_activity('user_created', current_user.id, 
                                {'new_user_email': email, 'is_admin': is_admin}, request)
        db.session.commit()
        
        flash(f'User {username} created successfully', 'success')
        return redirect(url_for('auth.admin_users'))
    
    return render_template('auth/create_user.html')

@auth.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/admin_users.html', users=users) 