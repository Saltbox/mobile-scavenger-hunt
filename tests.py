import unittest
import uuid
import json

from werkzeug.datastructures import ImmutableMultiDict
from flask import session
from hunt import db, app

import xapi


app.config['DEBUG'] = True
BASIC_LOGIN = app.config['WAX_LOGIN']
BASIC_PASSWORD = app.config['WAX_PASSWORD']
WAX_SITE = app.config['WAX_SITE']


def identifier():
    return uuid.uuid4().hex


def email():
    return '{}@example.com'.format(identifier())


# now that i have to make a setting anyway, maybe replace this
class MockSetting:
    def __init__(self, login, password, wax_site):
        self.login = login
        self.password = password
        self.wax_site = wax_site


class MockHunt:
    def __init__(self, hunt_id, name):
        self.hunt_id = hunt_id
        self.name = name


class HuntTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        db.create_all()
        email = 'dp@example.com'  # email()
        password = 'password'   # identifier()
        self.create_admin(email=email, password=password)
        self.admin = {'email': email, 'password': password}
        self.create_settings()
        print self.admin
        self.logout()

    def tearDown(self):
        self.logout()
        db.session.remove()
        db.drop_all()
        db.create_all()  # for interface

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username, password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def create_admin(
            self, first_name=identifier(), last_name=identifier(),
            email=email(), password=identifier()):
        return self.app.post('/admins', data=dict(
            first_name=first_name, last_name=last_name, email=email,
            password=password
        ))

    def create_settings(self, wax_site=WAX_SITE, admin_id=1,
                        domain='example.com', login=BASIC_LOGIN,
                        password=BASIC_PASSWORD):
        return self.app.post('/settings', data=dict(
            wax_site=wax_site, admin_id=admin_id, domain=domain,
            login=login, password=password
        ), follow_redirects=True)

    def create_hunt(self,
                    name=identifier(),
                    participant_rule='by_whitelist',
                    participants=[{'email': email()}],
                    items=[{'name': identifier()}], all_required=True):

        # this is how wtforms-alchemy expects data
        participant_emails = []
        for (index, participant) in enumerate(participants):
            participant_emails.append(
                ('participants-{}-email'.format(index), participant['email']))

        item_names = []
        for (index, item) in enumerate(items):
            item_names.append(
                ('items-{}-name'.format(index), item['name']))

        forminfo = participant_emails + item_names + \
            [('all_required', True), ('name', name),
             ('participant_rule', participant_rule)]
        self.imdict = ImmutableMultiDict(forminfo)
        return self.app.post(
            '/new_hunt', data=self.imdict, follow_redirects=True)

    def registered_statement(self, hunt, email=email()):
        return {
            "actor": xapi.make_agent(email),
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/registered",
                "display": {
                    "en-US": "registered"
                }
            },
            "object": xapi.hunt_activity(hunt)
        }

    def register_participant(self, app, participant_email, name):
        return app.post(
            '/register_participant?hunt_id=1',
            data={
                'email': participant_email,
                'name': name
            },
            follow_redirects=True
        )

    ### TESTS! ###

    def test_login_logout(self):
        response = self.login(self.admin['email'], self.admin['password'])
        self.assertIn('You were logged in', response.data)

        response = self.logout()
        self.assertIn('Login', response.data)

    def test_login_invalid_username(self):
        response = self.login(identifier(), identifier())
        self.assertIn('Invalid email or password', response.data)

    def test_pages_requiring_login(self):
        self.login(self.admin['email'], self.admin['password'])
        self.create_hunt()
        self.logout()

        for route in ['/hunts', '/hunts/1', '/settings']:
            response = self.app.get(route, follow_redirects=True)
            self.assertIn('login required', response.data)

    def test_create_admin(self):
        response = self.app.get('/admins')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Admin Registration', response.data)

        admin_email = email()
        password = identifier()

        response = self.create_admin(email=admin_email, password=password)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully created admin', response.data)

        self.logout()
        response = self.login(admin_email, password)
        self.assertEqual(response.status_code, 200)

    def test_create_settings(self):
        self.login(self.admin['email'], self.admin['password'])
        domain = 'thedomain'
        login = 'thelogin'
        settings_response = self.create_settings(
            domain=domain, login=login)

        self.assertEqual(settings_response.status_code, 200)
        self.assertIn(login, settings_response.data)
        self.assertIn(domain, settings_response.data)

    def test_create_and_show_hunt(self):
        self.login(self.admin['email'], self.admin['password'])
        name = identifier()
        participants = [{'email': email()} for _ in xrange(2)]
        items = [{'name': identifier()} for _ in xrange(2)]
        create_hunt_response = self.create_hunt(
            name=name, participants=participants, items=items)

        self.assertEqual(create_hunt_response.status_code, 200)

        # currently this always goes to 1 because it's a clean db
        show_hunt_response = self.app.get('/hunts/1', follow_redirects=True)
        self.assertEqual(show_hunt_response.status_code, 200)

        self.assertIn(name, show_hunt_response.data)

        for participant in participants:
            self.assertIn(participant['email'], show_hunt_response.data)

        for item in items:
            self.assertIn(item['name'], show_hunt_response.data)

    def test_delete_hunt(self):
        self.login(self.admin['email'], self.admin['password'])
        self.create_hunt()

        response = self.app.get('/hunts/1/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/hunts/1', follow_redirects=True)
        self.assertEqual(response.status_code, 404)

    def test_get_started(self):
        self.login(self.admin['email'], self.admin['password'])
        self.create_hunt()
        self.logout()
        response = self.app.get(
            '/get_started/hunts/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter your name and email', response.data)

    def test_show_item_codes(self):
        self.login(self.admin['email'], self.admin['password'])
        item1 = {'name': identifier()}
        item2 = {'name': identifier()}
        self.create_hunt(items=[item1, item2])

        response = self.app.get('/hunts/1/qrcodes')
        self.assertEqual(response.status_code, 200)
        for item in [item1, item2]:
            self.assertIn(item['name'], response.data)

        response = self.app.get('/hunts/1/items/1/qrcode')
        self.assertEqual(response.status_code, 200)
        self.assertIn(item1['name'], response.data)

    # this also tests the show_item function/route
    def test_whitelisted_participant(self):
        with app.test_client() as c:
            self.login(self.admin['email'], self.admin['password'])
            participant_email = email()
            self.create_hunt(
                participants=[{'email': participant_email}],
                items=[{'name': identifier()}])

            self.logout()

            # necessary to access item routes
            with c.session_transaction() as sess:
                sess['email'] = participant_email
                sess['intended_url'] = '/hunts/1'

            name = identifier()
            response = self.register_participant(c, participant_email, name)
            self.assertEqual(response.status_code, 200)

            response = c.get('/hunts/1/items/1', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(name, response.data)

    def test_not_whitelisted_participant(self):
        with app.test_client() as c:
            self.login(self.admin['email'], self.admin['password'])
            self.create_hunt()
            self.logout()

            with c.session_transaction() as sess:
                sess['admin_id'] = 1

            c.get('/hunts/1/items/1', follow_redirects=True)
            response = self.register_participant(c, email(), identifier())
            self.assertIn(
                'You are not on the list of allowed participants',
                response.data
            )

    def test_index_items(self):
        self.login(self.admin['email'], self.admin['password'])
        items = [{'name': identifier()}, {'name': identifier()}]
        participants = [{'email': email()}]
        self.create_hunt(items=items, participants=participants)
        self.logout()

        self.app.get('hunts/1/items')
        response = self.register_participant(
            self.app, participants[0]['email'], identifier())
        self.assertEqual(response.status_code, 200)

        for item in items:
            self.assertIn(item['name'], response.data)

    def test_put_state_doc(self):
        with app.test_request_context('/'):
            hunt_id = 1
            session_email = email()
            params = xapi.default_params(session_email, hunt_id)

            data = {'required_ids': [1, 2]}
            setting = MockSetting(BASIC_LOGIN, BASIC_PASSWORD, WAX_SITE)

            response = xapi.put_state(json.dumps(data), params, setting)
            self.assertEqual(response.status_code, 204)

            response = xapi.get_state_response(params, setting)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), data)

    def test_post_state_doc(self):
        with app.test_request_context('/'):
            hunt = MockHunt(1, identifier())
            statement = self.registered_statement(hunt)
            setting = MockSetting(BASIC_LOGIN, BASIC_PASSWORD, WAX_SITE)
            response = xapi.send_statement(statement, setting)
            self.assertEqual(response.status_code, 200)

    def test_send_begin_hunt_statement(self):
        with app.test_request_context('/'):
            hunt = MockHunt(1, identifier())
            statement = self.registered_statement(hunt)
            setting = MockSetting(BASIC_LOGIN, BASIC_PASSWORD, WAX_SITE)
            response = xapi.send_statement(statement, setting)
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
