from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import random
import os
from datetime import datetime 
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") or 'somethingsecret'
app.config['SQLALCHEMY_DATABASE_URI'] =  os.environ.get('DATABASE_URI') or 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean(), default=True)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(100), nullable=False, default='Enjoy!')
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # one payer and one payee
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# relationship table
user_transactions = db.Table('user_transactions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('transaction_id', db.Integer, db.ForeignKey('transactions.id'), primary_key=True)
)

with app.app_context():
    db.init_app(app)
    login_manager.init_app(app)
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()

@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user is not None and user.password == password:
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registered and Logged in successfully.')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    users = User.query.all()

    if request.method == 'POST':

        amount = request.form['amount']
        description = request.form['description'] or 'Enjoy!'
        payee_users = request.form.getlist('payee')
        # print(payee_users)

        if(len(payee_users) == 0):
            flash('No users selected.')
            return redirect(url_for('dashboard'))

        payee_users = [User.query.get(int(id)) for id in payee_users]

        x = float(amount)/len(payee_users)

        for user in payee_users:
            transaction = Transaction(amount=x, description=description, payee_id=user.id, payer_id=current_user.id)
            db.session.add(transaction)
            db.session.commit()
        flash('Transaction added successfully.')
        return redirect(url_for('dashboard'))


    # convert users list to dictionary with key as id
    users = {user.id: user for user in users}
    transactions = Transaction.query.filter(or_(Transaction.payer_id==current_user.id, Transaction.payee_id==current_user.id)).all() 

    return render_template('dashboard.html', cur_user=current_user, transactions=transactions, users=users)

@app.route('/delete_transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.filter_by(id=id).first()
    if transaction is not None:
        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted successfully.')
    return redirect(url_for('dashboard'))

if(__name__ == '__main__'):
    app.run(debug=True)
