from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import psycopg2
import psycopg2.extras
import datetime
import os
def get_db_connection():
    conn = psycopg2.connect(host=os.environ['DB_HOST'],
                            database=os.environ['DB_NAME'],
                            user=os.environ['DB_USERNAME'],
                            password=os.environ['DB_PASSWORD'])
    return conn
    
main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return render_template('index.html', name=current_user.name)

@main.route('/welcome')
def welcome():
    return render_template('welcome.html')

@main.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute(
                """
                SELECT rr.restaurant_name
                FROM recommends r, Restaurants rr
                WHERE r.user_id = %s AND r.restaurant_id=rr.restaurant_id;
                """,
                (current_user.id,)
            )

    rec = cur.fetchall()
    if len(rec)>0:
        return render_template('profile.html', current_user=current_user,recommendations=rec)
    else:
        return render_template('profile.html', current_user=current_user,recommendations=None)
    

@main.route('/restaurant/search/',methods=['GET','POST'])
@login_required    
def search():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        
        # login code goes here
        rname = request.form.get('rname')
        cuisine = request.form.get('cuisine')
        region = request.form.get('region')
        
        restaurants_found = []
        rid = None
        if rname != "":
            cur.execute(
                    """
                    SELECT *
                    FROM Restaurants r
                    WHERE r.restaurant_name = %s ;
                    """,
                (rname,)
            )

            r1 = cur.fetchall()
            restaurants_found.extend(r1)
            
            rid = set([res_['restaurant_id'] for res_ in r1])
        if cuisine != "":
            cur.execute(
                """
                SELECT *
                FROM Restaurants r
                NATURAL JOIN serves s
                WHERE s.cuisine_name = %s;
                """,
                (cuisine,)
            )

            r2 = cur.fetchall()
            restaurants_found.extend(r2)
            if rid:
                rid = list(rid| set([res_['restaurant_id'] for res_ in r2]))
            else:
                rid = set([res_['restaurant_id'] for res_ in r2])
        if region != "":
            cur.execute(
                """
                SELECT *
                FROM Restaurants r
                NATURAL JOIN locates l
                NATURAL JOIN Regions re
                WHERE re.zip_code = %s ;
                """,
                (region,)
            )

            r3 = cur.fetchall()
            restaurants_found.extend(r3)
            if rid:
                rid = list(rid| set([res_['restaurant_id'] for res_ in r3]))
            else:
                rid = set([res_['restaurant_id'] for res_ in r3])
        
        if len(rid)==0:
            flash('No candidate found!')
            return render_template('search.html',
                               restaurants_found = None)
        
        restaurants_found = [res_ for res_ in restaurants_found if res_['restaurant_id'] in rid]
        regions = []
        hours = []
        cuisines = []
        
        for res_ in restaurants_found:
            cur.execute(
                """
                SELECT re.*
                FROM Restaurants r
                NATURAL JOIN locates l
                NATURAL JOIN Regions re
                WHERE r.restaurant_id = %s ;
                """,
                (res_['restaurant_id'],)
            )

            region_ = cur.fetchall()
            if len(region_)>0:
                regions.append(','.join(list(region_[0].values())))
            else:
                regions.append('unkown')
                
            cur.execute(
                """
                SELECT s.cuisine_name
                FROM Restaurants r
                NATURAL JOIN serves s
                WHERE r.restaurant_id = %s ;
                """,
                (res_['restaurant_id'],)
            )

            cuisine_ = cur.fetchall()
            if len(cuisine_)>0:
                cuisines.append(cuisine_[0]['cuisine_name'])
            else:
                cuisines.append('unkown')
                
            cur.execute(
                """
                SELECT h.*
                FROM Restaurants r
                NATURAL JOIN opens_at o
                NATURAL JOIN Hours h
                WHERE r.restaurant_id = %s ;
                """,
                (res_['restaurant_id'],)
            )

            hour_ = cur.fetchall()
            if len(hour_)>0:
                hours.append(list(hour_[0].values())[1:])
            else:
                hours.append(['unkown']*7)
        return render_template('search.html',
                               restaurants_found = restaurants_found, hours=hours,regions=regions,cuisines=cuisines)

    else:
        return render_template('search.html')
        
