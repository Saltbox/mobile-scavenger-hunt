# import mock
import unittest
import uuid
import json

from flask import session, g

from hunt import app

import xapi
import utils
import views


from mock import patch, MagicMock, ANY

app.config['DEBUG'] = True


def identifier():
    return uuid.uuid4().hex


def example_email():
    return '{}@example.com'.format(identifier())


class xAPITestCase(unittest.TestCase):
    def setUp(self):
        self.request = MagicMock()
        self.admin = {'email': example_email(), 'password': identifier()}

    @patch('views.get_items')
    @patch('views.xapi.initialize_state_doc')
    @patch('views.xapi.default_params')
    @patch('views.WaxCommunicator.put_state')
    @patch('views.get_db')
    def test_create_state_doc_puts_state(
            self, get_db, put_state, default_params, initialize_state_doc,
            get_items):
        with app.test_request_context():
            state = {
                'hunt_completed': False, 'found_ids': [0],
                'total_items': 0, 'num_found': 0
            }
            initialize_state_doc.return_value = state
            views.create_state_doc(
                get_db(), MagicMock(), MagicMock(), MagicMock())
            put_state.assert_called_with(json.dumps(state), ANY)

    @patch('views.xapi')
    @patch('views.validate_participant')
    @patch('views.create_state_doc')
    @patch('views.get_items')
    @patch('views.get_hunt')
    @patch('views.get_participant')
    @patch('views.get_db')
    def test_register_participant_sends_xapi_statement(
            self, get_db, get_participant, get_hunt,
            get_items, create_state, valid_participant, xapi):
        with app.test_client() as c:
            data = {'email': example_email(), 'name': identifier()}
            valid_participant.return_value = MagicMock(), 'Error message'
            response = c.post('/register_participant?hunt_id=1', data=data)

            assert any(call[0] is 'send_began_hunt_statement'
                       for call in xapi.method_calls)

    def test_update_state_item_information(self):
        state = {'found_ids': [1], 'num_found': 0}
        item_id = 2
        xapi.update_state_item_information(state, item_id)
        assert item_id in state['found_ids']
        assert state['num_found'] == 1

    @patch('views.get_settings')
    @patch('views.xapi')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.WaxCommunicator')
    def test_finding_item_updates_state(
            self, LRS, get_item, get_hunt, part_registered,
            xapi, get_settings):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='some name')
            state = {
                'hunt_completed': False, 'found_ids': [1],
                'total_items': 1, 'num_found': 1
            }
            LRS().get_state().json.return_value = state
            response = c.get('/hunts/1/items/1')

            assert LRS().post_state.called

    @patch('views.xapi')
    @patch('views.validate_participant')
    @patch('views.create_state_doc')
    @patch('views.get_items')
    @patch('views.get_hunt')
    @patch('views.get_participant')
    @patch('views.get_db')
    def test_register_participant_sends_xapi_statement(
            self, get_db, get_participant, get_hunt,
            get_items, create_state, valid_participant, xapi):
        with app.test_client() as c:
            data = {'email': example_email(), 'name': identifier()}
            valid_participant.return_value = MagicMock(), 'Error message'
            response = c.post('/register_participant?hunt_id=1', data=data)

            assert any(call[0] is 'send_began_hunt_statement'
                       for call in xapi.method_calls)

    @patch('views.update_state_api_doc')
    @patch('views.get_settings')
    @patch('views.xapi')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.WaxCommunicator')
    def test_finding_item_sends_found_item_statement(
            self, LRS, get_item, get_hunt, part_registered,
            xapi, get_settings, update_state_api_doc):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='name')
            response = c.get('/hunts/1/items/1')

            assert xapi.send_found_item_statement.called

    @patch('views.update_state_api_doc')
    @patch('views.get_settings')
    @patch('views.xapi')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    def test_refinding_item_sends_found_item_statement(
            self, LRS, already_found, get_item, get_hunt, part_registered,
            xapi, get_settings, update_state_api_doc):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='some name')
            response = c.get('/hunts/1/items/1')
            assert xapi.send_refound_item_statement.called

    @patch('views.update_state_api_doc')
    @patch('views.get_settings')
    @patch('views.xapi')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    def test_completing_hunt_sends_completed_hunt_statement(
            self, LRS, already_found, get_item, get_hunt, part_registered,
            xapi, get_settings, update_state_api_doc):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='name')
            state = {
                'hunt_completed': False, 'found_ids': [1],
                'total_items': 1, 'num_found': 1
            }
            LRS().get_state().json.return_value = state
            response = c.get('/hunts/1/items/1')

            assert xapi.send_completed_hunt_statement.called

if __name__ == '__main__':
    unittest.main()
