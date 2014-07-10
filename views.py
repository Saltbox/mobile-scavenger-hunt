from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect, send_file
from functools import wraps

import datetime
import uuid
import io

import qrcode

from models import Hunt, Participant, Item, Admin, db, Setting
from forms import HuntForm, AdminForm, AdminLoginForm, ParticipantForm, \
    SettingForm
from hunt import app, logger

import xapi

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
            session['admin_id'] = matched_admin.admin_id
            return redirect(url_for('hunts'))
        flash('Invalid email or password')
    return render_template(
        'login.html', error=error, form=form, display_login_link=True)


@app.route('/logout')
def logout():
    for prop in ['admin_id', 'user_id', 'logged_in', 'name']:
        session.pop(prop, None)

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
        if form.validate():
            logger.debug('valid admin form submission')
            form.populate_obj(admin)
            db.session.add(admin)
            db.session.commit()

            session['logged_in'] = True
            flash('Successfully created admin')

            session['admin_id'] = get_admin(
                form.email.data, form.password.data).admin_id
            return render_template('settings.html')
        logger.info('Admin signup form was submitted with invalid information')
        flash(
            'There was an error creating your admin profile. Please try again')
    return render_template(
        'admin_signup.html', form=form, display_login_link=True)


# create or list hunts
@app.route('/hunts', methods=['GET', 'POST'])
@login_required
def hunts():
    if request.method == 'POST':
        hunt = Hunt()
        form = HuntForm(request.form)
        if form.validate():
            hunt.admin_id = session['admin_id']
            form.populate_obj(hunt)

            # todo: session manager
            db.session.add(hunt)
            db.session.commit()

            flash('New scavenger hunt added', 'success')
            logger.info(
                'hunt, %s, created for admin with id, %s',
                hunt.name, hunt.admin_id)
            return redirect(url_for('hunts'))
        else:
            flash('some error msg about invalid form')
            return render_template('new_hunt.html', form=form)
    else:
        hunts = db.session.query(Hunt).filter(
            Hunt.admin_id == session['admin_id']).all()
        return render_template('hunts.html', hunts=hunts)


# edit and/or view hunt
@app.route('/hunts/<hunt_id>')
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


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)


@app.route('/hunts/<hunt_id>/qrcodes')
def show_item_codes(hunt_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        # todo: figure out how to get multiple on one page without google
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
    disposition = 'filename=qrcode-hunt-{}-item-{}.jpg'.format(
        hunt_id, item_id)
    response.headers['Content-Disposition'] = disposition
    return response


def get_setting(admin_id=None, hunt_id=None):
    if admin_id:
        return db.session.query(Setting).filter(
            Setting.admin_id == admin_id).first()
    elif hunt_id:
        return db.session.query(Setting).join(Admin).join(Hunt).first()


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        setting = get_setting(session['admin_id']) or Setting()
        form = SettingForm(request.form)
        if form.validate():
            setting.admin_id = session['admin_id']
            form.populate_obj(setting)
            db.session.add(setting)
            db.session.commit()
            flash('Settings have been updated')
        else:
            # get the erros from form. i think it's form.errors
            flash('Invalid setting information. '
                  'Please check your form entries and try again.')

    setting = get_setting(admin_id=session['admin_id'])
    login = getattr(setting, 'login', '')
    password = getattr(setting, 'password', '') # or just None is probably fine
    endpoint = getattr(setting, 'endpoint', '')

    return make_response(render_template(
        'settings.html', login=login, password=password,
        endpoint=endpoint))


def get_hunt(hunt_id):
    return db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()


def get_item(item_id):
    return db.session.query(Item).filter(Item.item_id == item_id).first()


################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    logger.info(
        'preparing to render items for hunt_id, {}'.format(hunt_id))

    if get_hunt(hunt_id):
        if session.get('email'):
            logger.debug('session: %s', session)
            items = db.session.query(Item).filter(Item.hunt_id == hunt_id).all()
            required_ids = [item.item_id for item in items if item.required]
            logger.debug('required ids: %s', required_ids)

            params = xapi.default_params(session['email'], hunt_id)
            setting = get_setting(hunt_id=hunt_id)
            if xapi.get_state_response(params, setting).status_code != 200:
                data = {
                    'num_found': 0,
                    'required_ids': required_ids,
                    'total_items': db.session.query(Item).filter(
                        Item.hunt_id == hunt_id).count()
                }
                xapi.initialize_state_doc(
                    hunt_id, session['email'], params, data, setting)
            return render_template('items.html', items=items, hunt_id=hunt_id)
        return get_started(hunt_id)

    abort(404)


