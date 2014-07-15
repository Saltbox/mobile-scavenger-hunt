from behave import *   # noqa
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, \
    WebDriverException, TimeoutException

from hunt import db
from models import Hunt, Participant, Item

import uuid
import time


def email():
    return "{}@example.com".format(uuid.uuid4().hex)


def randomtext():
    return uuid.uuid4().hex


@given('a hunt')
def create_hunt(context):
    hunt = Hunt()
    hunt.name = uuid.uuid4().hex

    participant = Participant()
    participant.email = email()
    db.session.add(participant)
    db.session.commit()

    hunt.participants = [participant]

    item = Item()
    item.name = uuid.uuid4().hex
    db.session.add(item)
    db.session.commit()

    hunt.items = [item]
    hunt.admin_id = 1  # fresh db for each scenario

    db.session.add(hunt)
    db.session.commit()

    context.hunt = hunt


step_matcher('parse')


@when(u'waiting for the page to load')
def wait_for_page_change(context):
    def ready_state_complete(d):
        return d.execute_script('return document.readyState') == 'complete'

    # Wait a few seconds for js accordions and things to settle
    time.sleep(5)

    try:
        WebDriverWait(context.browser, 30)\
            .until(ready_state_complete)
    except TimeoutException:
        d.execute_script('window.stop();')
    except WebDriverException:
        pass


@given('I am logged in')
def logged_in(context):
    context.browser.get(context.root)
    email_field = context.browser.find_element_by_name('username')
    email_field.send_keys(context.admin.email)

    password_field = context.browser.find_element_by_name('password')
    password_field.send_keys(context.admin.password)

    context.browser.find_element_by_css_selector('button[type=submit]').click()
    wait_for_page_change(context)


@given('I am on the "{pagepath}" page')
def visit_page(context, pagepath):
    context.browser.get('{}/{}'.format(context.root, pagepath))


step_matcher('re')


@when("clicking the hunt's name")
def click_hunt_name(context):
    click_the_button(context, context.hunt.name)


@when(u'clicking the "(?P<value>[^"]+)" button')
def click_the_button(context, value):
    paths = [
        '//input[normalize-space(@value)="%s"]',
        '//a[contains(normalize-space(text()),"%s")]',
        '//a[contains(normalize-space(string(.)),"%s")]',
        '//button[normalize-space(text())="%s"]',
        '//button[contains(normalize-space(string(.)),"%s")]',
        '//button/span[contains(normalize-space(string(.)),"%s")]'
    ]

    failures = []

    for xpath in paths:
        try:
            context.browser.find_element_by_xpath(xpath % value).click()
        except Exception, e:
            failures.append(e)
        else:
            failures = []
            break

    assert not failures, 'Failed to find the button labeled "{}": {}'.format(
        value, failures)


step_matcher('parse')


@when('clicking the "{name}" radio button with value "{value}"')
def click_radio(context, name, value):
    context.browser.find_element_by_css_selector(
        'input[name={}][value={}]'.format(name, value)).click()


@when('filling out the "{fieldname}" field')
def fill_out_field(context, fieldname):
    field = context.browser.find_element_by_name(fieldname)
    value = uuid.uuid4().hex
    setattr(context, fieldname, value)
    field.send_keys(value)


@when('entering {num:d} participant emails')
def participant_emails(context, num):
    field = context.browser.find_element_by_css_selector('input[type=email]')
    for _ in xrange(num):
        context.emails = getattr(context, 'emails', [])
        context.emails.append(email())
        field.send_keys(context.emails[-1])
        context.browser.find_element_by_css_selector(
            "#add-participant").click()


@when('entering {num:d} item names')
def item_names(context, num):
    field = context.browser.find_element_by_css_selector(
        'input#items-template')
    for _ in xrange(num):
        context.items = getattr(context, 'items', [])
        context.items.append(uuid.uuid4().hex)
        field.send_keys(context.items[-1])
        context.browser.find_element_by_css_selector("#add-item").click()

fake_data = {
    'participant': email,
    'item': randomtext
}


step_matcher('re')


@when('adding (?:a|an) (?P<form_item>[^"]+)')
def add_form_item(context, form_item):
    context.added = getattr(context, 'added', {})
    data = fake_data[form_item]()
    context.added[form_item] = getattr(context.added, form_item, [])
    context.added[form_item].append(data)

    form = context.browser.find_element_by_css_selector(
        '#more-{}s'.format(form_item)).send_keys(data)
    btn = context.browser.find_element_by_css_selector(
        '#more-{}s-btn'.format(form_item)).click()


step_matcher('parse')


@when('revisiting the "{path}" page')
def revisit_path(context, path):
    visit_page(context, path)


def click_selector(context, selector):
    context.browser.find_element_by_css_selector(selector).click()


def send_keys(context, selector, data):
    context.browser.find_element_by_css_selector(selector).send_keys(data)


@when('changing the {msgtype} message')
def change_message(context, msgtype):
    click_selector(context, '.panel.{}'.format(msgtype))
    context.added = getattr(context, 'added', {})
    context.added[msgtype] = uuid.uuid4().hex
    send_keys(context, '#update-{}'.format(msgtype), context.added[msgtype])
    click_selector(context, 'html')  # blur triggers update


@then('I should be directed to the "{page_path}" page')
def directed_to(context, page_path):
    assert page_path in context.browser.current_url, \
        "Expected browser to be at the folowing url but is not: {}".format(
            page_path)


def missing_text_msg(text):
    return "Expected {} on the page but did not find it".format(text)


@then('the email(s) should appear on the page')
def participant_emails_appear(context):
    for email in context.emails:
        assert email in context.browser.page_source, missing_text_msg(email)


@then('the item should appear on the page')
def item_names_appear(context):
    for item in context.items:
        assert item in context.browser.page_source, missing_text_msg(item)


@then('the "{selector_name}" {inputtype} should be displayed')
def input_selector_appears(context, selector_name, inputtype):
    assert context.browser.find_element_by_name(selector_name).is_displayed(),\
        "Expected the {} {} to be displayed but is not".format(
            selector_name, inputtype)


@then('the hunt name should appear on the page')
def hunt_name_appears(context):
    assert context.name in context.browser.page_source, \
        missing_text_msg(context.hunt)


@then('the text, "{text}", appears')
def text_appears(context, text):
    assert text in context.browser.page_source, missing_text_msg(text)


@then('the added data should appear on the page')
def added_data_present(context):
    for typ in context.added:
        for obj in context.added[typ]:
            assert obj in context.browser.page_source, \
                missing_text_msg(obj)
