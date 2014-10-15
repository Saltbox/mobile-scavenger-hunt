from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect, g, jsonify
from sqlalchemy.exc import IntegrityError
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

import uuid
import json

from models import Hunt, Participant, Item, Admin, Setting
from forms import HuntForm, AdminForm, AdminLoginForm, ParticipantForm, \
    ItemForm, SettingForm
import hunt
from hunt import app, logger, login_manager, db, bcrypt
from utils import get_admin, get_settings, get_hunt, get_item, \
    get_participant, item_path, validate_participant, get_intended_url, \
    get_hunts, get_items, initialize_hunt, initialize_registered_participant, \
    valid_login, finished_setting

import xapi


login_manager.login_view = "login"


def get_db():
    return db


@app.before_request
def before_request():
    g.db = get_db()


@login_manager.user_loader
def load_user(userid):
    return Admin.query.get(userid)

#################### ADMIN ROUTES ####################


@app.route('/login', methods=['GET', 'POST'])
def login():
    errors = None
    form = AdminLoginForm(request.form)
    if request.method == 'POST' and form.validate():
        admin = get_admin(g.db, form.email.data)
        if valid_login(admin, form.email.data, form.password.data):
            login_user(admin)
            return redirect(url_for('hunts'))
        flash('Invalid email and password combination')
    else:
        errors = form.errors
    return make_response(render_template(
        'homepage.html', form=form, display_login_link=True))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
def root():
    return login()


# create or list admins who can create hunts
@app.route('/admins', methods=['POST'])
def admins():
    form = AdminForm(request.form)
    if request.method == 'POST':
        if form.validate():
            admin = Admin()
            form.populate_obj(admin)
            admin.pw_hash = bcrypt.generate_password_hash(form.password.data)

            g.db.session.add(admin)
            g.db.session.commit()

            saved_admin = get_admin(g.db, admin.email)
            login_user(saved_admin)

            flash('Welcome to xAPI Scavenger Hunt', 'success')
            logger.info(
                'Admin registration form was submitted successfully for %s',
                admin.email)
            return make_response(render_template(
                'settings.html', form=SettingForm()))

        logger.info(
            'Admin registration form was submitted with'
            ' invalid information. Errors: %s', form.errors)
        flash(
            'There was an error creating your admin profile.'
            ' Please try again.', 'warning')
        return render_template(
            'homepage.html', form=form, display_login_link=True)
    return login()


# settings page primarily for connecting to Wax LRS
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    errors = None
    admin_settings = get_settings(
        g.db, admin_id=current_user.admin_id) or Setting()
    form = SettingForm(request.form)
    if request.method == 'POST':
        if form.validate():
            first_submission = not admin_settings
            form.populate_obj(admin_settings)
            admin_settings.admin_id = current_user.admin_id

            g.db.session.add(admin_settings)
            g.db.session.commit()

            if first_submission:
                return make_response(redirect(url_for('new_hunt')))
            else:
                return make_response(redirect(url_for('hunts')))
        else:
            logger.info(
                '%s attempted to submit settings information'
                ' resulting in errors: %s', current_user.email, form.errors)
    return make_response(render_template(
        'settings.html', login=admin_settings.login,
        password=admin_settings.password, wax_site=admin_settings.wax_site,
        form=form
    ))


# list hunts
@app.route('/hunts', methods=['GET'])
@login_required
def hunts():
    hunts = get_hunts(g.db, current_user.admin_id)
    return render_template('hunts.html', hunts=hunts)