def listed_participant(email, hunt_id):
    return db.session.query(Participant).filter(
        Participant.hunt_id == hunt_id, Participant.email == email).first()


# later prevent resending statements if they for whatever reason scan the qrcode
# multiple times
def send_statements(email, hunt, item, state, setting):
    actor = xapi.make_agent(email)
    params = xapi.default_params(session['email'], hunt.hunt_id)

    logger.debug(
        'participant found item, %s, sending statement to wax', item.name)
    xapi.send_statement(
        xapi.found_item_statement(actor, hunt, item), setting)

    if state['num_found'] == hunt.num_required and not state['required_ids']:
        logger.debug(
            'participant found required items. sending statement to Wax')
        xapi.send_statement(
            xapi.found_all_required_statement(actor, hunt), setting)

    if state['num_found'] == state['total_items_count']:
        logger.debug(
            'participant completed hunt. sending statement to Wax')
        xapi.send_statement(
            xapi.completed_hunt_statement(actor, hunt), setting)
        return make_response(render_template('congratulations.html'))


# information about one item for scavenger to read
@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    def update_state(params, setting):
        state = xapi.get_state_response(params, setting).json()
        logger.debug('state: %s', state)
        state['num_found'] += 1
        if hunt_id in state['required_ids']:
            state['required_ids'].remove(hunt_id)
        return state

    # right now ids are unique, not unique to the hunt. so i could fix this.
    item = db.session.query(Item)\
        .filter(Hunt.hunt_id == hunt_id) \
        .filter(Item.item_id == item_id).first()

    if item:
        hunt = get_hunt(hunt_id)
        email = session['email']

        if listed_participant(email, hunt_id):
            params = xapi.default_params(email, hunt_id)

            # what if they somehow go here first?
            setting = get_setting(hunt_id=hunt_id)

            state = update_state(params, setting)
            xapi.post_state(state, params, setting)

            send_statements(email, hunt, item, state, setting)
            return make_response(render_template(
                'item.html', item=item, username=session['name'],
                num_found=state['num_found'],
                total_items=state['total_items_count']))
        else:
            return make_response(render_template(
                'welcome.html',
                action_url="/get_started/hunts/{}/items".format(hunt_id)))
    else:
        abort(404)


# maybe just get rid of this
# form for scavenger hunt participant to enter email and name
@app.route('/get_started/hunts/<hunt_id>/items', methods=['GET'])
def get_started(hunt_id):
    # todo: track duration
    return render_template('get_started.html', form=ParticipantForm(),
                           hunt_id=hunt_id)


# check scavenger is on whitelist and set user_id
@app.route('/new_participant', methods=['POST'])
def new_participant():
    logger.debug('partip form: %s', request.form)
    form = ParticipantForm(request.form)
    if form.validate():
        hunt_id = request.args['hunt_id']
        email = form.email.data

        if listed_participant(email, hunt_id):
            name = form.name.data
            user_id = str(uuid.uuid4())

            session['user_id'] = user_id
            session['name'] = name
            session['email'] = email

            redirect_url = 'hunts/{}/items'.format(hunt_id)

            logger.info(
                "user id, name, and email set to %s, %s, and %s\n"
                "preparing requested item information.",
                user_id, name, email)

            logger.info('preparing to redirect to: %s', redirect_url)

            statement = xapi.begin_hunt_statement(
                xapi.make_agent(email), get_hunt(hunt_id))
            xapi.send_statement(statement, get_setting(hunt_id=hunt_id))

            return make_response(redirect(redirect_url))
        else:
            return 'you are not on the list of participants for this hunt'
            # make template
    abort(400)


@app.route('/oops', methods=['GET', 'POST'])
def oops():
    # for testing. delete later.
    session['user_id'] = ''
    session['admin_id'] = ''
    session['email'] = ''

    return make_response(render_template('goodbye.html'))
