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


def begin_hunt_statement(actor, hunt, host_url):
    return {
        "actor": actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/registered",
            "display": {
                "en-US": "registered"
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
            "x-experience-api-version": "1.0.0"
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


def get_state_response(params, settings):
    return requests.get(
        'https://{}.waxlrs.com/TCAPI/activities/state'.format(
            settings.wax_site),
        params=params,
        headers={
            "x-experience-api-version": "1.0.0"
        },
        auth=(settings.login, settings.password)
    )


def default_params(email, hunt_id, host_url):
    return {
        'agent': json.dumps(make_agent(email)),
        'activityId': "{}/hunts/{}".format(host_url, hunt_id),
        'stateId': 'hunt_progress'
    }


def prepare_initial_state(item_id, required_ids, num_items):
    return {
        'found_ids': [item_id],
        'num_found': 0,
        'required_ids': required_ids,
        'total_items': num_items
    }


def make_agent(email):
    return {"mbox": "mailto:{}".format(email)}


def update_state(response, email, hunt, item, params, db):
    def update(state, params, setting):
        item_id = int(item_id)
        if item_id not in state['found_ids']:
            state['found_ids'].append(item_id)
            state['num_found'] += 1
        return state

    report = {}
    state = None
    actor = make_agent(email)
    if response.status_code == 404:
        logger.info(
            'No state exists for %s on this hunt, %s'
            ' Beginning new state document.', email, hunt.name)

        items = get_items(db, hunt.hunt_id)
        required_ids = [
            item.item_id for item in items if item.required]

        state = prepare_initial_state(
            int(item.item_id), required_ids, len(items))
        put_state(json.dumps(state), params, admin_settings)
        report['state_created'] = True
    elif response.status_code == 200:
        state = response.json()
        if item.item_id not in state['found_ids']:
            logger.info(
                'Updating state api for %s on hunt, %s.', email, hunt.name)
            state = update(state, params, admin_settings)
            report['state_updated'] = True

            post_state(state, params, admin_settings)

            required_found = set(state['found_ids']) == set(state['required_ids'])
            complete = state['num_found'] >= hunt.num_required and required_found
            report['hunt_completed'] = complete
    else:
        # todo: get worker to retry
        logger.warning(
            "An unexpected error occurred retrieving information from"
            " the state api using params, %s, with status, %s, and"
            " response: \n%s", params, response.status_code,
            response.text)
    return report, state


# send statements based off of found state
def send_statements(
        state, state_report, settings, email, hunt, host_url, item=None):
    statements = []
    actor = make_agent(email)
    if state_report.get('state_created'):
        statements.append(begin_hunt_statement(actor, hunt, host_url))
        logger.debug(
            '%s began hunt. sending statement to Wax', email)
    if state_report.get('state_updated'):
        statements.append(found_item_statement(actor, hunt, item, host_url))
        logger.debug(
            '%s found hunt item. sending statement to Wax', email)
    if state_report.get('hunt_completed'):
        statements.append(completed_hunt_statement(actor, hunt, host_url))
        logger.debug(
            '%s completed hunt. sending statement to Wax', email)

    if statements:
        return requests.post(
            'https://{}.waxlrs.com/TCAPI/statements'.format(settings.wax_site),
            headers={
                "Content-Type": "application/json",
                "x-experience-api-version": "1.0.0"
            },
            data=json.dumps(statements),
            auth=(settings.login, settings.password)
        )
