from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect, send_file
from functools import wraps


import datetime
import uuid
import io
import os

from models import Hunt, Participant, Item, Admin, db
from forms import HuntForm, AdminForm, AdminLoginForm, ParticipantForm
from hunt import app, logger

import qrcode


#################### ADMIN ROUTES ####################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('login required')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_admin(email, password):
    return db.session.query(Admin).filter(
        Admin.email == email,
        Admin.password == password
    ).first()


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = AdminLoginForm(request.form)
    if request.method == 'POST' and form.validate():
        #  change later
        matched_admin = get_admin(form.username.data, form.password.data)
        if matched_admin:
            session['logged_in'] = True
            flash('You were logged in')
            # logger.debug('you were logged in')
            session['admin_id'] = matched_admin.admin_id
            return redirect(url_for('hunts'))
        # logger.debug('invalid email or password')
        flash('Invalid email or password')
    # logger.debug('rendering login page: %s', session)
    return render_template('login.html', error=error, form=form)


@app.route('/logout')
def logout():
    for prop in ['admin_id', 'user_id', 'logged_in', 'name']:
        session.pop(prop, None)
    # logger.debug('logout session: %s', session)
    return redirect(url_for('login'))


@app.route('/')
def root():
    if session.get('logged_in'):
        return hunts()
    return login()


# create or list admins who can create hunts # probably rename to signup
@app.route('/admins', methods=['GET', 'POST'])
def admins():
    admin = Admin()
    form = AdminForm(request.form)
    if request.method == 'POST':
        # logger.debug('attempting to create admin')
        if form.validate():
            form.populate_obj(admin)
            db.session.add(admin)
            db.session.commit()

            session['logged_in'] = True
            flash('Successfully created admin')

            session['admin_id'] = get_admin(
                form.email.data, form.password.data).admin_id
            # logger.debug('valid admin form session: %s', session)
            return render_template('hunts.html')

        flash(
            'There was an error creating your admin profile. Please try again')
    # logger.debug('rendering admin signup')
    return render_template('admin_signup.html', form=form)


# create or list hunts
@app.route('/hunts', methods=['GET', 'POST'])
@login_required
def hunts():
    if request.method == 'POST':
        # logger.debug('request form in create hunts: %s', request.form)
        hunt = Hunt()
        form = HuntForm(request.form)
        if form.validate():
            hunt.owner = session['admin_id']
            form.populate_obj(hunt)

            # todo: session manager
            db.session.add(hunt)
            db.session.commit()

            flash('New scavenger hunt added', 'success')
            return redirect(url_for('hunts'))
        else:
            flash('some error msg about invalid form')
            return render_template('new_hunt.html', form=form)
    else:   # request.method == 'GET':
        # logger.debug('rendering hunts table: %s', session)
        hunts = db.session.query(Hunt).filter(
            Hunt.owner == session['admin_id']).all()
        return render_template('hunts.html', hunts=hunts)


# edit and/or view hunt
@app.route('/hunts/<hunt_id>')
@login_required
def show_hunt(hunt_id):
    # logger.debug('showing hunt: %s', hunt_id)
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        return render_template('show_hunt.html', hunt=hunt)
    else:
        abort(404)


# form to create new hunt
@app.route('/new_hunt', methods=['GET'])
def new_hunt():
    # logger.debug('rendering new hunt page')
    return render_template('new_hunt.html', form=HuntForm())


def item_path(hunt_id, item_id):
    app_root = os.path.dirname(os.path.abspath(__file__))
    return "{}/hunts/{}/items/{}".format(app_root, hunt_id, item_id)


@app.route('/hunts/<hunt_id>/qrcodes')
def show_item_codes(hunt_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        # must figure out how to get multiple on one page without google
        item_paths = [
            {'name': item.name, 'path': item_path(hunt_id, item.item_id)}
            for item in hunt.items
        ]
        return make_response(render_template(
            'qrcodes.html', item_paths=item_paths))
    else:
        abort(404)


def create_qrcode_binary(qrcode):
    output = io.BytesIO()
    qrcode.save(output, 'PNG')
    return output.getvalue()


@app.route('/hunts/<hunt_id>/items/<item_id>/qrcode', methods=['GET'])
def show_item_code(hunt_id, item_id):
    # add check for hunt id and item id
    code = qrcode.make(item_path(hunt_id, item_id))
    hex_data = create_qrcode_binary(code)

    response = make_response(hex_data)
    response.headers['Content-Type'] = 'image/png'
    response.headers['Content-Disposition'] = 'filename=qrcode-hunt-{}-item-{}.jpg'.format(hunt_id, item_id)
    return response


################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    logger.info(
        'preparing to render items for hunt_id, {}'.format(hunt_id))
    items = db.session.query(Item).filter(
        Item.hunt_id == hunt_id).all()
    if items:
        return render_template('items.html', items=items, hunt_id=hunt_id)
    abort(404)


# information about one item for scavenger to read
@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    item = db.session.query(Item)\
        .filter(Hunt.hunt_id == hunt_id) \
        .filter(Item.item_id == item_id).first()

    if item:
        if session.get('user_id'):
            return make_response(render_template(
                'item.html', item=item, username=session['name']))
        else:
            return render_template(
                'welcome.html', hunt_id=hunt_id, item_id=item_id)
    else:
        abort(404)


# form for scavenger hunt participant to enter email and name
@app.route('/get_started/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def get_started(hunt_id, item_id):
    return render_template('get_started.html',
                           form=ParticipantForm(),
                           hunt_id=hunt_id, item_id=item_id)


# check scavenger is on whitelist and set user_id
@app.route('/new_participant', methods=['POST'])
def new_participant():
    logger.debug('partip form: %s', request.form)
    form = ParticipantForm(request.form)
    if form.validate():
        hunt_id = request.args['hunt_id']
        email = form.email.data

        # check that the participant is on this hunt's whitelist
        listed_participant = db.session.query(Participant)\
            .filter(Participant.hunt_id == hunt_id,
                    Participant.email == email).first()
        if listed_participant:
            name = form.name.data
            user_id = str(uuid.uuid4())

            session['user_id'] = user_id
            session['name'] = name

            item_id = request.args.get('item_id')
            redirect_url = '/hunts/{}/items/{}'.format(hunt_id, item_id)

            logger.info(
                "user id, name, and email set to %s, %s, and %s\n"
                "preparing requested item information.",
                user_id, name, email)

            logger.info('preparing to redirect to: %s', redirect_url)

            return make_response(redirect(redirect_url))
        else:
            return 'you are not on the list of participants for this hunt' # make template
    abort(400)


@app.route('/oops', methods=['GET', 'POST'])
def oops():
    resp = make_response(render_template('goodbye.html'))
    # for testing. delete later.
    session['user_id'] = ''
    session['admin_id'] = ''
    return resp
