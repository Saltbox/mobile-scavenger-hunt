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
    def email(self):
        return '{}@example.com'.format(identifier())

    def setUp(self):
        self.app = app.test_client()
        db.create_all()
        email = 'dp@example.com'  # self.email()
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
            email=email(None), password=identifier()):
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
        ))

    def create_hunt(self,
                    name=identifier(),
                    participant_rule='by_whitelist',
                    participants=[email(None)],
                    items=[identifier()], all_required=True):

        # this is how wtforms-alchemy expects data
        # participants not being created for some reason
        participant_emails = [
            ('participants-{}-email'.format(index), email)
            for (index, email) in enumerate(participants)
        ]
        participant_registered = [
            ('participants-{}-registered'.format(index), email)
            for (index, email) in enumerate(participants)
        ]
        items = [
            ('items-{}-name'.format(index), item_name)
            for (index, item_name) in enumerate(items)
        ]

        forminfo = participant_emails + items + \
            [('all_required', True), ('name', name),
             ('participant_rule', participant_rule),

             ('participants-0-registered', True),
             ('participants-1-registered', True)]

        self.imdict = ImmutableMultiDict(forminfo)
        return self.app.post(
            '/new_hunt', data=self.imdict, follow_redirects=True)

    def submit_new_participant(self, email, username):
        return self.app.post(
            '/new_participant',
            data={
                'email': email,
                'name': username,
                'hunt_id': 1
            },
            follow_redirects=True)

    def registered_statement(self, hunt, email=email(None)):
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
        self.assertIn('Admin Signup', response.data)

        email = self.email()
        password = identifier()

        response = self.create_admin(email=email, password=password)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully created admin', response.data)

        self.logout()
        response = self.login(email, password)
        self.assertEqual(response.status_code, 200)

    def test_get_started(self):
        self.login(self.admin['email'], self.admin['password'])
        self.create_hunt()
        self.logout()
        response = self.app.get(
            '/get_started/hunts/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter your name and email', response.data)

    @unittest.skip('participants are not being created')
    def test_create_and_show_hunt(self):
        self.login(self.admin['email'], self.admin['password'])
        name = identifier()
        participants = [self.email() for _ in xrange(2)]
        items = [identifier() for _ in xrange(2)]
        create_hunt_response = self.create_hunt(
            name=name, participants=participants, items=items)

        self.assertEqual(create_hunt_response.status_code, 200)

        # currently this always goes to 1 because it's a clean db
        show_hunt_response = self.app.get('/hunts/1', follow_redirects=True)
        self.assertEqual(show_hunt_response.status_code, 200)

        self.assertIn(name, show_hunt_response.data)

        for participant in participants:
            self.assertIn(participant, show_hunt_response.data)

        for item in items:
            self.assertIn(item, show_hunt_response.data)

    def test_whitelisted_participant(self):
        with app.test_client() as c:
            self.login(self.admin['email'], self.admin['password'])
            username = identifier()
            participant_email = self.email()
            item_name = identifier()
            self.create_hunt(
                participants=[participant_email], items=[item_name])

            name = identifier()
            # workaround for create_hunt issue
            self.submit_new_participant(participant_email, name)
            self.logout()

            # necessary to access item routes
            with c.session_transaction() as sess:
                sess['email'] = participant_email
                sess['last_item_id'] = 1

            response = self.register_participant(c, email, name)
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
            response = self.register_participant(c, self.email(), identifier())
            self.assertIn(
                'You are not on the list of allowed participants',
                response.data
            )

    def test_no_email_for_new_participant(self):
        response = self.submit_new_participant(None, identifier())
        self.assertEqual(response.status_code, 400)

    def test_put_state_doc(self):
        with app.test_request_context('/'):
            hunt_id = 1
            session_email = self.email()
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
