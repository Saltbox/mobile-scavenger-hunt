from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect
from functools import wraps

from models import *
from forms import HuntForm, AdminLoginForm, ParticipantLoginForm

import datetime
import uuid
import os

from hunt import app


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
        hunts = Hunt.query.all()
        return render_template('hunts.html', hunts=hunts)


@app.route('/hunts/<int:hunt_id>/')
def show_hunt(hunt_id):
    hunt = Hunt.query.filter(Hunt.hunt_id == hunt_id).first()
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
    return render_template(
        'get_started.html', form=ParticipantLoginForm())


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
