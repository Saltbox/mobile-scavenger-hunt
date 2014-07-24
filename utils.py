from flask import session, request
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


# later prevent resending statements if they for whatever reason scan the qrcode
# multiple times
def send_statements(email, hunt, item, state, setting):
    actor = xapi.make_agent(email)
    params = xapi.default_params(session['email'], hunt.hunt_id)

    xapi.send_statement(
        xapi.found_item_statement(actor, hunt, item), setting)

    if state['num_found'] == hunt.num_required and not state['required_ids']:
        xapi.send_statement(
            xapi.found_all_required_statement(actor, hunt), setting)

    if state['num_found'] == state['total_items']:
        xapi.send_statement(
            xapi.completed_hunt_statement(actor, hunt), setting)
        return make_response(render_template('congratulations.html'))


def item_path(hunt_id, item_id):
    return "{}hunts/{}/items/{}".format(request.host_url, hunt_id, item_id)