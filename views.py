from flask import session, abort, flash, url_for, make_response, request, \
    render_template, redirect, send_file, jsonify

import datetime
import uuid
import io
import json

import qrcode

from models import Hunt, Participant, Item, Admin, db, Setting
from forms import HuntForm, AdminForm, AdminLoginForm, ParticipantForm, \
    SettingForm, ItemForm
from hunt import app, logger
from utils import get_admin, get_setting, get_hunt, \
    get_item, listed_participant, login_required, item_path, \
    get_domain_by_admin_id, participant_email_exists, \
    validated_by_participant_rule
from sqlalchemy.exc import IntegrityError

import xapi


#################### ADMIN ROUTES ####################


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = AdminLoginForm(request.form)
    if request.method == 'POST' and form.validate():
        #  change later
        matched_admin = get_admin(form.username.data, form.password.data)
        if matched_admin:
            session['logged_in'] = True
            flash('You were logged in', 'info')
            session['admin_id'] = matched_admin.admin_id
            return redirect(url_for('hunts'))
        flash('Invalid email or password', 'warning')
    return render_template(
        'login.html', error=error, form=form, display_login_link=True)


@app.route('/logout')
def logout():
    for prop in ['admin_id', 'user_id', 'logged_in', 'name']:
        session.pop(prop, None)

    return redirect(url_for('login'))


@app.route('/')
def root():
    return login()


# create or list admins who can create hunts # probably rename to signup
@app.route('/admins', methods=['GET', 'POST'])
def admins():
    admin = Admin()
    form = AdminForm(request.form)
    if request.method == 'POST':
        if form.validate():
            form.populate_obj(admin)
            db.session.add(admin)
            db.session.commit()

            session['logged_in'] = True
            flash('Successfully created admin', 'success')

            domain = admin.email.split('@')[-1]
            session['admin_id'] = get_admin(
                form.email.data, form.password.data).admin_id
            return render_template('settings.html', domain=domain)
        logger.info('Admin signup form was submitted with invalid information')
        flash(
            'There was an error creating your admin profile.'
            ' Please try again.', 'warning')
    return render_template(
        'admin_signup.html', form=form, display_login_link=True)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        setting = get_setting(session['admin_id']) or Setting()
        form = SettingForm(request.form)
        if form.validate():
            setting.admin_id = request.form.get('admin_id') or session['admin_id']
            form.populate_obj(setting)

            db.session.add(setting)
            db.session.commit()
            flash('Settings have been updated', 'info')
        else:
            # get the errors from form. i think it's form.errors
            flash('Invalid setting information. '
                  'Please check your form entries and try again.')

    setting = get_setting(admin_id=session['admin_id'])

    # make it so these always exist
    if setting:
        login = getattr(setting, 'login')
        password = getattr(setting, 'password')
        wax_site = getattr(setting, 'wax_site')
        domain = getattr(setting, 'domain')
    else:
        login = password = wax_site = domain = ''

    return make_response(render_template(
        'settings.html', login=login, password=password,
        wax_site=wax_site, domain=domain))


# create or list hunts
@app.route('/hunts', methods=['GET'])
@login_required
def hunts():
    hunts = db.session.query(Hunt).filter(
        Hunt.admin_id == session['admin_id']).all()
    return render_template('hunts.html', hunts=hunts)


# form to create new hunt
@app.route('/new_hunt', methods=['GET', 'POST'])
def new_hunt():
    domain = get_domain_by_admin_id(session['admin_id'])
    hunt = Hunt()
    form = HuntForm(request.form)

    def newParticipant(email):
        p = Participant()
        p.email = email
        return p

    if request.method == 'POST':
        if form.validate():
            hunt.admin_id = session['admin_id']

            form.populate_obj(hunt)

            # even though this is structured the same way as items
            # (which works), this workaround is necessary to create
            # hunt participants
            hunt.participants = [
                newParticipant(request.form[prop]) for prop in request.form
                if '-email' in prop
            ]
            try:
                # todo: session manager
                db.session.add(hunt)
                db.session.commit()
            except IntegrityError as e:
                flash('Error creating form: hunt name, "{}", '
                      'already exists'.format(hunt.name), 'warning')
                logger.info(
                    'Exception found while creating hunt: %s\n'
                    'Form data: %s ', e, form.data)
                abort(400)

            flash('New scavenger hunt added', 'success')
            logger.info('hunt, %s, created for admin with id, %s',
                        hunt.name, hunt.admin_id)
            return redirect(url_for('hunts'))
        else:
            flash('Error creating form', 'warning')
            logger.warning('Error creating form.\nForm errors: %s\nForm data: '
                           '%s ', form.errors, form.data)
    return render_template('new_hunt.html', form=form, domain=domain)