@main.route('/<restaurant_id>/review', methods=['GET','POST'])
@login_required
def review(restaurant_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    
    uid = current_user.id
    cur.execute("""
            SELECT *
            FROM reviews r
            WHERE r.restaurant_id = %s AND r.user_id = %s;
            """,
            (restaurant_id,uid))
    rev = cur.fetchall()
   
    if request.method == 'POST':
        content = request.form.get('content')
        rating = request.form.get('rating')
        rev_time = str(datetime.datetime.now())
        recommend = True if request.form.get('recommend') else False
        
        if len(rev)>0:
            rev_time_ = rev[0]['review_time']
            rev_time_.append(rev_time)
            content_ = rev[0]['text']
            content_.append(content)
            rating_ = rev[0]['review_rating'].strip('{}').split(',')
            rating_.append(rating)
            rev_time_ = [str(rt) for rt in rev_time_]
            cur.execute(""" UPDATE reviews
                SET review_time = %s , text = %s, review_rating = %s::stars[]
                WHERE restaurant_id = %s AND user_id = %s """,
                (str(rev_time_).replace('[','{').replace(']','}'), str(content_).replace('[','{').replace(']','}'),rating_,restaurant_id, uid))
        else:            
            cur.execute('INSERT INTO reviews (restaurant_id,user_id,text,review_time,review_rating)'
                    'VALUES (%s, %s, %s, %s, %s)',
                    (restaurant_id, uid,  '{'+str(content)+'}','{'+str(rev_time)+'}','{'+str(rating)+'}'))
        
        
        
        
        if recommend:
            try:
                cur.execute('INSERT INTO recommends (restaurant_id,user_id)'
                        'VALUES (%s, %s)',
                        (restaurant_id, uid))
            except:
                pass
        conn.commit()
        flash('Success!')    
        
    cur.execute("""
            SELECT *
            FROM reviews r
            WHERE r.restaurant_id = %s AND r.user_id = %s;
            """,
            (restaurant_id,uid))
    rev = cur.fetchall()
    
    cur.close()
    conn.close()
    if len(rev)>0:
        print(rev[0])
        return render_template('review.html',data=['1.0','1.5','2.0','2.5','3.0','3.5','4.0','4.5','5.0'],reviews=rev[0],restaurant_id=restaurant_id)
    else:
        return render_template('review.html',data=['1.0','1.5','2.0','2.5','3.0','3.5','4.0','4.5','5.0'],reviews=None,restaurant_id=restaurant_id)   

@main.route('/<restaurant_id>/reservation', methods=['GET','POST'])
@login_required
def reservation(restaurant_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    
    uid = current_user.id
    cur.execute("""
            SELECT *
            FROM reserves r
            WHERE r.restaurant_id = %s AND r.user_id = %s;
            """,
            (restaurant_id,uid))
    res = cur.fetchall()
   
    if request.method == 'POST':
        res_time = request.form.get('time')
        pnum = request.form.get('#people')
        
        if len(res)>0:
            res_time_ = res[0]['reservation_time']
            res_time_.append(res_time)
            pnum_ = res[0]['number_of_people']
            pnum_.append(pnum)
            res_time_ = [str(rt) for rt in res_time_]
            pnum_ = [int(n) for n in pnum_]
            cur.execute(""" UPDATE reserves
                SET reservation_time = %s , number_of_people = %s
                WHERE restaurant_id = %s AND user_id = %s """,
                (str(res_time_).replace('[','{').replace(']','}'), str(pnum_).replace('[','{').replace(']','}'),restaurant_id, uid,))
        else:
            res_time_=str(res_time)
            pnum_ = str(pnum)
        
            cur.execute('INSERT INTO reserves (restaurant_id,user_id,reservation_time,number_of_people)'
                    'VALUES (%s, %s, %s, %s)',
                    (restaurant_id, uid, '{'+str(res_time_)+'}', '{'+str(pnum_)+'}'))
        conn.commit()
        
        flash('Success!')
        
    cur.execute("""
            SELECT *
            FROM reserves r
            WHERE r.restaurant_id = %s AND r.user_id = %s;
            """,
            (restaurant_id,uid))
    res = cur.fetchall()
    
    cur.close()
    conn.close()
    if len(res)>0:
        print(res[0])
        return render_template('reservation.html',reservations=res[0],restaurant_id=restaurant_id)
    else:
        return render_template('reservation.html',reservations=None,restaurant_id=restaurant_id)
