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
    @patch('views.get_settings')
    @patch('views.WaxCommunicator.put_state')
    @patch('views.WaxCommunicator.send_began_hunt_statement')
    @patch('views.validate_participant')
    @patch('views.get_participant')
    @patch('views.get_db')
    @patch('views.get_hunt')
    def test_register_participant_puts_state(
            self, get_hunt, get_db, get_participant, validate_participant,
            send_began, put_state, get_settings, get_items):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(num_required=2)

            data = {'email': example_email(), 'name': identifier()}
            validate_participant.return_value = MagicMock(), 'Error message'
            response = c.post('/register_participant?hunt_id=1', data=data)
            put_state.called

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
        lrs = xapi.WaxCommunicator(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        state = lrs.update_state_item_information(state, item_id)
        assert item_id in state['found_ids']
        assert state['num_found'] == 1

    @patch('views.get_settings')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.WaxCommunicator')
    def test_finding_item_updates_state(
            self, LRS, get_item, get_hunt, part_registered,
            get_settings):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='some name')
            state = {
                'hunt_completed': False, 'found_ids': [1],
                'total_items': 1, 'num_found': 1
            }
            LRS().get_state().json.return_value = state
            response = c.get('/hunts/1/items/1')

            assert LRS().update_state_api_doc.called

    @patch('views.validate_participant')
    @patch('views.WaxCommunicator')
    @patch('views.get_items')
    @patch('views.get_hunt')
    @patch('views.get_participant')
    @patch('views.get_db')
    def test_register_participant_sends_xapi_statement(
            self, get_db, get_participant, get_hunt,
            get_items, LRS, valid_participant):
        with app.test_client() as c:
            data = {'email': example_email(), 'name': identifier()}
            valid_participant.return_value = MagicMock(), 'Error message'
            response = c.post('/register_participant?hunt_id=1', data=data)

            # assert any(call[0] is 'send_began_hunt_statement'
            #            for call in LRS.method_calls)
            assert LRS().send_began_hunt_statement.called

    @patch('views.get_settings')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.WaxCommunicator')
    def test_finding_item_sends_found_item_statement(
            self, LRS, get_item, get_hunt, part_registered,
            get_settings):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='name')
            response = c.get('/hunts/1/items/1')

            assert LRS().send_found_item_statement.called

    @patch('views.get_settings')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    def test_refinding_item_sends_found_item_statement(
            self, LRS, already_found, get_item, get_hunt, part_registered,
            get_settings):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='some name')
            already_found.return_value = True
            response = c.get('/hunts/1/items/1')

            LRS().send_found_item_statement.assert_called_with(found_again=True)

    @patch('views.get_settings')
    @patch('views.participant_registered')
    @patch('views.get_hunt')
    @patch('views.get_item')
    @patch('views.item_already_found')
    @patch('views.WaxCommunicator')
    def test_completing_hunt_sends_completed_hunt_statement(
            self, LRS, already_found, get_item, get_hunt, part_registered,
            get_settings):
        with app.test_client() as c:
            get_hunt.return_value = MagicMock(name='name')
            state = {
                'hunt_completed': False, 'found_ids': [1], 'num_required': 1,
                'total_items': 1, 'num_found': 1, 'required_ids': [1]
            }
            LRS().update_state_item_information.return_value = state
            response = c.get('/hunts/1/items/1')

            assert LRS().send_completed_hunt_statement.called

if __name__ == '__main__':
    unittest.main()
