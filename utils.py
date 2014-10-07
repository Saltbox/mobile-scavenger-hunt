from flask import request, flash, redirect, url_for

from models import Hunt, Participant, Item, Admin, db, Setting
from hunt import bcrypt


def valid_login(admin, email, password):
    return admin and bcrypt.check_password_hash(
        admin.pw_hash, password)


def get_admin(db, email):
    return db.session.query(Admin).filter(Admin.email == email).first()


def get_settings(db, admin_id=None, hunt_id=None):
    if admin_id:
        return db.session.query(Setting).filter(
            Setting.admin_id == admin_id).first()
    elif hunt_id:
        return db.session.query(Setting).join(Admin).join(Hunt).first()
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


def get_hunt_domain(db, hunt_id):
    hunt = db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()
    if hunt:
        return hunt.domain
    return None


def get_intended_url(session, hunt_id):
    if 'intended_url' in session:
        return session.pop('intended_url')
    else:
        return '/hunts/{}/items'.format(hunt_id)


def ready_to_send_statements(db, settings):
    return settings.wax_site and settings.login and settings.password


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)


def validate_participant(db, email, hunt_id, participant_rule):
    if participant_rule == 'by_domain':
        domain = get_hunt_domain(db, hunt_id)
        return domain == email.split('@')[-1], \
            "Only employees of this organization may participate"
    elif participant_rule == 'by_whitelist':
        return get_participant(db, email, hunt_id) is not None, \
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
    hunt.admin_id = admin_id

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
