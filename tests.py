import unittest
import uuid

from werkzeug.datastructures import ImmutableMultiDict

from hunt import db, app

app.config['DEBUG'] = True


def identifier():
    return uuid.uuid4().hex


class HuntTestCase(unittest.TestCase):
    def email(self):
        return '{}@example.com'.format(identifier())

    def setUp(self):
        self.app = app.test_client()
        db.create_all()
        email = self.email()
        password = identifier()
        self.create_admin(email=email, password=password)
        self.admin = {'email': email, 'password': password}
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
        self.create_hunt()
        for route in ['/hunts', 'hunts/1']:
            response = self.app.get('/hunts', follow_redirects=True)
            self.assertIn('login required', response.data)

    def create_hunt(self,
                    name=identifier(),
                    participants=[email(None)],
                    items=[identifier()], all_required=True):

        # this is how wtforms-alchemy expects data
        participants = [
            ('participants-{}-email'.format(index), email)
            for (index, email) in enumerate(participants)
        ]
        items = [
            ('items-{}-name'.format(index), item_name)
            for (index, item_name) in enumerate(items)
        ]
        forminfo = participants + items + [('all_required', True), ('name', name)]
        imdict = ImmutableMultiDict(forminfo)
        return self.app.post(
            '/hunts', data=imdict, follow_redirects=True)

    def create_admin(
            self, first_name=identifier(), last_name=identifier(),
            email=email(None),
            password=identifier()):
        return self.app.post('/admins', data=dict(
            first_name=first_name, last_name=last_name, email=email,
            password=password
        ))

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
        response = self.app.get(
            '/get_started/hunts/1/items/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter your name and email', response.data)

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

    def submit_new_participant(self, email, username):
        return self.app.post(
            '/new_participant?hunt_id=1&item_id=1',
            data={
                'email': email,
                'name': username
            },
            follow_redirects=True)

    def test_new_participant(self):
        self.login(self.admin['email'], self.admin['password'])
        username = identifier()
        email = self.email()
        item_name = identifier()
        self.create_hunt(participants=[email], items=[item_name])

        # participant is on the whitelist
        response = self.submit_new_participant(email, username)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "{}! you found {}".format(username, item_name),
            response.data
        )

    def test_prevent_unlisted_new_participant(self):
        # participant is not on the whitelist
        response = self.submit_new_participant(self.email(), identifier())
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'you are not on the list of participants for this hunt',
            response.data
        )

    def test_no_email_for_new_participant(self):
        response = self.submit_new_participant(None, identifier())
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
