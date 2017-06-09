from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Sport, SportItem, User
from flask import session as login_session
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextField
from wtforms import validators, ValidationError
import random
import string

# Oauth imports
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Sport Items Catalog App"


# Connect to Database and create database session
engine = create_engine('sqlite:///sportwithitems.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


#class to perform form validation
class inputForm(FlaskForm):
    name = TextField(
        'Name:',
        validators=[validators.Required("Please enter your name"),
                    validators.Length(
                        min=4, max=80, message=
                        "Name should have max 4 and min 80 characters.")])


# flask login decorator
def login_required(f):
    @wraps(f)
    def dec_func(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return dec_func


# get User ID by email
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# get User detail by user id
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# create new user
def createUser(login_session):
    newUser = User(
        name=login_session['username'],
        email=login_session['email'],
        picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Create a state token to prevent request forgery.
# Store it in session for later validation.
@app.route('/login')
def showLogin():
    up = string.ascii_uppercase
    state = ''.join(random.choice(up + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Logic for Third party Authentication and Authorization - google
@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # Upgrade the authorization code into credential object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        msg = 'Failed to upgrade the authorization code.'
        response = make_response(json.dumps(msg), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    login_session['access_token'] = access_token
    purl = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
    url = (purl % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 50)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended use
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        msg = "Token's user ID doesn't match given user ID."
        response = make_response(json.dumps(msg), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check to see if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplud_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        msg = "Token's user ID doesn't match given user ID."
        response = make_response(json.dumps(msg), 200)
        response.headers['Content-Type'] = 'application/json'

    # Store the access token in the session for the later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get User info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h2>Welcome, '
    output += login_session['username']
    output += '!</h2>'
    output += '<img src="'
    output += login_session['picture']
    output += '''"style=" width: 300px;
                    height: 300px;
                    border-radius: 150px;
                    -webkit-border-radius: 150px;
                    -moz-border-radius: 150px;">'''
    flash("you are now logged in as %s" % login_session['username'])
    return output


# Disconnect - Revoke a current user's token and reset their login_session
# Logic for logging out
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    if access_token is None:
        print 'Access Token is None'
        msg = "Token's user ID doesn't match given user ID."
        response = make_response(json.dumps(msg), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        return redirect('/sport')
    else:
        msg = 'Failed to revoke token for given user.'
        response = make_response(json.dumps(msg, 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs


# JSON endpoint for all sports
@app.route('/sport/JSON')
def sportsJSON():
    sports = session.query(Sport).all()
    return jsonify(SportList=[s.serialize for s in sports])


# JSON endpoint for all items within one sport
@app.route('/sport/<int:sport_id>/menu/JSON')
def SportItemsJSON(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    items = session.query(SportItem).filter_by(sport_id=sport_id).all()
    return jsonify(SportItemList=[i.serialize for i in items])


# JSON endpoint for detail of one item
@app.route('/sport/<int:sport_id>/menu/<int:item_id>/detail/JSON')
def ItemDetailJSON(sport_id, item_id):
    item = session.query(SportItem).filter_by(id=item_id).one()
    return jsonify(ItemDetail=item.serialize)


# Show all Sports
@app.route('/')
@app.route('/sport/')
def showSports():
    sports = session.query(Sport).order_by(asc(Sport.name))
    if 'username' in login_session:
        return render_template('sports.html', sports=sports)
    else:
        return render_template('publicsports.html', sports=sports)


# Show Menu for one Sport
@app.route('/sport/<int:sport_id>/')
@app.route('/sport/<int:sport_id>/menu/')
def showMenu(sport_id):
    sps = session.query(Sport).order_by(asc(Sport.name))
    sp = session.query(Sport).filter_by(id=sport_id).one()
    crtr = getUserInfo(sp.user_id)
    i = session.query(SportItem).filter_by(sport_id=sport_id).all()
    if 'username' not in login_session:
        l = 'publicsports.html'
        return render_template(l, sports=sps, items=i, sport=sp, creator=crtr)
    else:
        l = 'sports.html'
        return render_template(l, sports=sps, items=i, sport=sp, creator=crtr)


# Create a new Sport
@app.route('/sport/new/', methods=['GET', 'POST'])
@login_required
def newSport():
    form = inputForm(request.form)
    if request.method == 'POST':
        if form.validate() == False:
            return render_template('newSport.html', form=form)
        else:
            iname = request.form['name']
            iuserid = login_session['user_id']
            newSport = Sport(name=iname, user_id=iuserid)
            session.add(newSport)
            flash('New Sport %s Successfully Created' % newSport.name)
            session.commit()
            return redirect(url_for('showSports'))
    else:
        return render_template('newSport.html', form=form)


# Delete a sport
@app.route('/sport/<int:sport_id>/delete/', methods=['GET', 'POST'])
@login_required
def deleteSport(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if sport.user_id != login_session['user_id']:
        return redirect(url_for('error'))
    if request.method == 'POST':
        session.delete(sport)
        session.commit()
        flash('Sport %s Successfully Deleted' % sport.name)
        return redirect(url_for('showSports'))
    else:
        return render_template('deletesport.html', sport=sport)


# Show details of one sport item
@app.route('/sport/<int:sport_id>/menu/<int:item_id>/detail')
def showDetail(sport_id, item_id):
    sp = session.query(Sport).filter_by(id=sport_id).one()
    i = session.query(SportItem).filter_by(id=item_id).one()
    c = getUserInfo(sp.user_id)
    if 'username' not in login_session:
        l = 'publicdetail.html'
        return render_template(l, item=i, sport=sp, creator=c)
    else:
        return render_template('detail.html', item=i, sport=sp, creator=c)


# Create new item for one sport
@app.route('/sport/<int:sport_id>/menu/new', methods=['GET', 'POST'])
@login_required
def newItem(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if sport.user_id != login_session['user_id']:
        return redirect(url_for('error'))
    form = inputForm(request.form)
    if request.method == 'POST':
        if form.validate() == False:
            return render_template('newitem.html', form=form)
        else:
            n = request.form['name']
            d = request.form['description']
            p = request.form['price']
            c = request.form['category']
            i = sport_id
            u = sport.user_id
            newItem = SportItem(
                name=n, description=d,
                price=p, category=c,
                sport_id=i, user_id=u)
            session.add(newItem)
            session.commit()
            flash('New %s Item Successfully Created' % (newItem.name))
            return redirect(url_for('showMenu', sport_id=sport_id))
    else:
        return render_template(
            'newitem.html', sport_id=sport_id, form=form)


# Edit one item
@app.route(
    '/sport/<int:sport_id>/menu/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def editItem(sport_id, item_id):
    edI = session.query(SportItem).filter_by(id=item_id).one()
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if sport.user_id != login_session['user_id']:
        return redirect(url_for('error'))
    if request.method == 'POST':
        if request.form['name']:
            edI.name = request.form['name']
        if request.form['price']:
            edI.price = request.form['price']
        if request.form['category']:
            edI.category = request.form['category']
        if request.form['description']:
            edI.description = request.form['description']
        session.add(edI)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showMenu', sport_id=sport_id))
    else:
        return render_template(
            'edititem.html', sport_id=sport_id, item_id=item_id, item=edI)


# Delete one item
@app.route(
    '/sport/<int:sport_id>/menu/<int:item_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteItem(sport_id, item_id):
    deletedItem = session.query(SportItem).filter_by(id=item_id).one()
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if sport.user_id != login_session['user_id']:
        return redirect(url_for('error'))
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showMenu', sport_id=sport_id))
    else:
        return render_template('deleteitem.html', item=deletedItem)


# Error for Authorization
@app.route('/error/')
def error():
    message = '''You are not authorized to
        perform this task as your are not the Owner.'''
    return render_template('error.html', message=message)


if __name__ == '__main__':
    WTF_CSRF_ENABLED = True
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
