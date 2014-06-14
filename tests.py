import unittest
import uuid
import hunt

from hunt import db

USERNAME = hunt.app.config['USERNAME']
PASSWORD = hunt.app.config['PASSWORD']


class HuntTestCase(unittest.TestCase):
    def setUp(self):
        self.app = hunt.app.test_client()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username, password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    ### TESTS! ###

    def test_login_logout(self):
        response = self.login(USERNAME, PASSWORD)
        assert 'You were logged in' in response.data

        response = self.logout()
        assert 'You were logged out' in response.data

    def test_admin_login(self):
        response = self.app.get('/')
        assert 'Scavenger Hunt List' not in response.data

        response = self.login(USERNAME, PASSWORD)
        assert 'Scavenger Hunt List' in response.data

    def create_hunt(self, name=str(uuid.uuid4().hex)):
        email = '{}@example.com'.format(uuid.uuid4().hex)
        item = str(uuid.uuid4().hex)
        all_required = "true"  # this is how the form submits
        response = self.app.post('/hunts', data=dict(
            name=name,
            participants=[email],
            items=[item],
            all_required=True,
        ), follow_redirects=True)
        return response

    def test_create_hunt(self):
        self.login(USERNAME, PASSWORD)
        name = str(uuid.uuid4().hex)
        response = self.create_hunt(name=name)
        assert name in response.data

    def test_create_and_show_hunt(self):
        self.login(USERNAME, PASSWORD)
        name = str(uuid.uuid4().hex)
        self.create_hunt(name=name)

        from models import Hunt
        hunt_id = Hunt.query.first().hunt_id  #currently always 1
        #hm. this goes to real data/hunt not test data
        response = self.app.get('/hunts/{}'.format(
            hunt_id), follow_redirects=True)
        assert response.status_code == 200
        assert name in response.data


if __name__ == '__main__':
    unittest.main()
