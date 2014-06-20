from wtforms import Form, StringField, FieldList, validators, \
    FormField  # need validators?
from wtforms_alchemy import ModelFieldList, model_form_factory

ModelForm = model_form_factory(Form)

import models

from hunt import db


class LoginForm(Form):
    username = StringField('Username')


class AdminLoginForm(LoginForm):
    password = StringField('Password')


class ItemForm(ModelForm):
    class Meta:
        model = models.Item


class ParticipantLoginForm(ModelForm):
    class Meta:
        model = models.Participant
        exclude = ['name']


class HuntForm(ModelForm):
    class Meta:
        model = models.Hunt

    participants = ModelFieldList(
        FormField(ParticipantLoginForm), min_entries=1)
    items = ModelFieldList(FormField(ItemForm), min_entries=1)
