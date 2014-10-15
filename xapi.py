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
            "id": "http://adlnet.gov/expapi/verbs/registered",
            "display": {
                "en-US": "registered for"
            }
        },
        "object": hunt_activity(hunt, host_url)
    }


def verb_completed():
    return {
        "id": "http://adlnet.gov/expapi/verbs/completed",
        "display": {
            "en-US": "completed"
        }
    }


def found_item_statement(actor, hunt, item, host_url):
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
                "parent": hunt_activity(hunt, host_url)
            }
        }
    }


# participant found every item
def completed_hunt_statement(actor, hunt, host_url):
    return {
        'actor': actor,
        'verb': verb_completed(),
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


def get_state_response(params, settings):
    logger.info(
        'requesting state from the state api for site, %s', settings.wax_site)
    return requests.get(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site),
        params=params,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(settings.login, settings.password)
    )


def create_new_state(email, hunt, item_id, params, settings, items):
    logger.info(
        'No state exists for %s on this hunt, %s.'
        ' Beginning new state document.', email, hunt.name)

    required_ids = [
        item.item_id for item in items if item.required]

    state = {
        'found_ids': [int(item_id)],
        'num_found': 1,
        'required_ids': required_ids,
        'total_items': len(items)
    }
    put_state(json.dumps(state), params, settings)
    return state


def update_state(state, params, settings, item, email, hunt):
    logger.info(
        'Updating state document for %s on hunt, "%s".', email, hunt.name)
    item_id = int(item.item_id)
    state['found_ids'].append(item_id)
    state['num_found'] += 1

    post_state(json.dumps(state), params, settings)
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
