# import mock
import unittest
import uuid
import json

from werkzeug.datastructures import ImmutableMultiDict
from flask import session, g
from hunt import app, bcrypt

import xapi
import utils


from mock import patch, MagicMock

app.config['DEBUG'] = True


def identifier():
    return uuid.uuid4().hex


def email():
    return '{}@example.com'.format(identifier())


class HuntTestCase(unittest.TestCase):
    def setUp(self):
        self.request = MagicMock()
        self.app = app.test_client()
        self.admin = {'email': email(), 'password': identifier()}

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

    def login(self, app, username, password):
        return app.post('/login', data=dict(
            username=username, password=password
        ), follow_redirects=True)

    def logout(self, app):
        return app.get('/logout', follow_redirects=True)

    def create_admin(self, app, email, password):
        return app.post('/admins', data=dict(
            email=email, password=password
        ))

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

    def create_settings(self, app, wax_site, admin_id, login, password):
        return app.post('/settings', data=dict(
            wax_site=wax_site, admin_id=admin_id,
            login=login, password=password
        ), follow_redirects=True)

    def create_mock_admin(self, get_db, valid=False):
        if valid:
            pw_hash = bcrypt.generate_password_hash(self.admin['password'])
            admin = MagicMock(pw_hash=pw_hash)
        else:
            admin = MagicMock(admin_id=1)

        admin.get_id.return_value = 1
        return admin

    ### TESTS! ###

    @patch('views.get_db')
    def test_visit_homepage_works(self, get_db):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sign in', response.data)

    @patch('views.get_admin')
    @patch('views.get_db')
    def test_create_admin_works(self, get_db, get_admin):
        get_admin.return_value = self.create_mock_admin(get_db)
        with app.test_client() as c:
            password = identifier()
            admin_email = email()
            response = self.create_admin(
                app=c, email=admin_email, password=password)

            self.assertEqual(response.status_code, 200)
            self.assertIn('Welcome to xAPI Scavenger Hunt', response.data)

    @patch('views.get_settings')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    @patch('views.get_admin')
    @patch('views.get_db')
    def test_create_settings(
            self, get_db, get_admin, login_disabled, current_user, get_settings):
        get_admin.return_value = self.create_mock_admin(get_db)
        current_user.admin_id = 1
        with app.test_client() as c:
            response = self.create_settings(
                c, identifier(), 1, identifier(), identifier())

            self.assertEqual(response.status_code, 200)
            # successfully saving settings redirects to new hunt page
            self.assertIn("Let's create a hunt!", response.data)

    @patch('views.get_settings')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    @patch('views.get_db')
    @patch('views.get_admin')
    def test_previously_saved_settings_appear_when_visiting_settings(
            self, get_admin, get_db, login_disabled, current_user, get_settings):
        login_disabled = True
        get_admin.return_value = self.create_mock_admin(get_db)
        current_user.admin_id = 1

        wax_site = identifier()
        login = identifier()
        password = identifier()
        get_settings.return_value = MagicMock(
            wax_site=wax_site, login=login, password=password)
        with app.test_client() as c:
            response = c.get('/settings')
            self.assertEqual(response.status_code, 200)
            for text in [wax_site, login, password]:
                self.assertIn(text, response.data)

    @patch('views.get_admin')
    @patch('views.get_db')
    def test_login_valid_credentials_allows_user_to_enter_site(
            self, get_db, get_admin):
        get_admin.return_value = self.create_mock_admin(get_db, valid=True)
        with app.test_client() as c:
            self.create_admin(c, self.admin['email'], self.admin['password'])
            self.logout(c)
            response = self.login(c, self.admin['email'], self.admin['password'])
            self.assertEqual(response.status_code, 200)

    @patch('views.get_admin')
    def test_login_invalid_credentials_prevents_user_from_entering_site(
            self, get_admin):
        get_admin.return_value = None
        with app.test_client() as c:
            admin_email = email()
            password = identifier()

            response = self.login(c, admin_email, password)
            self.assertEqual(response.status_code, 200)
            self.assertIn(
                'Invalid email and password combination', response.data)

    @patch('views.get_admin')
    @patch('views.get_db')
    def test_pages_requiring_login(self, get_db, get_admin):
        get_admin.return_value = self.create_mock_admin(get_db)
        for route in ['/hunts', '/hunts/1', '/settings']:
            response = self.app.get(route, follow_redirects=True)
            self.assertIn('Please log in to access this page.', response.data)

    @patch('views.get_db')
    @patch('views.login_manager._login_disabled')
    @patch('views.current_user')
    def test_visiting_new_hunt_works(self, current_user, login_disabled, get_db):
        login_disabled = True
        current_user.admin_id = 1
        with app.test_client() as c:
            response = c.get('/new_hunt')
            self.assertEqual(response.status_code, 200)

    @patch('views.get_admin')
    @patch('views.get_db')
    def test_create_hunt_works(self, get_db, get_admin):
        get_admin.return_value = self.create_mock_admin(get_db, valid=True)
        with app.test_client() as c:
            participants = [{'email': email()} for _ in xrange(2)]
            items = [{'name': identifier()} for _ in xrange(2)]
            create_hunt_response = self.create_hunt(
                name=identifier(), participants=participants, items=items)

            self.assertEqual(create_hunt_response.status_code, 200)

    @patch('views.get_hunt')
    def test_show_hunt_works(self, get_hunt):
        name = identifier()
        participants = [{'email': email()} for _ in xrange(2)]
        items = [{'name': identifier()} for _ in xrange(2)]
        get_hunt.return_value = MagicMock(
            name=name, participants=participants, items=items,
            participant_rule='by_whitelist'
        )
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
            show_hunt_response = c.get('/hunts/1', follow_redirects=True)
            self.assertEqual(show_hunt_response.status_code, 200)

            self.assertIn(name, show_hunt_response.data)

            for participant in participants:
                self.assertIn(participant['email'], show_hunt_response.data)

            for item in items:
                self.assertIn(item['name'], show_hunt_response.data)

    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    def test_show_hunt_on_nonexistent_hunt_id_404s(
            self, login_disabled, current_user):
        current_user.admin_id = 1
        login_disabled = True
        with app.test_client() as c:
            response = self.app.get('/hunts/1', follow_redirects=True)
            self.assertEqual(response.status_code, 404)

    @patch('views.xapi')
    @patch('views.get_hunt')
    @patch('views.get_settings')
    @patch('views.get_db')
    @patch('views.get_items')
    def test_index_items_displays_all_items(
            self, get_items, _get_db, _get_settings, _get_hunt, _xapi):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['email'] = email()

            items = [{'name': identifier()}, {'name': identifier()}]
            get_items.return_value = items

            response = c.get('hunts/1/items')
            self.assertEqual(response.status_code, 200)

            for item in items:
                self.assertIn(item['name'], response.data)

    @patch('views.login_manager._login_disabled')
    def test_index_items_on_nonexistent_hunt_404s(self, login_disabled):
        login_disabled = True
        with app.test_client() as c:
            response = c.get('hunts/1/items')
            self.assertEqual(response.status_code, 404)

    @patch('views.get_hunt')
    def test_get_started(self, get_hunt):
        response = self.app.get(
            '/get_started/hunts/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter your name and email', response.data)

    @patch('views.get_admin')
    @patch('views.get_hunt')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    @patch('views.get_db')
    def test_show_all_hunt_item_codes_works(
            self, get_db, login_disabled, current_user, get_hunt, get_admin):
        current_user.admin_id = 1
        login_disabled = True
        get_admin.return_value = self.create_mock_admin(get_db, valid=True)
        with app.test_client() as c:
            item1 = MagicMock()
            item1.name = identifier()
            item1.item_id = 1
            item2 = MagicMock()
            item2.name = identifier()
            item2.item_id = 2

            get_hunt.return_value = MagicMock(items=[item1, item2])

            response = self.app.get('/hunts/1/qrcodes')
            self.assertEqual(response.status_code, 200)

            for item in [item1, item2]:
                self.assertIn(item.name, response.data)

    @patch('views.get_admin')
    @patch('views.get_hunt')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    @patch('views.get_db')
    def test_show_one_hunt_item_code_works(
            self, get_db, login_disabled, current_user, get_hunt, get_admin):
        current_user.admin_id = 1
        login_disabled = True
        get_admin.return_value = self.create_mock_admin(get_db, valid=True)
        with app.test_client() as c:
            item1 = MagicMock()
            item1.name = identifier()
            item1.item_id = 1
            hunt = MagicMock(items=[item1])
            get_hunt.return_value = hunt

            response = c.get('/hunts/1/items/1/qrcode')
            self.assertEqual(response.status_code, 200)
            self.assertIn(item1.name, response.data)


    @patch('views.get_admin')
    @patch('views.get_hunt')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    @patch('views.get_db')
    def test_delete_hunt_works(
            self, get_db, login_disabled, current_user, get_hunt, get_admin):
        current_user.admin_id = 1
        login_disabled = True
        get_admin.return_value = self.create_mock_admin(get_db, valid=True)
        with app.test_client() as c:
            hunt = MagicMock(admin_id=1)
            get_hunt.return_value = hunt
            response = c.get('/hunts/1/delete', follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # make get_hunt return None
            get_hunt.return_value = None
            response = c.get('/hunts/1', follow_redirects=True)
            self.assertEqual(response.status_code, 404)

    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    def test_delete_nonexistent_hunt_404s(self, login_disabled, current_user):
        current_user.admin_id = 1
        login_disabled = True
        with app.test_client() as c:
            response = c.get('hunts/1/delete')
            self.assertEqual(response.status_code, 404)

    @patch('views.get_hunt')
    @patch('views.current_user')
    @patch('views.login_manager._login_disabled')
    def test_delete_other_admin_hunt_404s(
            self, login_disabled, current_user, get_hunt):
        get_hunt().admin_id = 1
        current_user.admin_id = 2
        login_disabled = True
        with app.test_client() as c:
            response = c.get('hunts/1/delete')
            self.assertEqual(response.status_code, 404)

    @patch('utils.get_hunt_domain')
    @patch('views.get_db')
    def test_validate_participant_by_domain(self, get_db, get_hunt_domain):
        domain = get_hunt_domain.return_value = 'example.com'
        email = '{}@{}'.format(identifier(), domain)
        valid, _ = utils.validate_participant(get_db(), email, 1, 'by_domain')
        self.assertTrue(valid)

    @patch('views.get_db')
    def test_validate_participate_by_domain_invalid_domain(self, get_db):
        different_domain_email = '{}@not.example.com'.format(identifier())
        invalid, _ = utils.validate_participant(
            get_db(), different_domain_email, 1, 'by_domain')
        self.assertFalse(invalid)

    @patch('utils.get_participant')
    @patch('views.get_db')
    def test_validate_participant_by_whitelist(self, get_db, get_participant):
        # mock will be truthy when returned from the check for participant
        valid, _ = utils.validate_participant(
            get_db(), email(), 1, 'by_whitelist')
        self.assertTrue(valid)

    @patch('utils.get_participant')
    @patch('views.get_db')
    def test_validate_participant_by_whitelist_with_invalid_email(
            self, get_db, get_participant):
        get_participant.return_value = None
        invalid, _ = utils.validate_participant(
            get_db(), email(), 1, 'by_whitelist')
        self.assertFalse(invalid)

    @patch('views.get_db')
    def test_validate_participant_anyone_can_participate(self, get_db):
        valid, err_msg = utils.validate_participant(
            get_db(), email(), 1, 'anyone')
        self.assertTrue(valid)

    # Flask-Login calls load_user which uses Admin, around the
    # time response is returned
    @patch('views.Admin')
    @patch('views.xapi')
    @patch('views.get_settings')
    @patch('views.get_hunt')
    @patch('views.get_db')
    def test_valid_participant_can_register_for_hunt(
            self, get_db, get_hunt, get_settings, xapi, Admin):
        with app.test_client() as c:
            response = c.post(
                '/register_participant?hunt_id=1',
                data={
                    'email': email(),
                    'name': identifier()
                },
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)

    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.get_settings')
    @patch('views.ready_to_send_statements')
    @patch('views.get_participant')
    @patch('views.xapi')
    def test_registered_participant_can_resume_hunt(
            self, xapi, get_participant, ready_to_send_statements,
            get_settings, get_item, get_hunt):
        state_report = MagicMock()
        state_report.get.return_value = False
        xapi.update_state.return_value = state_report, MagicMock()
        with app.test_client() as c:
            participant_email = email()
            name = identifier()

            # necessary to access item routes
            with c.session_transaction() as sess:
                sess['email'] = participant_email
                sess['name'] = name

            response = c.get('/hunts/1/items/1', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(name, response.data)

    @patch('views.get_item')
    @patch('views.get_settings')
    @patch('views.ready_to_send_statements')
    @patch('views.get_participant')
    @patch('views.xapi')
    def test_registered_participant_congratulated_on_hunt_finish(
        self, xapi, get_participant, ready_to_send_statements,
            get_settings, get_item):
        state_report = MagicMock()
        state_report.get.return_value = True
        xapi.update_state.return_value = state_report, MagicMock()
        with app.test_client() as c:
            participant_email = email()
            with c.session_transaction() as sess:
                sess['email'] = participant_email
            response = c.get('/hunts/1/items/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('congratulations!', response.data)

    def test_show_item_on_nonexistent_hunt_404s(self):
        with app.test_client() as c:
            response = c.get('/hunts/1/items/1', follow_redirects=True)
            self.assertEqual(response.status_code, 404)

    @patch('views.get_item')
    @patch('views.get_db')
    def test_show_item_for_nonexistent_item_404s(self, get_db, get_item):
        get_item.return_value = None
        with app.test_client() as c:
            response = c.get('/hunts/1/items/1')
            self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
