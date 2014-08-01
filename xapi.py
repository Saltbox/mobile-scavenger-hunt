from hunt import logger
from flask import request, make_response, render_template

import json
import requests


def hunt_activity_id(hunt_id):
    return "{}hunts/{}".format(request.host_url, hunt_id)


def hunt_activity(hunt):
    return {
        "id": hunt_activity_id(hunt.hunt_id),
        "definition": {
            "type": "{}activities/type/scavengerhunt".format(
                request.host_url),
            "name": {
                "und": hunt.name
            }
        },
        "objectType": "Activity"
    }


def begin_hunt_statement(actor, hunt):
    logger.debug(
        'participant began hunt. sending statement to Wax')
    return {
        "actor": actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/registered",
            "display": {
                "en-US": "registered"
            }
        },
        "object": hunt_activity(hunt)
    }


def verb_completed():
    return {
        "id": "http://adlnet.gov/expapi/verbs/completed",
        "display": {
            "en-US": "completed"
        }
    }


def found_item_statement(actor, hunt, item):
    return {
        "actor": actor,
        "verb": verb_completed(),
        "object": {
            "id": "{}hunts/{}/items/{}".format(
                request.host_url, hunt.hunt_id, item.item_id),
            "definition": {
                "type": "{}activities/type/scavengerhunt".format(
                    request.host_url),
                "name": {
                    "und": "find item {} from {}".format(item.name, hunt.name)
                }
            },
            "objectType": "Activity"
        },
        "context": {
            "contextActivities": {
                "parent": hunt_activity(hunt)
            }
        }
    }


# participant found every item
def completed_hunt_statement(actor, hunt):
    return {
        'actor': actor,
        'verb': verb_completed(),
        "object": hunt_activity(hunt)
    }


def send_statement(statement, setting):
    return requests.post(
        'https://{}.waxlrs.com/TCAPI/statements'.format(setting.wax_site),
        headers={
            "Content-Type": "application/json",
            "x-experience-api-version": "1.0.0"
        },
        data=json.dumps(statement),
        auth=(setting.login, setting.password)
    )


# later prevent resending statements if they for whatever reason scan the
# qrcode multiple times
def send_statements(actor, hunt, item, state, setting, params):
    send_statement(
        found_item_statement(actor, hunt, item), setting)

    logger.debug('sending statements with state: %s', state)
    if state['num_found'] == hunt.num_required and not state['required_ids']:
        send_statement(
            completed_hunt_statement(actor, hunt), setting)
        return make_response(render_template('congratulations.html'))


def put_state(data, params, setting):
    return requests.put(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            setting.wax_site),
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )


def post_state(data, params, setting):
    return requests.post(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            setting.wax_site),
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )


def get_state_response(params, setting):
    return requests.get(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            setting.wax_site),
        params=params,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )


def default_params(email, hunt_id):
    return {
        'agent': json.dumps(make_agent(email)),
        'activityId': "{}/hunts/{}".format(request.host_url, hunt_id),
        'stateId': 'hunt_progress'
    }


def make_agent(email):
    return {"mbox": "mailto:{}".format(email)}
