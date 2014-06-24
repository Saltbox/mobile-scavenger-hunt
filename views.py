from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect
from functools import wraps

from models import *
from forms import HuntForm, AdminForm, AdminLoginForm, ParticipantForm

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

            return redirect(url_for('hunts'))
    return render_template('login.html', error=error, form=form)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
def root():
    return login()


# create or list hunts
@app.route('/hunts', methods=['GET', 'POST'])
@login_required
def hunts():
    if request.method == 'POST':
        hunt = Hunt()
        form = HuntForm(request.form, hunt)  # why do i need obj?
        if form.validate():

            form.populate_obj(hunt)

            # todo: session manager

            db.session.add(hunt)
            db.session.commit()

            flash('New scavenger hunt added', 'success')
            return redirect(url_for('hunts'))
        else:
            return render_template('new_hunt.html', form=form)
    else:   # request.method == 'GET':
        hunts = db.session.query(Hunt).all()
        return render_template('hunts.html', hunts=hunts)


# edit and/or view hunt
@app.route('/hunts/<int:hunt_id>/')
@login_required
def show_hunt(hunt_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        return render_template('show_hunt.html', hunt=hunt)
    else:
        abort(404)


# form to create new hunt
@app.route('/new_hunt', methods=['GET'])
def new_hunt():
    return render_template('new_hunt.html', form=HuntForm())


################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<int:hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    logger.info(
        'preparing to render items for hunt_id, {}'.format(hunt_id))
    items = db.session.query(Item).filter(
        Item.hunt_id == hunt_id)
    return render_template('items.html', items=items, hunt_id=hunt_id)


# information about one item for scavenger to read
@app.route('/hunts/<int:hunt_id>/items/<int:item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    item = db.session.query(Item)\
        .filter(Hunt.hunt_id == hunt_id) \
        .filter(Item.item_id == item_id).first()

    if item:
        if session.get('user_id'):
            return make_response(render_template(
                'item.html', item=item, username=session['name']))
        else:
            return render_template('welcome.html', hunt_id=hunt_id)
    else:
        abort(404)


# form for scavenger hunt participant to enter email and name
@app.route('/get_started/<int:hunt_id>', methods=['GET'])
def get_started(hunt_id):
    return render_template('get_started.html',
                           form=ParticipantForm(), hunt_id=hunt_id)


# check scavenger is on whitelist and set user_id
@app.route('/new_participant', methods=['POST'])
def new_participant():
    # currently there's client-side check that these are not empty
    # but need to put in serverside validations
    logger.debug('args: %s', request.args)
    logger.debug('forms: %s', request.form)
    email = request.form['email']
    hunt_id = request.args['hunt_id']

    # check that the participant is on this hunt's whitelist
    participant = db.session.query(Participant).filter(
        Participant.hunt_id == hunt_id).first()

    if participant:
        logger.debug('participant: %s', participant)

        name = request.form.get('name')

        user_id = str(uuid.uuid4())

        session['user_id'] = user_id    # i don't remember why i need this
        session['name'] = name

        # replace with wtf
        item_id = request.args.get('item_id')
        redirect_url = '/hunts/{}/items/{}'.format(hunt_id, item_id)

        logger.info(
            "user id, name, and email set to %s, %s, and %s\n"
            "preparing requested item information.",
            user_id, name, email)

        logger.info('preparing to redirect to: %s', redirect_url)

        return make_response(redirect(redirect_url))
    else:
        return 'you are on the list of participants for this hunt' # make template


@app.route('/oops', methods=['POST'])
def oops():
    resp = make_response(render_template('goodbye.html'))
    session['user_id'] = ''  # for testing. delete later.
    return resp
