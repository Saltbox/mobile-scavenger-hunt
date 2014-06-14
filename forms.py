from wtforms import Form, BooleanField, StringField, FieldList, validators


class LoginForm(Form):
    username = StringField('Username')


class AdminLoginForm(LoginForm):
    password = StringField('Password')


class ParticipantLoginForm(LoginForm):
    email = StringField('Email', [validators.Email()])


class HuntForm(Form):
    name = StringField('Hunt Name', [validators.required()])
    participants = FieldList(
        StringField('Participant Emails', [validators.Email()]), min_entries=1)
    items = FieldList(StringField('Items', []), min_entries=1)
    all_required = BooleanField('All Items Required', [])
