import unittest
import uuid

from flask import g

from hunt import db, app


class HuntTestCase(unittest.TestCase):
    def email(self):
        return '{}@example.com'.format(uuid.uuid4().hex)

    def setUp(self):
        self.app = app.test_client()
        db.create_all()
        email = self.email()
        password = uuid.uuid4().hex
        self.create_admin(email=email, password=password)
        self.admin = {'email': email, 'password': password}
        self.logout()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.create_all()

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
        self.assertIn('log in', response.data)

    def test_admin_login(self):
        response = self.app.get('/hunts')
        self.assertNotIn('Scavenger Hunt List', response.data)

        response = self.login(self.admin['email'], self.admin['password'])

        self.assertIn('Scavenger Hunt List', response.data)

    def create_hunt(self,
                    name=uuid.uuid4().hex,
                    participants=[email(None)],
                    items=[uuid.uuid4().hex], all_required=True):
        return self.app.post(
            '/hunts',
            data=dict(
                name=name, participants=participants,
                items=items, all_required=all_required),
            follow_redirects=True)

    def create_admin(
            self, first_name=uuid.uuid4().hex, last_name=uuid.uuid4().hex,
            email=email(None),
            password=uuid.uuid4().hex):
        return self.app.post('/admins', data=dict(
            first_name=first_name, last_name=last_name, email=email,
            password=password
        ))

    def test_create_admin(self):
        response = self.app.get('/admins')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Admin Signup', response.data)

        email = self.email()
        password = uuid.uuid4().hex

        response = self.create_admin(email=email, password=password)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully created admin', response.data)

        self.logout()
        response = self.login(email, password)
        self.assertEqual(response.status_code, 200)

    def test_get_started(self):
        self.create_hunt()
        response = self.app.get('/get_started/hunts/1/items/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter your name and email', response.data)


if __name__ == '__main__':
    unittest.main()
