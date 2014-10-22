import os
from hunt import db
import sys

from flask.ext.login import UserMixin


class Admin(db.Model):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True)
    pw_hash = db.Column(db.String(64))
    hunts = db.relationship('Hunt', backref='hunts')

    def __repr__(self):
        return '<Admin %r>' % self.email

    # http://flask-login.readthedocs.org/en/latest/_modules/flask/ext/login.html#UserMixin
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.admin_id)
        except AttributeError:
            raise NotImplementedError('No `id` attribute - override `get_id`')

    def __eq__(self, other):
        '''
        Checks the equality of two `UserMixin` objects using `get_id`.
        '''
        if isinstance(other, UserMixin):
            return self.get_id() == other.get_id()
        return NotImplemented

    def __ne__(self, other):
        '''
        Checks the inequality of two `UserMixin` objects using `get_id`.
        '''
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    if sys.version_info[0] != 2:  # pragma: no cover
        # Python 3 implicitly set __hash__ to None if we override __eq__
        # We set it back to its default implementation
        __hash__ = object.__hash__


class Hunt(db.Model):
    __tablename__ = 'hunts'
    hunt_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    participants = db.relationship(
        'Participant', backref='hunts', cascade='all')
    participant_rule = db.Column(db.String(20))
    items = db.relationship('Item', backref='hunts', cascade='all')

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    last_modified = db.Column(db.DateTime(timezone=True), server_default=db.func.now(),
                              onupdate=db.func.now())
    # refers to items required
    all_required = db.Column(db.Boolean)
    num_required = db.Column(db.Integer)

    welcome_message = db.Column(db.String(500))
    congratulations_message = db.Column(db.String(500))
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.admin_id'))
    domain = db.Column(db.String(50))

    def __repr__(self):
        return '<Hunt %r>' % self.name

    @classmethod
    def list_for_admin_id(cls, db, admin_id):
        return db.session.query(Hunt).filter(Hunt.admin_id == admin_id).all()

    @classmethod
    def find_by_id(cls, db, hunt_id):
        return db.session.query(Hunt).filter(Hunt.hunt_id == hunt_id).first()


class Participant(db.Model):
    __tablename__ = 'participants'
    participant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50), nullable=False)
    hunt_id = db.Column(db.Integer, db.ForeignKey('hunts.hunt_id'))
    registered = db.Column(db.Boolean)

    def __repr__(self):
        return '<Participant %r>' % self.email


class Item(db.Model):
    __tablename__ = 'items'
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    hunt_id = db.Column(db.Integer, db.ForeignKey('hunts.hunt_id'))
    required = db.Column(db.Boolean)

    def __repr__(self):
        return '<Item %r %r>' % (self.item_id, self.name)


class Setting(db.Model):
    __tablename__ = 'settings'
    settings_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.admin_id'))
    wax_site = db.Column(db.String(500), nullable=False)
    login = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<Settings for admin id: %r>' % self.admin_id
