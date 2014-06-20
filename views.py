from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect
from functools import wraps

from models import *
from forms import HuntForm, AdminLoginForm, ParticipantLoginForm

import datetime
import uuid
import os

from hunt import app, logger


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
        hunt = Hunt()
        form = HuntForm(request.form, obj=hunt)
        if form.validate():
            form.populate_obj(hunt)
            # todo: session manager
            db.session.add(hunt)
            db.session.commit()
            flash('New scavenger hunt added', 'success')
            return redirect(url_for('root'))
        else:
            return render_template('new_hunt.html', form=form)
    else:   # request.method == 'GET':
        hunts = db.session.query(Hunt).all()
        return render_template('hunts.html', hunts=hunts)


@app.route('/hunts/<int:hunt_id>/')
def show_hunt(hunt_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        return render_template('show_hunt.html', hunt=hunt)
    else:
        abort(404)


@app.route('/new_hunt', methods=['GET'])
def new_hunt():
    return render_template('new_hunt.html', form=HuntForm())


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = AdminLoginForm(request.form)
    if request.method == 'POST' and form.validate():
        #  change later
        if form.username.data != app.config['USERNAME']:
            error = 'Invalid username'
        elif form.password.data != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            # figure out how to redirect to whatever page they want to go to
            # probably a request var
            return redirect(url_for('hunts'))
    return render_template('login.html', error=error, form=form)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('hunts'))


#################### USER ROUTES ####################

def set_session_ids(hunt_id, item_id):
    session['hunt_id'] = hunt_id  # probably better way to do this
    session['item_id'] = item_id


@app.route('/hunts/<int:hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    set_session_ids(hunt_id, None)
    if session.get('user_id'):
        # hm. using session here but elsewhere just using model
        logger.info(
            'preparing to render items for hunt_id, {}'.format(hunt_id))
        items = db.session.query(Item).filter(
            Item.hunt_id == hunt_id)
        return render_template('items.html', items=items)
    return make_response(render_template('welcome.html'))


@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    if session.get('user_id'):
        logger.info(
            'user id, %s, found. preparing requested item information.',
            hunt_id
        )
        item = db.session.query(Item).filter(
            Item.hunt_id == hunt_id, Item.item_id == item_id).first()

        resp = make_response(render_template(
            'item.html', item=item, username=session['name']))

        set_session_ids(hunt_id, item_id)
        return resp

    logger.info('user id not found. requesting information from user.')
    resp = make_response(render_template('welcome.html'))
    set_session_ids(hunt_id, item_id)
    return resp


@app.route('/get_started', methods=['GET'])
def get_started():
    return render_template(
        'get_started.html', form=ParticipantLoginForm())


@app.route('/new_scavenger', methods=['POST'])
def new_scavenger():
    hunt_id = session.get('hunt_id')
    item_id = session.get('item_id')

    if item_id:
        redirect_url = '/hunts/{}/items/{}'.format(hunt_id, item_id)
    else:
        redirect_url = 'hunts/{}/items'.format(hunt_id)

    logger.info('preparing to redirect to: %s', redirect_url)

    # currently there's client-side check that these are not empty
    # but need to put in serverside validations
    name = request.form.get('name')
    email = request.form.get('email')
    logger.debug('name, email: %s, %s', name, email)
    resp = make_response(redirect(redirect_url))
    session['user_id'] = str(uuid.uuid4())
    session['name'] = name
    logger.info(
        "user id, name, and email set to %s, %s, and %s\n"
        "preparing requested item information.",
        str(uuid.uuid4()), name, email)
    return resp


@app.route('/oops', methods=['POST'])
def oops():
    resp = make_response(render_template('goodbye.html'))
    session['user_id'] = ''  # for testing. delete later.
    return resp
