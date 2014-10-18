from hunt import logger
from flask import request, make_response, render_template

import json
import requests
import uuid

from utils import get_items


def hunt_activity_id(hunt_id, host_url):
    return "{}hunts/{}".format(host_url, hunt_id)


def hunt_activity(hunt, host_url):
    return {
        "id": hunt_activity_id(hunt.hunt_id, host_url),
        "definition": {
            "type": "{}activities/type/scavengerhunt".format(
                request.host_url),
            "name": {
                "und": hunt.name
            }
        },
        "objectType": "Activity"
    }


def began_hunt_statement(actor, hunt, host_url):
    return {
        "actor": actor,
        "verb": {
            "id": "http://saltbox.com/xapi/verbs/registered",
            "display": {
                "en-US": "registered for"
            }
        },
        "object": hunt_activity(hunt, host_url)
    }


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


def found_item_statement(actor, hunt, item, host_url):
    return {
        "actor": actor,
        "verb": verb_found(),
        "object": {
            "id": "{}hunts/{}/items/{}".format(
                request.host_url, hunt.hunt_id, item.item_id),
            "definition": {
                "type": "{}activities/type/scavengerhunt".format(host_url),
                "name": {
                    "und": "{} from {}".format(item.name, hunt.name)
                }
            },
            "objectType": "Activity"
        },
        "context": {
            "contextActivities": {
                "parent": hunt_activity(hunt, host_url)
            }
        }
    }


def refound_item_statement(actor, hunt, item, host_url):
    found_statement = found_item_statement(actor, hunt, item, host_url)
    found_statement['verb'] = verb_refound()
    return found_statement


# participant met requirements for completion
def completed_hunt_statement(actor, hunt, host_url):
    return {
        'actor': actor,
        'verb': {
            'id': 'http://adlnet.gov/expapi/verbs/completed/',
            'display': {
                'en-US': 'completed'
            }
        },
        "object": hunt_activity(hunt, host_url),
        "result": {
            "success": True,
            "completion": True,
        }
    }


def put_state(data, params, settings):
    return requests.put(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site),
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0",
            "content-type": "application/json"
        },
        auth=(settings.login, settings.password)
    )


def post_state(data, params, settings):
    return requests.post(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site),
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0",
            "content-type": "application/json"
        },
        auth=(settings.login, settings.password)
    )


def default_params(email, hunt_id, host_url):
    return {
        'agent': json.dumps(make_agent(email, None)),
        'activityId': hunt_activity_id(hunt_id, host_url),
        'stateId': 'hunt_progress'
    }


def make_agent(email, name):
    agent = {"mbox": "mailto:{}".format(email)}
    if name:
        agent['name'] = name
    return agent


def get_state(params, settings):
    logger.info(
        'requesting state from the state api for site, %s,'
        ' with params, %s', settings.wax_site, params)
    return requests.get(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site),
        params=params,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(settings.login, settings.password)
    )


def initialize_state_doc(num_required, items):
    required_ids = [
        item.item_id for item in items if item.required]

    return {
        'found_ids': [],
        'num_found': 0,
        'required_ids': required_ids,
        'total_items': len(items),
        'num_required': num_required,
        'hunt_completed': False
    }


def hunt_requirements_completed(state):
    required_ids = set(state['required_ids'])
    found_ids = set(state['found_ids'])
    num_found = state['num_found']
    num_required = state['num_required']

    if required_ids:
        required_found = required_ids.issubset(found_ids)
        return num_found >= num_required and required_found
    else:
        return num_found >= num_required


def update_state_item_information(state, item):
    item_id = int(item.item_id)
    if item_id not in state['found_ids']:
        state['num_found'] += 1
    state['found_ids'].append(item_id)
    return state


def send_began_hunt_statement(name, email, hunt, host_url, settings):
    actor = make_agent(email, name)
    statement = began_hunt_statement(actor, hunt, host_url)
    send_statement(statement, settings)
    logger.info(
        '%s began hunt, %s. sending statement to Wax', email, hunt.name)


def send_found_item_statement(name, email, hunt, item, host_url, settings):
    actor = make_agent(email, name)
    statement = found_item_statement(actor, hunt, item, host_url)
    send_statement(statement, settings)
    logger.info(
        '%s found item, %s, from hunt, %s. sending statement to Wax',
        email, item.name, hunt.name)


def send_refound_item_statement(name, email, hunt, item, host_url, settings):
    actor = make_agent(email, name)
    statement = refound_item_statement(actor, hunt, item, host_url)
    send_statement(statement, settings)
    logger.info(
        '%s refound item, %s, from hunt, %s. sending statement to Wax',
        email, item.name, hunt.name)


def send_completed_hunt_statement(name, email, hunt, item, host_url, settings):
    actor = make_agent(email, name)
    statement = completed_hunt_statement(actor, hunt, host_url)
    send_statement(statement, settings)
    logger.info(
        '%s completed hunt, %s. sending statement to Wax', email, hunt.name)


def send_statement(statement, settings):
    return requests.post(
        'https://{}.waxlrs.com/TCAPI/statements'.format(settings.wax_site),
        headers={
            "Content-Type": "application/json",
            "x-experience-api-version": "1.0.0"
        },
        data=json.dumps(statement),
        auth=(settings.login, settings.password)
    )
