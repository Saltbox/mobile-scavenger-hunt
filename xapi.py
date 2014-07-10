from hunt import logger
from flask import request

import json
import requests


def hunt_activity_id(hunt_id):
    return "{}/hunts/{}".format(request.host_url, hunt_id)


def hunt_activity(hunt):
    return {
        "id": hunt_activity_id(hunt.hunt_id),
        "definition": {
            "type": "{}/activities/type/scavengerhunt".format(
                request.host_url),
            "name": hunt.name
        },
        "objectType": "Activity"
    }


def begin_hunt_statement(actor, hunt):
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
        "verb": {
            "id": "{}/verbs/found".format(request.host_url),
            "display": {
                "en-US": "found"
            }
        },
        "object": {
            "id": "{}/hunts/{}".format(request.host_url, hunt.hunt_id),
            "definition": {
                "type": "{}/activities/type/scavengerhunt".format(
                    request.host_url),
                "name": "found item {} from {}".format(item.name, hunt.name)
            },
            "objectType": "Activity"
        },
        "context": {
            "contextActivities": {
                "parent": hunt_activity(hunt)
            }
        }
    }


# participant found all required items but not all items
def found_all_required_statement(actor, hunt):
    return {
        'actor': actor,
        'verb': verb_completed(),
        "object": {
            #activity name suggestions?
            "id": "{}/activities/findallrequired/hunts/{}".format(
                request.host_url, hunt.hunt_id),
            "description": {
                "type": "{}/activities/type/scavengerhunt".format(
                    request.host_url),
                "name": "finding all required items for {}".format(hunt.name)
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
    response = requests.post(
        setting.endpoint,
        headers={
            "Content-Type": "application/json",
            "x-experience-api-version": "1.0.0"
        },
        data=json.dumps(statement),
        auth=(setting.login, setting.password)
    )
    logger.debug('statement response status: %s', response.status_code)
    return response


def put_state(data, params, setting):
    response = requests.put(
        'https://testsite.waxlrs.com/TCAPI/activities/state',
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )

    logger.debug('put state api respone: %s', response.status_code)
    logger.debug('response.text: %s', response.text)
    return response


def post_state(data, params, setting):
    response = requests.post(
        'https://testsite.waxlrs.com/TCAPI/activities/state',
        params=params,
        data=data,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )
    logger.debug('post state api respone: %s', response.status_code)
    logger.debug('response.text: %s', response.text)
    return response


def get_state_response(params, setting):
    response = requests.get(
        'https://testsite.waxlrs.com/TCAPI/activities/state',
        params=params,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(setting.login, setting.password)
    )
    logger.debug('get state api respone: %s', response.status_code)
    logger.debug('response.text: %s', response.text)
    return response


def default_params(email, hunt_id):
    return {
        'agent': make_agent(email),
        'activityId': "{}/hunts/{}".format(request.host_url, hunt_id),
        'stateId': 'hunt_progress'
    }

# no. just get rid of this
def initialize_state_doc(hunt_id, email, params, data, setting):
    params = params or default_params(email, hunt_id)
    put_state(data, params, setting)


def make_agent(email):
    return json.dumps({'mbox': 'mailto:{}'.format(email)})
