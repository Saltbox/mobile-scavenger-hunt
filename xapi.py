from flask import request, make_response, render_template

import json
import requests
import uuid
import urllib

import logging

logger = logging.getLogger(__name__)


def make_mailto(email):
    ident, domain = email.rsplit('@', 1)
    ident = urllib.quote_plus(ident)
    return "mailto:{}@{}".format(ident, domain)


def verb_found():
    return {
        "id": "http://saltbox.com/xapi/verbs/found",
        "display": {
            "en-US": "found"
        }
    }


def verb_refound():
    return {
        "id": "http://saltbox.com/xapi/verbs/refound",
        "display": {
            "en-US": "refound"
        }
    }


class WaxCommunicator:
    def __init__(
            self, settings, host_url, hunt, current_item, scavenger_info={}):
        self.login = settings.login
        self.password = settings.password
        self.site = settings.wax_site
        self.state_api_endpoint = 'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site)

        self.host_url = host_url
        self.hunt = hunt
        self.current_item = current_item
        self.scavenger = scavenger_info

    submission_headers = {
        "x-experience-api-version": "1.0.0",
        "content-type": "application/json"
    }

    def default_params(self):
        return {
            'agent': json.dumps(self.make_agent()),
            'activityId': self.hunt_activity_id(),
            'stateId': 'hunt_progress'
        }

    def get_state(self):
        params = self.default_params()
        logger.info(
            'requesting state from the state api for site, %s,'
            ' with params, %s', self.site, params)
        response = requests.get(
            self.state_api_endpoint,
            params=params,
            headers={"x-experience-api-version": "1.0.0"},
            auth=(self.login, self.password)
        )
        logger.info('response from state api: %s', response)
        if response:
            return response.json()
        return {}

    def post_state(self, data):
        return requests.post(
            self.state_api_endpoint,
            params=self.default_params(),
            data=data,
            headers=self.submission_headers,
            auth=(self.login, self.password)
        )

    def make_agent(self):
        agent = {"mbox": make_mailto(self.scavenger['email'])}
        if self.scavenger.get('name'):
            agent['name'] = self.scavenger['name']
        return agent

    def update_state_api_doc(self, state):
        logger.info(
            'Updating state document for %s on hunt, "%s".',
            self.scavenger['email'], self.hunt.name)
        self.post_state(json.dumps(state))

    def send_statement(self, statement):
        return requests.post(
            'https://{}.waxlrs.com/TCAPI/statements'.format(self.site),
            headers=self.submission_headers,
            data=json.dumps(statement),
            auth=(self.login, self.password)
        )

    def hunt_activity_id(self):
        return "{}hunts/{}".format(self.host_url, self.hunt.hunt_id)

    def hunt_activity(self):
        return {
            "id": self.hunt_activity_id(),
            "definition": {
                "type": "{}activities/type/scavengerhunt".format(
                    self.host_url),
                "name": {
                    "und": self.hunt.name
                }
            },
            "objectType": "Activity"
        }

    def send_began_hunt_statement(self):
        self.send_statement(self.began_hunt_statement())
        logger.info(
            '%s began hunt, %s. sending statement to Wax',
            self.scavenger['email'], self.hunt.name)

    def began_hunt_statement(self):
        return {
            "actor": self.make_agent(),
            "verb": {
                "id": "http://saltbox.com/xapi/verbs/registered",
                "display": {
                    "en-US": "registered for"
                }
            },
            "object": self.hunt_activity()
        }

    def send_found_item_statement(self, found_again=False):
        if found_again:
            self.send_statement(self.refound_item_statement())
            logger.info(
                '%s refound item, "%s", from hunt, "%s". sending statement to Wax',
                self.scavenger['email'], self.current_item.name,
                self.hunt.name)
        else:
            self.send_statement(self.found_item_statement())
            logger.info(
                '%s found item, "%s", from hunt, "%s". sending statement to Wax',
                self.scavenger['email'], self.current_item.name,
                self.hunt.name)

    def found_item_statement(self):
        return {
            "actor": self.make_agent(),
            "verb": verb_found(),
            "object": {
                "id": "{}hunts/{}/items/{}".format(
                    self.host_url, self.hunt.hunt_id,
                    self.current_item.item_id),
                "definition": {
                    "type": "{}activities/type/scavengerhunt".format(
                        self.host_url),
                    "name": {
                        "und": "{} from {}".format(
                            self.current_item.name, self.hunt.name)
                    }
                },
                "objectType": "Activity"
            },
            "context": {
                "contextActivities": {
                    "parent": self.hunt_activity()
                }
            }
        }

    def refound_item_statement(self):
        found_statement = self.found_item_statement()
        found_statement['verb'] = verb_refound()
        return found_statement

    def send_completed_hunt_statement(self):
        logger.info(
            '%s completed hunt, %s. sending statement to Wax',
            self.scavenger['email'], self.hunt.name)
        self.send_statement(self.completed_hunt_statement())

    def completed_hunt_statement(self):
        return {
            'actor': self.make_agent(),
            'verb': {
                'id': 'http://adlnet.gov/expapi/verbs/completed/',
                'display': {
                    'en-US': 'completed'
                }
            },
            "object": self.hunt_activity(),
            "result": {
                "success": True,
                "completion": True,
            }
        }
