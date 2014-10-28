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

from hunt import app, logger, login_manager, db, bcrypt
from utils import get_admin, get_settings, get_item, \
    get_participant, item_path, validate_participant, get_intended_url, \
    get_items, initialize_hunt, create_new_participant, \
    valid_login, finished_setting, participant_registered,\
    num_items_remaining, hunt_requirements_completed, found_ids_list

from xapi import WaxCommunicator


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
    if request.method == 'POST':
        form = AdminForm(request.form)
        if form.validate():
            admin = Admin()
            form.populate_obj(admin)
            admin.pw_hash = bcrypt.generate_password_hash(form.password.data)

            g.db.session.add(admin)
            g.db.session.commit()

            login_user(get_admin(g.db, admin.email))

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
            already_completed = finished_setting(admin_settings)
            form.populate_obj(admin_settings)
            admin_settings.admin_id = current_user.admin_id

            g.db.session.add(admin_settings)
            g.db.session.commit()

            url = 'hunts' if already_completed else 'new_hunt'
            flash('Settings have been updated successfully', 'success')
            return make_response(redirect(url_for(url)))
        else:
            logger.info(
                '%s attempted to submit settings information'
                ' resulting in errors: %s', current_user.email, form.errors)
    return make_response(render_template(
        'settings.html', login=admin_settings.login, form=form,
        password=admin_settings.password, wax_site=admin_settings.wax_site
    ))


# list hunts
@app.route('/hunts', methods=['GET'])
@login_required
def hunts():
    hunts = Hunt.list_for_admin_id(g.db, current_user.admin_id)
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
                logger.warning(
                    'Exception found while creating hunt with an existing '
                    ' name: %s\n Form data: %s ', e, form.data)
                return jsonify(
                    {'hunt name': [{'name': ['hunt name already taken']}]}), 400
            else:
                flash('New scavenger hunt added', 'success')
                logger.info('hunt, %s, created for admin with id, %s',
                            hunt.name, hunt.admin_id)

                saved_hunt = g.db.session.query(Hunt).order_by(
                    Hunt.hunt_id.desc()).first()
                return jsonify({'hunt_id': saved_hunt.hunt_id})
        else:
            logger.warning('Error creating hunt.\nForm errors: %s\nForm data: '
                           '%s ', form.errors, form.data)
            return jsonify(form.errors), 400
    domain = current_user.email.split('@')[-1]
    return make_response(
        render_template('new_hunt.html', form=form, domain=domain))


# page to view hunt
@app.route('/hunts/<int:hunt_id>', methods=['GET'])
@login_required
def hunt(hunt_id):
    hunt = Hunt.find_by_id(g.db, hunt_id)
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
    logger.info('Someone attempted to visit a hunt with id, %s, but it '
                'does not exist', hunt_id)
    abort(404)


# check googlecharts infographics api in April 2015 when they may or may
# not change the qrcode api
def get_qr_codes_response(hunt_id, item_id, condition):
    hunt = Hunt.find_by_id(g.db, hunt_id)
    if hunt:
        item_paths = [
            {'name': item.name, 'path': item_path(hunt_id, item.item_id)}
            for item in hunt.items if condition(item, item_id)
        ]
        return make_response(render_template(
            'qrcodes.html', item_paths=item_paths))
    abort(404)


@app.route('/hunts/<int:hunt_id>/qrcodes')
@login_required
def show_item_codes(hunt_id):
    return get_qr_codes_response(hunt_id, '', lambda x, y: True)


@app.route('/hunts/<int:hunt_id>/items/<int:item_id>/qrcode', methods=['GET'])
@login_required
def show_item_code(hunt_id, item_id):
    return get_qr_codes_response(
        hunt_id, item_id, lambda item, item_id: item.item_id == item_id)


@app.route('/hunts/<int:hunt_id>/delete')
@login_required
def delete_hunt(hunt_id):
    hunt = Hunt.find_by_id(g.db, hunt_id)
    if hunt and hunt.admin_id == current_user.admin_id:
        logger.info(
            'preparing to delete hunt with hunt_id, {}'.format(hunt_id))
        g.db.session.delete(hunt)
        g.db.session.commit()

        flash('Successfully deleted hunt: {}'.format(hunt.name), 'success')

        hunts = Hunt.list_for_admin_id(g.db, current_user.admin_id)
        return make_response(render_template('hunts.html', hunts=hunts))
    abort(404)

################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# maybe just get rid of this
# form for scavenger hunt participant to enter email and name
@app.route('/get_started/hunts/<int:hunt_id>', methods=['GET'])
def get_started(hunt_id):
    # todo: track duration
    hunt = Hunt.find_by_id(g.db, hunt_id)
    logger.info("Rendering getting started form for hunt, '%s'.", hunt.name)
    return render_template('get_started.html', form=ParticipantForm(),
                           hunt_id=hunt_id, hunt=hunt)


