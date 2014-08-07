from flask import session, request, flash, redirect, url_for
from functools import wraps

from models import Hunt, Participant, Item, Admin, db, Setting


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


def get_settings(admin_id=None, hunt_id=None):
    if admin_id:
        return db.session.query(Setting).filter(
            Setting.admin_id == admin_id).first()
    elif hunt_id:
        return db.session.query(Setting).join(Admin).join(Hunt).first()
    return None


def get_hunt(hunt_id):
    return db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()


def get_item(item_id):
    return db.session.query(Item).filter(Item.item_id == item_id).first()


def get_participant(email, hunt_id):
    return db.session.query(Participant).filter(
        Participant.email == email, Participant.hunt_id == hunt_id).first()


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)


def get_domain_by_admin_id(admin_id):
    admin = db.session.query(Setting).filter(
        Setting.admin_id == session['admin_id']).first()
    if admin:
        return admin.domain
    return None


def validate_participant(email, hunt_id):
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
