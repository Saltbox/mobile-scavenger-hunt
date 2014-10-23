import unittest
import uuid
import json

from flask import session, g

from hunt import app

import xapi
import utils
import views


from mock import patch, MagicMock

app.config['DEBUG'] = True


def identifier():
    return uuid.uuid4().hex


def example_email():
    return '{}@example.com'.format(identifier())


class xAPITestCase(unittest.TestCase):
    def setUp(self):
        self.registration_data = {
            'email': example_email(),
            'name': identifier()
        }

    @patch('views.validate_participant')
    @patch('views.get_db')
    @patch('views.WaxCommunicator.send_statement')
    def test_register_participant_sends_xapi_statement(
            self, send_statement, get_db, valid_participant):
        with app.test_client() as c:
            valid_participant.return_value = MagicMock(), 'Error message'
            c.post(
                '/register_participant?hunt_id=1', data=self.registration_data)

            lrs = xapi.WaxCommunicator(
                MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
            )
            assert send_statement.called, "Expected a" \
                "began hunt statement to be sent but it wasn't"

    @patch('views.Hunt')
    @patch('views.WaxCommunicator.post_state')
    @patch('views.WaxCommunicator.get_state')
    @patch('views.WaxCommunicator.send_statement')
    @patch('views.get_db')
    def test_finding_item_updates_state(
            self, get_db, send_statement, get_state, post_state, Hunt):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['email'] = example_email()
            Hunt.find_by_id.return_value = MagicMock(name='some name')

            c.get('/hunts/1/items/1')

            assert post_state.called, "Expected a state document to be" \
                " updated by a call to post_state, but post_state was not" \
                " called"

    @patch('views.Hunt')
    @patch('views.WaxCommunicator')
    @patch('views.get_db')
    def test_finding_item_sends_found_item_statement(
            self, get_db, LRS, Hunt):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['email'] = example_email()
            Hunt.find_by_id.return_value = MagicMock(name='name')
            c.get('/hunts/1/items/1')

            assert LRS().send_found_item_statement.called, "Expected" \
                " finding an item to send a statement but a statement was" \
                " not sent"

    @patch('views.Hunt')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    @patch('views.get_db')
    def test_refinding_item_sends_refound_item_statement(
            self, get_db, LRS, already_found, Hunt):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['email'] = example_email()
            Hunt.find_by_id.return_value = MagicMock(name='some name')
            already_found.return_value = True
            c.get('/hunts/1/items/1')

            LRS().send_found_item_statement.assert_called_with(
                found_again=True)

    @patch('views.Hunt')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    @patch('views.hunt_requirements_completed')
    @patch('views.get_db')
    def test_completing_hunt_sends_completed_hunt_statement(
            self, get_db, req_completed, LRS, already_found, Hunt):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['email'] = example_email()
            Hunt.find_by_id.return_value = MagicMock(name='name')

            LRS().get_state.return_value = {'1': True}
            c.get('/hunts/1/items/1')

            assert LRS().send_completed_hunt_statement.called, "Expected" \
                " scavenger meeting all of the hunt requirements to send a" \
                " completed hunt statement"

if __name__ == '__main__':
    unittest.main()