# validate and register participant before redirecting back to hunt
@app.route('/register_participant', methods=['POST'])
def register_participant():
    hunt_id = request.args['hunt_id']
    hunt = Hunt.find_by_id(g.db, hunt_id)

    if hunt:
        form = ParticipantForm(request.form)
        if form.validate():
            email = form.email.data

            logger.info(
                'Participant registration form validated for hunt, "%s", and'
                ' email, %s.\nPreparing to validate participant against hunt'
                ' participation rules.', hunt.name, email)
            participant_valid, err_msg = validate_participant(
                g.db, email, hunt_id, hunt.participant_rule)
            if participant_valid:
                logger.info('The registering participant, %s, has been'
                            ' validated against the hunt participation rules.'
                            ' Preparing to find email in participant database'
                            ' table.', email)
                if not get_participant(g.db, email, hunt_id):
                    logger.info(
                        'Preparing to save new participant with email, %s,'
                        ' to hunt, %s', email, hunt.name)
                    create_new_participant(g.db, form, hunt_id)

                scavenger_info = {'email': email, 'name': form.name.data}
                session.update(scavenger_info)

                admin_settings = get_settings(g.db, hunt_id=hunt_id)
                logger.info(
                    "Retrieved settings associated with hunt with id, %s: %s",
                    hunt_id, admin_settings)

                try:
                    lrs = WaxCommunicator(
                        admin_settings, request.host_url, hunt, None,
                        scavenger_info=scavenger_info)
                except Exception as e:
                    logger.exception(
                        "Error instantiating WaxCommunicator while registering"
                        " participant: %s", e)
                    raise e

                try:
                    lrs.send_began_hunt_statement()
                except Exception as e:
                    logger.exception(
                        "Error sending began hunt statement: %s", e)
                    raise e

                logger.info(
                    "name and email set to %s, and %s\n"
                    "preparing requested item information.",
                    session['name'], email)
                redirect_url = get_intended_url(session, hunt_id)
                return make_response(redirect(redirect_url))
            else:
                logger.info('participant attempted to register for'
                            ' hunt with invalid form information.\n'
                            'Error message: %s\n.  Form data: %s',
                            err_msg, request.form)
                return err_msg
    else:
        # i don't think this can happen ever in the app
        logger.warning('A user attempted to register for hunt with id, %s,'
                       ' but the hunt could not be found. Form data: %s',
                       hunt_id, request.form)
        abort(400)


# list of items for scavengers to scavenge
@app.route('/hunts/<int:hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    hunt = Hunt.find_by_id(g.db, hunt_id)
    if hunt:
        email = session.get('email')
        if email:
            admin_settings = get_settings(g.db, hunt_id=hunt_id)
            lrs = WaxCommunicator(
                admin_settings, request.host_url, hunt, None,
                {'email': email, 'name': session.get('name')})

            state = lrs.get_state()

            logger.info(
                'preparing to render items from hunt_id, %s, for user, %s',
                hunt_id, email)

            return make_response(render_template(
                'items.html', state=state, hunt=hunt,
                num_remaining=num_items_remaining(state, hunt.items)))

        session['intended_url'] = '/hunts/{}/items'.format(hunt_id)
        return make_response(
            render_template('welcome.html', hunt=hunt,
                            welcome=hunt.welcome_message,
                            action_url="/get_started/hunts/{}".format(
                                hunt_id)))
    logger.info('Someone attempted to visit the items list for hunt with id, '
                '%s, but this hunt does not exist', hunt_id)
    abort(404)


# information about one item for scavenger to read
@app.route('/hunts/<int:hunt_id>/items/<int:item_id>', methods=['GET'])
def find_item(hunt_id, item_id):
    logger.info(
        'Participant is visiting route: /hunts/%s/items/%s', hunt_id, item_id)

    admin_settings = get_settings(g.db, hunt_id=hunt_id)
    # admin_settings found through hunt_id means hunt exists
    logger.info("Settings retrieved for hunt with id, %s", hunt_id)

    if finished_setting(admin_settings):
        logger.info(
            "Settings are complete. Preparing to retrieve item with id, %s",
            item_id)
        item = get_item(g.db, item_id, hunt_id)
        if item:
            logger.info(
                "Item found. Preparing to retrieve hunt with id, %s ", hunt_id)
            hunt = Hunt.find_by_id(g.db, hunt_id)
            if participant_registered(g.db, session.get('email'), hunt_id):
                logger.info(
                    "Participant, %s, has registered. Preparing to"
                    " retrieve data from the state api.", session.get('email'))
                lrs = WaxCommunicator(
                    admin_settings, request.host_url, hunt, item,
                    scavenger_info={
                        'email': session.get('email'),
                        'name': session.get('name')
                    })

                state = lrs.get_state()

                found_again = str(item_id) in state
                lrs.send_found_item_statement(found_again=found_again)
                updated_state = {str(item.item_id): True}

                hunt_previously_completed = state.get('hunt_completed')
                state.update(updated_state)
                if hunt_requirements_completed(state, hunt):
                    logger.info(
                        'Requirements for hunt, "%s", have been completed.',
                        hunt.name)
                    if not hunt_previously_completed:
                        lrs.send_completed_hunt_statement()
                        updated_state['hunt_completed'] = True
                        state.update(updated_state)

                lrs.update_state_api_doc(updated_state)

                found_ids = found_ids_list(state)
                return make_response(render_template(
                    'items.html', item=item, hunt=hunt,
                    username=session.get('name'), found_ids=found_ids,
                    hunt_now_completed=state.get('hunt_completed'),
                    num_found=len(found_ids), num_items=len(hunt.items),
                    num_remaining=num_items_remaining(state, hunt.items),
                    found_again=found_again,
                    previously_completed=hunt_previously_completed))
            else:
                logger.info(
                    "Page visitor is not yet registered for this hunt."
                    " Preparing to redirect to the getting started page.")
                session['intended_url'] = '/hunts/{}/items/{}'.format(
                    hunt_id, item_id)
                return make_response(render_template(
                    'welcome.html', hunt=hunt, welcome=hunt.welcome_message,
                    action_url="/get_started/hunts/{}".format(hunt_id)))
    abort(404)


@app.route('/oops')
def oops():
    session.clear()
    return make_response(render_template('goodbye.html'))


@app.route('/failblog')
def failblog():
    try:
        return doesnotexistsowillerror
    except Exception as e:
        logger.exception("Error for the failblog: %s", e)
        raise e
