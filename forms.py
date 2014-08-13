from wtforms import Form, StringField, FieldList, validators, \
    FormField
from wtforms_alchemy import ModelFieldList, model_form_factory

ModelForm = model_form_factory(Form)

import models

from hunt import db


class LoginForm(Form):
    email = StringField('Email')


class AdminLoginForm(LoginForm):
    password = StringField('Password')


class AdminForm(ModelForm):
    class Meta:
        model = models.Admin
    password = StringField('Password')


class ItemForm(ModelForm):
    class Meta:
        model = models.Item


class ParticipantForm(ModelForm):
    class Meta:
        model = models.Participant


class HuntForm(ModelForm):
    class Meta:
        model = models.Hunt

    name = StringField('Name', [validators.Length(min=4)])
    items = ModelFieldList(FormField(ItemForm), min_entries=1)


class SettingForm(ModelForm):
    class Meta:
        model = models.Setting
