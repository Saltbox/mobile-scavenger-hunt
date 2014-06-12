import datetime
import uuid
import os

from flask import Flask, request, session, render_template, abort, flash, \
    redirect, url_for, make_response
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.assets import Environment, Bundle

from functools import wraps

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

from models import *


logger = app.logger


################ ASSETS MANAGEMENT ################
# right now just minification and concatenation

assets = Environment(app)
assets.url = app.static_url_path

css_all = Bundle(
    'css/*.css',
    filters='cssmin',
    output='dist/css_all.css'
)

my_js = Bundle(
    'js/*.js',
    filters='jsmin',
    output='dist/my_js.js'
)

vendor_js = Bundle(
    'js/vendor/*.js',
    output='dist/vendor_js.js'
)

assets.register('css_all', css_all)
assets.register('my_js', my_js)

assets.add(css_all)
assets.add(my_js)

my_js.build()
css_all.build()


#################### ADMIN ROUTES ####################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            redirect(url_for('login'))
            flash('login required')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def root():
    return hunts()


@app.route('/hunts', methods=['GET', 'POST'])
@login_required
def hunts():
    if request.method == 'POST':
        hunt_name = request.form['name']

        hunt_query = Hunt.query.filter(Hunt.name == 'hunt_name').first()
        if hunt_query:
            logger.info('hunt name already exists returning to hunt form')
            flash('a hunt named {} already exists'.format(
                hunt_name), 'danger')
            return render_template('new_hunt.html')

        hunt = Hunt(name=hunt_name)

        for email in request.form.getlist('participants'):
            hunt.participants.append(Participant(email))

        for name in request.form.getlist('items'):
            hunt.items.append(Item(name))

        hunt.date_created = hunt.last_modified = datetime.datetime.now()

        all_required = request.form['all_required']
        hunt.all_required = True if all_required.lower() == 'true' else False

        try:
            db.session.add(hunt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # should make sure fields that were ok stay populated
            flash(
                "There was an error saving your new hunt. "
                "Please try again.", "danger"
            )
            logger.debug(
                "error trying to save hunt, %s, to database: %s", hunt_name, e)
            return render_template('new_hunt.html')

        # error category (2nd arg) corresponds with bootstrap terminology
        flash('New scavenger hunt added', 'success')
        return redirect(url_for('root'))
    elif request.method == 'GET':
        hunts = Hunt.query.all()
        return render_template('hunts.html', hunts=hunts)


@app.route('/hunts/<int:hunt_id>/')
def show_hunt(hunt_id):
    hunt = Hunt.query.filter(Hunt.hunt_id == hunt_id).first()
    logger.debug("hunt: %s", hunt)
    if hunt:
        return render_template('show_hunt.html', hunt=hunt)
    flash('That hunt does not exist', 'danger')
    return render_template('hunts.html')


@app.route('/new_hunt', methods=['GET'])
def new_hunt():
    return render_template('new_hunt.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        #  change later
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')

            return redirect(url_for('hunts'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('hunts'))


#################### USER ROUTES ####################


@app.route('/hunts/<int:hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    if request.cookies.get('user_id'):
        # hm. using session here but elsewhere just using model
        items = db.session.query(Item).filter(
            Item.hunt_id == hunt_id)
        return render_template('items.html', items=items)
    return make_response(render_template('welcome.html'))


@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    if request.cookies.get('user_id'):
        logger.info(
            'user id, %s, found. preparing requested item information.',
            hunt_id
        )
        item = db.session.query(Item).filter(
            Item.hunt_id == hunt_id, Item.item_id == item_id).first()

        resp = make_response(render_template(
            'item.html', item=item, username=request.cookies['username']))
        resp.set_cookie('hunt_id', hunt_id)  # probably better way to do this
        resp.set_cookie('item_id', item_id)
        return resp

    logger.info('user id not found. requesting information from user.')
    resp = make_response(render_template('welcome.html'))
    resp.set_cookie('hunt_id', hunt_id)  # probably better way to do this
    resp.set_cookie('item_id', item_id)
    return resp


@app.route('/get_started', methods=['GET'])
def get_started():
    return render_template('get_started.html')


@app.route('/new_scavenger', methods=['POST'])
def new_scavenger():
    hunt_id = request.cookies.get('hunt_id')
    item_id = request.cookies.get('item_id')

    redirect_url = '/hunts/{}/items/{}'.format(hunt_id, item_id)

    logger.info('preparing to redirect to: %s', redirect_url)

    # currently there's client-side check that these are not empty
    # but need to put in serverside validations
    username = request.form['username']
    email = request.form['email']

    resp = make_response(redirect(redirect_url))
    logger.debug('type of hunt_id: %s', type(hunt_id))
    resp.set_cookie('user_id', str(uuid.uuid4()))
    resp.set_cookie('username', username)
    logger.info(
        "user id, username, and email set to %s, %s, and %s\n"
        "preparing requested item information.",
        str(uuid.uuid4()), username, email)
    return resp


@app.route('/oops', methods=['POST'])
def oops():
    resp = make_response(render_template('goodbye.html'))
    resp.set_cookie('user_id', '', expires=0)  # for testing. delete later.
    return resp


if __name__ == '__main__':
    app.run()