# form to create new hunt
@app.route('/new_hunt', methods=['GET', 'POST'])
@login_required
def new_hunt():
    setting = get_settings(g.db, admin_id=current_user.admin_id)
    if not finished_setting(setting):
        flash('You must complete your settings information before'
              ' creating a hunt', 'warning')
        return redirect(url_for('settings'))

    hunt = Hunt()
    form = HuntForm(request.form)

    if request.method == 'POST':
        if form.validate():
            hunt = initialize_hunt(form, hunt, current_user.admin_id, request)

            try:
                g.db.session.add(hunt)
                g.db.session.commit()
            except IntegrityError as e:
                flash('Error creating form: hunt name, "{}", '
                      'already exists'.format(hunt.name), 'warning')
                logger.warning(
                    'Exception found while creating hunt with an existing '
                    ' name: %s\n Form data: %s ', e, form.data)
                abort(400)

            flash('New scavenger hunt added', 'success')
            logger.info('hunt, %s, created for admin with id, %s',
                        hunt.name, hunt.admin_id)

            saved_hunt = g.db.session.query(Hunt).order_by(
                Hunt.hunt_id.desc()).first()
            return jsonify({'hunt_id': saved_hunt.hunt_id})
        else:
            flash('Error creating hunt: {}'.format(form.errors), 'warning')
            logger.warning('Error creating hunt.\nForm errors: %s\nForm data: '
                           '%s ', form.errors, form.data)
    domain = current_user.email.split('@')[-1]
    return make_response(
        render_template('new_hunt.html', form=form, domain=domain))


# page to view hunt
@app.route('/hunts/<hunt_id>', methods=['GET'])
@login_required
def hunt(hunt_id):
    hunt = get_hunt(g.db, hunt_id)
    if hunt:
        registered = []
        unregistered = []
        for participant in hunt.participants:
            if participant.registered:
                registered.append(participant)
            else:
                unregistered.append(participant)
        return render_template(
            'show_hunt.html', hunt=hunt, registered_participants=registered,
            unregistered_participants=unregistered)
    abort(404)


# check googlecharts infographics api in April 2015 when they may or may
# not change the qrcode api
def get_qr_codes_response(hunt_id, item_id, condition):
    hunt = get_hunt(g.db, hunt_id)
    if hunt:
        item_paths = [
            {'name': item.name, 'path': item_path(hunt_id, item.item_id)}
            for item in hunt.items if condition(item, item_id)
        ]
        return make_response(render_template(
            'qrcodes.html', item_paths=item_paths))
    abort(404)


@app.route('/hunts/<hunt_id>/qrcodes')
@login_required
def show_item_codes(hunt_id):
    return get_qr_codes_response(hunt_id, '', lambda x, y: True)


@app.route('/hunts/<hunt_id>/items/<int:item_id>/qrcode', methods=['GET'])
@login_required
def show_item_code(hunt_id, item_id):
    return get_qr_codes_response(
        hunt_id, item_id, lambda item, item_id: item.item_id == item_id)


@app.route('/hunts/<int:hunt_id>/delete')
@login_required
def delete_hunt(hunt_id):
    hunt = get_hunt(g.db, hunt_id)
    if hunt and hunt.admin_id == current_user.admin_id:
        logger.info(
            'preparing to delete hunt with hunt_id, {}'.format(hunt_id))
        g.db.session.delete(hunt)
        g.db.session.commit()

        flash('Successfully deleted hunt: {}'.format(hunt.name), 'success')

        hunts = get_hunts(g.db, current_user.admin_id)
        return make_response(render_template('hunts.html', hunts=hunts))
    abort(404)

################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    hunt = get_hunt(g.db, hunt_id)
    if hunt:
        email = session.get('email')
        if email:
            logger.info(
                'preparing to render items from hunt_id, %s, for user, %s',
                hunt_id, email)
            items = get_items(g.db, hunt_id)
            params = xapi.default_params(
                email, hunt_id, request.host_url)
            admin_settings = get_settings(g.db, hunt_id=hunt_id)

            state = {}
            response = xapi.get_state_response(params, admin_settings)
            if response.status_code == 200:
                state = response.json()

            return make_response(render_template(
                'items.html', items=items, hunt_id=hunt_id,
                hunt_name=hunt.name, num_found=state.get('num_found', 0),
                found_ids=state.get('found_ids', []),
                total_items=state.get('total_items', 0)))

        session['intended_url'] = '/hunts/{}/items'.format(hunt_id)
        return make_response(
            render_template('welcome.html', hunt_name=hunt.name,
                            welcome=hunt.welcome_message,
                            action_url="/get_started/hunts/{}".format(
                                hunt_id)))

    abort(404)


