from flask import session, request, flash, redirect, url_for

from models import Hunt, Participant, Item, Admin, db, Setting
from forms import SettingForm
from hunt import bcrypt


# to do sha1
def get_admin(db, email, password):
    pw_hash = bcrypt.generate_password_hash(password)
    return db.session.query(Admin).filter(
        Admin.email == email, Admin.password == pw_hash
    ).first()


def get_admin_id_from_login(method, db, form):
    matched_admin = get_admin(
        db, form.username.data, form.password.data)
    if matched_admin:
        return matched_admin.admin_id
    raise Exception({'errors': {'email': 'Invalid email or password'}})


def get_settings(db, admin_id=None, hunt_id=None):
    if admin_id:
        return db.session.query(Setting).filter(
            Setting.admin_id == admin_id).first()
    elif hunt_id:
        return db.session.query(Setting).join(Admin).join(Hunt).first()
    return None


def update_settings(db, request, settings, form, admin_id):
    if request.method == 'POST':
        if form.validate():
            form.populate_obj(settings)
            settings.admin_id = admin_id
            return settings
        raise Exception({'errors': form.errors})
    return None


def get_hunts(db, admin_id):
    return db.session.query(Hunt).filter(Hunt.admin_id == admin_id).all()


def get_hunt(db, hunt_id):
    return db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()


def get_items(db, hunt_id):
    return db.session.query(Item).filter(Item.hunt_id == hunt_id).all()


def get_item(db, item_id):
    return db.session.query(Item).filter(Item.item_id == item_id).first()


def get_participant(db, email, hunt_id):
    return db.session.query(Participant).filter(
        Participant.email == email, Participant.hunt_id == hunt_id).first()


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)


def get_domain_by_admin_id(db, admin_id):
    admin = db.session.query(Setting).filter(
        Setting.admin_id == session['admin_id']).first()
    if admin:
        return admin.domain
    return None


def get_intended_url(session, hunt_id):
    if 'intended_url' in session:
        return session.pop('intended_url')
    else:
        return '/hunt/{}'.format(hunt_id)


def validate_participant(db, email, hunt_id):
    participant_rule = db.session.query(Hunt).filter(
        Hunt.hunt_id == hunt_id).first().participant_rule
    if participant_rule == 'by_domain':
        setting = get_settings(hunt_id=hunt_id)
        return setting and email.split('@')[-1] == setting.domain, \
            "Only employees of this organization may participate"
    elif participant_rule == 'by_whitelist':
        return get_participant(email, hunt_id), \
            "You are not on the list of allowed participants"
    # anyone can participate
    return True, ''


def mark_items_found(state, items):
    for item in items:
        if state.get('found_ids'):
            item.found = item.item_id in state['found_ids']
        else:
            item.found = None
    return items


def initialize_hunt(form, hunt, admin_id, request):
    def new_participant(email):
        p = Participant()
        p.email = email
        return p

    form.populate_obj(hunt)
    hunt.admin_id = session['admin_id']

    # even though this is structured the same way as items
    # (which works), this workaround is necessary to create
    # hunt participants
    hunt.participants = [
        new_participant(v) for k, v in request.form.items()
        if '-email' in k
    ]
    return hunt


def initialize_registered_participant(form, participant, hunt_id):
    form.populate_obj(participant)
    participant.registered = True
    participant.hunt_id = hunt_id
    return participant
