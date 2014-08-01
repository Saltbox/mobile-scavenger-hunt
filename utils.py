from flask import session, request, flash, redirect, url_for
from functools import wraps

from models import Hunt, Participant, Item, Admin, db, Setting

import qrcode


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


def create_qrcode_binary(qrcode):
    output = io.BytesIO()
    qrcode.save(output, 'PNG')
    return output.getvalue()


def get_setting(admin_id=None, hunt_id=None):
    if admin_id:
        return db.session.query(Setting).filter(
            Setting.admin_id == admin_id).first()
    elif hunt_id:
        return db.session.query(Setting).join(Admin).join(Hunt).first()


def get_hunt(hunt_id):
    return db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()


def get_item(item_id):
    return db.session.query(Item).filter(Item.item_id == item_id).first()


def listed_participant(email, hunt_id):
    return db.session.query(Participant).filter(
        Participant.hunt_id == hunt_id, Participant.email == email).first()


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)


def get_domain_by_admin_id(admin_id):
    admin = db.session.query(Setting).filter(
        Setting.admin_id == session['admin_id']).first()
    if admin:
        return admin.domain
    return None


def participant_email_exists(email, hunt_id):
    return db.session.query.filter(
        Participant.email == email).filter(Hunt.hunt_id == hunt_id).first()


def validated_by_participant_rule(email, hunt_id):
    participant_rule = db.session.query(Hunt).filter(
        Hunt.hunt_id == hunt_id).first().participant_rule
    if participant_rule == 'by_domain':
        setting = get_setting(hunt_id=hunt_id)
        if setting and email.split('@')[-1] != setting.domain:
            return None, "Only employees of this organization may participate"
    elif participant_rule == 'by_whitelist':
        return listed_participant(email, hunt_id), \
            "You are not on the list of allowed participants"

    participant = Participant()
    participant.email = email
    participant.hunt_id = hunt_id
    participant.registered = True
    return participant, ""