# information about one item for scavenger to read
@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def find_item(hunt_id, item_id):
    admin_settings = get_settings(g.db, hunt_id=hunt_id)
    # admin_settings found through hunt_id means hunt exists
    if finished_setting(admin_settings):
        item = get_item(g.db, item_id, hunt_id)
        if item:
            email = session.get('email')
            hunt = get_hunt(g.db, hunt_id)
            if email and get_participant(g.db, email, hunt_id):
                params = xapi.default_params(email, hunt_id, request.host_url)
                name = session.get('name')

                state_response = xapi.get_state_response(
                    params, admin_settings)

                if state_response.status_code == 404:
                    items = get_items(db, hunt.hunt_id)
                    state = xapi.create_new_state(
                        email, hunt, item_id, params, admin_settings, items)
                    xapi.send_began_hunt_statement(
                        name, email, hunt, request.host_url, admin_settings)
                    xapi.send_found_item_statement(
                        name, email, hunt, item, request.host_url,
                        admin_settings)

                elif state_response.status_code == 200:
                    state = state_response.json()
                    if int(item.item_id) not in state['found_ids']:
                        xapi.send_found_item_statement(
                            name, email, hunt, item, request.host_url,
                            admin_settings)
                        state = xapi.update_state(
                            state, params, admin_settings, item, email, hunt)

                else:
                    # todo: get worker to retry
                    logger.warning(
                        "An unexpected error occurred retrieving information"
                        " from the state api using params, %s, with status,"
                        " %s, and response: \n%s", params,
                        state_response.status_code, state_response.text)
                    raise Exception(
                        'An unexpected error occurred with the scavenger hunt')

                required_found = set(state['found_ids']) == set(state['required_ids'])
                hunt_completed = state['num_found'] >= hunt.num_required and required_found

                if hunt_completed:
                    xapi.send_completed_hunt_statement(
                        name, email, hunt, item, request.host_url, admin_settings)
                    return make_response(
                        render_template('congratulations.html', hunt_name=hunt.name,
                                        congratulations=hunt.congratulations_message))
                return make_response(render_template(
                    'items.html', item=item, items=get_items(g.db, hunt_id),
                    username=name, hunt_name=hunt.name,
                    num_found=state['num_found'], found_ids=state['found_ids'],
                    total_items=state['total_items'], hunt_id=hunt_id))
            else:
                session['intended_url'] = '/hunts/{}/items/{}'.format(
                    hunt_id, item_id)
                return make_response(render_template(
                    'welcome.html', welcome=hunt.welcome_message,
                    hunt_name=hunt.name,
                    action_url="/get_started/hunts/{}".format(hunt_id)))
    abort(404)


# maybe just get rid of this
# form for scavenger hunt participant to enter email and name
@app.route('/get_started/hunts/<hunt_id>', methods=['GET'])
def get_started(hunt_id):
    # todo: track duration
    hunt = get_hunt(g.db, hunt_id)
    return render_template('get_started.html', form=ParticipantForm(),
                           hunt_id=hunt_id, hunt_name=hunt.name)


# validate and register participant before redirecting back to hunt
@app.route('/register_participant', methods=['POST'])
def register_participant():
    hunt_id = request.args['hunt_id']
    hunt = get_hunt(g.db, hunt_id)

    if hunt:
        form = ParticipantForm(request.form)
        if form.validate():
            email = form.email.data

            participant_valid, err_msg = validate_participant(
                g.db, email, hunt_id, hunt.participant_rule)
            if participant_valid:
                session.update({'email': email, 'name': form.name.data})

                participant = get_participant(g.db, email, hunt_id)
                if not participant:
                    participant = initialize_registered_participant(
                        form, Participant(), hunt_id)

                g.db.session.add(participant)
                g.db.session.commit()

                logger.info(
                    "name and email set to %s, and %s\n"
                    "preparing requested item information.",
                    session['name'], email)

                redirect_url = get_intended_url(session, hunt_id)
                return make_response(redirect(redirect_url))
            else:
                return err_msg
    else:
        # i don't think this can happen ever in the app
        logger.warning('A user attempted to register for hunt with id, %s,'
                       ' but the hunt could not be found. Form data: %s',
                       hunt_id, request.form)
        abort(400)


@app.route('/oops')
def oops():
    session.clear()
    return make_response(render_template('goodbye.html'))
