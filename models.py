import os

from hunt import db


class Hunt(db.Model):
    __tablename__ = 'hunt'
    hunt_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    participants = db.relationship('Participant', backref='hunt')
    items = db.relationship('Item', backref='hunt')
    date_created = db.Column(db.DateTime)
    last_modified = db.Column(db.DateTime)
    # refers to items required
    all_required = db.Column(db.Boolean)
    num_required = db.Column(db.Integer)

    def __init__(self, name, participants=[], items=[]):
        self.name = name
        self.participants = participants
        self.items = items

    def __repr__(self):
        return '<Hunt %r>' % self.name


class Participant(db.Model):
    __tablename__ = 'participants'
    participant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50))
    hunt_id = db.Column(db.Integer, db.ForeignKey('hunt.hunt_id'))

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<Participant %r>' % self.email


class Item(db.Model):
    __tablename__ = 'items'
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    hunt_id = db.Column(db.Integer, db.ForeignKey('hunt.hunt_id'))
    required = db.Column(db.Boolean)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Item %r>' % self.name