# page to view hunt
@app.route('/hunts/<hunt_id>', methods=['GET'])
@login_required
def hunt(hunt_id):
    domain = get_domain_by_admin_id(session['admin_id'])
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        form = HuntForm(request.form)
        return render_template(
            'show_hunt.html', hunt=hunt, form=form, domain=domain)
    abort(404)


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
    abort(404)


@app.route('/hunts/<hunt_id>/items/<item_id>/qrcode', methods=['GET'])
def show_item_code(hunt_id, item_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        item_paths = [
            {'name': item.name, 'path': item_path(hunt_id, item.item_id)}
            for item in hunt.items if item.item_id == int(item_id)
        ]
        return make_response(render_template(
            'qrcodes.html', item_paths=item_paths))
    abort(404)


@app.route('/hunts/<hunt_id>/delete')
@login_required
def delete_hunt(hunt_id):
    logger.info(
        'preparing to delete hunt with hunt_id, {}'.format(hunt_id))
    hunt = get_hunt(int(hunt_id))
    if hunt:
        db.session.delete(hunt)
        db.session.commit()
        flash('Successfully deleted hunt', 'success')
        return make_response(render_template('hunts.html'))
    abort(404)

################ SCAVENGER HUNT PARTICIPANT ROUTES ####################


# list of items for scavengers to scavenge
@app.route('/hunts/<hunt_id>/items', methods=['GET'])
def index_items(hunt_id):
    logger.info(
        'preparing to render items for hunt_id, {}'.format(hunt_id))

    hunt = get_hunt(hunt_id)
    if hunt:
        if session.get('email'):
            items = db.session.query(Item).filter(
                Item.hunt_id == hunt_id).all()
            params = xapi.default_params(session['email'], hunt_id)
            setting = get_setting(hunt_id=hunt_id)
            response = xapi.get_state_response(params, setting)
            if response.status_code == 200:
                state = response.json()
                for item in items:
                    if state.get('found'):
                        item.found = item.item_id in state['found']
                    else:
                        item.found = None

            return render_template(
                'items.html', items=items, hunt_id=hunt_id, hunt_name=hunt.name)
        session['intended_url'] = '/hunts/{}/items'.format(hunt_id)
        return get_started(hunt_id)

    abort(404)


# information about one item for scavenger to read
@app.route('/hunts/<hunt_id>/items/<item_id>', methods=['GET'])
def show_item(hunt_id, item_id):
    def update_state(state, params, setting):
        if item_id not in state['found']:
            state['found'].append(int(item_id))
            console.log('found: %s', state['found'])
            state['num_found'] += 1
            if item_id in state['required_ids']:
                state['required_ids'].remove(item_id)
        return state

    # right now ids are unique across item table.
    item = db.session.query(Item)\
        .filter(Hunt.hunt_id == hunt_id) \
        .filter(Item.item_id == item_id).first()

    if item:
        email = session.get('email')
        if email and listed_participant(email, hunt_id):
            params = xapi.default_params(email, hunt_id)
            actor = xapi.make_agent(email)
            hunt = get_hunt(hunt_id)

            # hm. remember to make sure settings have been set.
            setting = get_setting(hunt_id=hunt_id)
            response = xapi.get_state_response(params, setting)
            status_code = response.status_code
            if status_code == 404:
                items = db.session.query(Item).filter(
                    Item.hunt_id == hunt_id).all()
                required_ids = [
                    item.item_id for item in items if item.required]

                state = {
                    'found': [int(item_id)],
                    'num_found': 0,
                    'required_ids': required_ids,
                    'total_items': len(items)
                }
                # xapi.put_state(json.dumps(state), params, setting)

                # xapi.send_statement(
                    # xapi.begin_hunt_statement(actor, hunt), setting)
            elif status_code == 200:
                state = update_state(response.json(), params, setting)
                # xapi.post_state(state, params, setting)
            else:
                logger.debug("why would this ever happen?")
                pass
                # ???

            # xapi.send_statements(actor, hunt, item, state, setting, params)
            return make_response(render_template(
                'item.html', item=item, username=session['name'],
                num_found=state['num_found'],
                total_items=state['total_items'], hunt_id=hunt_id))
        else:
            session['intended_url'] = '/hunts/{}/items/{}'.format(hunt_id, item_id)
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
    form = ParticipantForm(request.form)
    if form.validate():
        hunt_id = request.args['hunt_id']
        email = form.email.data

        validated_participant, err_msg = validated_by_participant_rule(
            email, hunt_id, form)
        if validated_participant:
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
            session['email'] = email
            validated_participant.name = session['name'] = form.name.data

            db.session.add(validated_participant)
            db.session.commit()

            logger.info(
                "user id, name, and email set to %s, %s, and %s\n"
                "preparing requested item information.",
                user_id, session['name'], email)
            if 'intended_url' in session:
                redirect_url = session['intended_url']
            else:
                redirect_url = '/hunt/{}'.format(hunt_id)
            return make_response(redirect(redirect_url))
        else:
            return err_msg
    abort(400)
