from flask import Blueprint, render_template, redirect, url_for, flash, request
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from flask_login import login_user, login_required, logout_user
from typing import Dict, Optional
import os
auth = Blueprint('auth', __name__)


def get_db_connection():
    conn = psycopg2.connect(host=os.environ['DB_HOST'],
                            database=os.environ['DB_NAME'],
                            user=os.environ['DB_USERNAME'],
                            password=os.environ['DB_PASSWORD'])
    return conn

    
@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # login code goes here
    uid = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    
    cur.execute(
        """
        SELECT *
        FROM Users u
        WHERE u.user_id = %s;
        """,
        (uid,)
    )

    user = cur.fetchone()
  
    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user[3], password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page
    
    # if the above check passes, then we know the user has the right credentials
    #login_user(User.get(uid), remember=remember)
    #if id is in Users database then create User instance rather than store them in the Users dictionary in models.py
    login_user(User(
        id=user[0],
        name=user[1],
        phone = user[2],
        password=user[3],
    ), remember=remember)
    return redirect(url_for('main.profile'))

@auth.route('/signup')
def signup():
    return render_template('signup.html')
@auth.route('/signup', methods=['POST'])
def signup_post():

    conn = get_db_connection()
    cur = conn.cursor()
    # code to validate and add user to database goes here
    uid = request.form.get('email')
    name = request.form.get('name')
    phone = request.form.get('phone')
    password = request.form.get('password')
    
    cur.execute(
        """
        SELECT user_id 
        FROM Users u
        WHERE u.user_id = %s;
        """,
        (uid,)
    )

    user = cur.fetchone()
    # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('User ID already exists')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    # add the new user to the database
    
    cur.execute('INSERT INTO Users (user_id,user_name,user_phone,user_password)'
                'VALUES (%s, %s, %s, %s)',
                (uid, name, phone, generate_password_hash(password, method='sha256')))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('auth.login'))
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))