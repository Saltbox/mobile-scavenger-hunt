import os

from hunt import db

hunt_participants = db.Table(
    'hunt_participants',
    db.Column('hunt_hunt_id', db.Integer, db.ForeignKey('participants.participant_id')),
    db.Column('participant_participant_id', db.Integer, db.ForeignKey('hunts.hunt_id'))
)


class Admin(db.Model):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(320), unique=True)
    password = db.Column(db.String(50))
    hunts = db.relationship('Hunt', backref='hunts')


class Hunt(db.Model):
    __tablename__ = 'hunts'
    hunt_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    participants = db.relationship('Participant', secondary=hunt_participants)
    items = db.relationship('Item', backref='hunts')
    # do i care about timezone aware?
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    last_modified = db.Column(db.TIMESTAMP, server_default=db.func.now(),
                              onupdate=db.func.current_time())
    # refers to items required
    all_required = db.Column(db.Boolean)
    num_required = db.Column(db.Integer)

    owner = db.Column(db.Integer, db.ForeignKey('admins.admin_id'))

    def __repr__(self):
        return '<Hunt %r>' % self.name


class Participant(db.Model):
    __tablename__ = 'participants'
    participant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50))
    # hunt_id = db.Column(db.Integer, db.ForeignKey('hunts.hunt_id'))
    hunts = db.relationship('Hunt', secondary=hunt_participants)

    def __repr__(self):
        return '<Participant %r>' % self.email


class Item(db.Model):
    __tablename__ = 'items'
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    hunt_id = db.Column(db.Integer, db.ForeignKey('hunts.hunt_id'))
    required = db.Column(db.Boolean)

    def __repr__(self):
        return '<Item %r>' % self.name
