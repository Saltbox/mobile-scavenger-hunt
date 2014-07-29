from wtforms import Form, StringField, FieldList, validators, \
    FormField  # need validators?
from wtforms_alchemy import ModelFieldList, model_form_factory

ModelForm = model_form_factory(Form)

import models

from hunt import db


class LoginForm(Form):
    username = StringField('Username')


# update me now that there's an actual admin
class AdminLoginForm(LoginForm):
    password = StringField('Password')


class AdminForm(ModelForm):
    class Meta:
        model = models.Admin


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
