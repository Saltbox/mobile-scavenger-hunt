from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect, g
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
    get_participant, item_path, get_domain_by_admin_id, \
    validate_participant, get_intended_url, get_hunts, get_items, \
    initialize_hunt, initialize_registered_participant, mark_items_found, \
    valid_login, ready_to_send_statements

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
            flash('You were logged in', 'info')
            return redirect(url_for('hunts'))
        flash('Invalid email and password combination')
    else:
        errors = form.errors
    return make_response(render_template(
        'login.html', errors=errors, form=form, display_login_link=True))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
def root():
    return login()


# create or list admins who can create hunts
@app.route('/admins', methods=['GET', 'POST'])
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

            domain = admin.email.split('@')[-1]

            flash('Successfully created admin', 'success')
            logger.info(
                'Admin registration form was submitted successfully')
            return make_response(
                render_template('settings.html', domain=domain))

        logger.info(
            'Admin registration form was submitted with'
            ' invalid information: %s', request.form)
        flash(
            'There was an error creating your admin profile.'
            ' Please try again.', 'warning')
    return render_template(
        'admin_registration.html', form=form, display_login_link=True)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    errors = None
    admin_settings = get_settings(
        g.db, admin_id=current_user.admin_id) or Setting()
    form = SettingForm(request.form)
    if request.method == 'POST':
        if form.validate():
            form.populate_obj(admin_settings)
            admin_settings.admin_id = current_user.admin_id
            g.db.session.add(admin_settings)
            g.db.session.commit()
        else:
            errors = form.errors
    return make_response(render_template(
        'settings.html', login=admin_settings.login,
        password=admin_settings.password, domain=admin_settings.domain,
        wax_site=admin_settings.wax_site, errors=errors
    ))


# create or list hunts
@app.route('/hunts', methods=['GET'])
@login_required
def hunts():
    hunts = get_hunts(g.db, current_user.admin_id)
    return render_template('hunts.html', hunts=hunts)


# form to create new hunt
@app.route('/new_hunt', methods=['GET', 'POST'])
@login_required
def new_hunt():
    domain = get_domain_by_admin_id(g.db, current_user.admin_id)
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
                    'Exception found while creating hunt with an existing name: %s\n'
                    'Form data: %s ', e, form.data)
                # can you flash on a 400 page?
                abort(400)

            flash('New scavenger hunt added', 'success')
            logger.info('hunt, %s, created for admin with id, %s',
                        hunt.name, hunt.admin_id)
            return redirect(url_for('hunts'))
        else:
            flash('Error creating form', 'warning')
            logger.warning('Error creating form.\nForm errors: %s\nForm data: '
                           '%s ', form.errors, form.data)
    return make_response(
        render_template('new_hunt.html', form=form, domain=domain))


# page to view hunt
@app.route('/hunts/<hunt_id>', methods=['GET'])
@login_required
def hunt(hunt_id):
    domain = get_domain_by_admin_id(g.db, current_user.admin_id)
    hunt = get_hunt(g.db, hunt_id)
    if hunt:
        form = HuntForm(request.form)
        return render_template(
            'show_hunt.html', hunt=hunt, form=form, domain=domain)
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
        flash('Successfully deleted hunt', 'success')
        return make_response(render_template('hunts.html'))
    abort(404)

################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    logger.info(
        'preparing to render items for hunt_id, {}'.format(hunt_id))

    hunt = get_hunt(g.db, hunt_id)
    if hunt:
        if session.get('email'):
            items = get_items(g.db, hunt_id)
            params = xapi.default_params(session['email'], hunt_id)
            admin_settings = get_settings(hunt_id=hunt_id)

            response = xapi.get_state_response(params, admin_settings)
            if response.status_code == 200:
                state = response.json()
                items = mark_items_found(state, items)

            return render_template(
                'items.html', items=items, hunt_id=hunt_id,
                hunt_name=hunt.name)

        session['intended_url'] = '/hunts/{}/items'.format(hunt_id)
        return make_response(
            render_template('welcome.html',
                            action_url="/get_started/hunts/{}".format(
                                hunt_id)))

    abort(404)


# information about one item for scavenger to read
@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    item = get_item(g.db, item_id)
    admin_settings = get_settings(hunt_id=hunt_id)

    if item and ready_to_send_statements(g.db, hunt_id=hunt_id):
        email = session.get('email')
        if email and get_participant(g.db, email, hunt_id):
            params = xapi.default_params(email, hunt_id)
            hunt = get_hunt(g.db, hunt_id)

            state_response = xapi.get_state_response(params, admin_settings)
            state_report, updated_state = xapi.update_state(
                state_response, email, hunt, item, params, g.db)
            xapi.send_statements(
                updated_state, state_report, admin_settings, email, hunt, item=item)

            if state_report.get('hunt_completed'):
                return make_response(render_template('congratulations.html'))
            return make_response(render_template(
                'item.html', item=item, username=session['name'],
                num_found=updated_state['num_found'],
                total_items=updated_state['total_items'], hunt_id=hunt_id))
        else:
            session['intended_url'] = '/hunts/{}/items/{}'.format(
                hunt_id, item_id)
            return make_response(render_template(
                'welcome.html',
                action_url="/get_started/hunts/{}".format(hunt_id)))
    abort(404)


# maybe just get rid of this
# form for scavenger hunt participant to enter email and name
@app.route('/get_started/hunts/<hunt_id>', methods=['GET'])
def get_started(hunt_id):
    # todo: track duration
    return render_template('get_started.html', form=ParticipantForm(),
                           hunt_id=hunt_id)


# validate and register participant before redirecting back to hunt
@app.route('/register_participant', methods=['POST'])
def register_participant():
    hunt_id = request.args['hunt_id']
    hunt = get_hunt(db, hunt_id)

    # i don't think this can happen ever in the app
    if not hunt:
        abort(404)

    form = ParticipantForm(request.form)
    if form.validate():
        email = form.email.data

        participant_valid, err_msg = validate_participant(
            g.db, email, hunt_id, hunt.participant_rule)
        if participant_valid:
            user_id = str(uuid.uuid4())
            session.update({
                'user_id': user_id,
                'email': email,
                'name': form.name.data
            })

            participant = initialize_registered_participant(
                form, Participant(), hunt_id)

            g.db.session.add(participant)
            g.db.session.commit()

            logger.info(
                "user id, name, and email set to %s, %s, and %s\n"
                "preparing requested item information.",
                user_id, session['name'], email)

            redirect_url = get_intended_url(session, hunt_id)
            return make_response(redirect(redirect_url))
        else:
            return err_msg
    abort(400)


@app.route('/oops')
def oops():
    session.clear()
    return make_response(render_template('goodbye.html'))
