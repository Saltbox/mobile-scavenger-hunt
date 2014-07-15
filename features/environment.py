from hunt import db, app
from models import Admin

from selenium import webdriver

import uuid


def before_feature(context, feature):
    app.config['TESTING'] = True
    context.app = app.test_client()
    context.root = 'localhost:5000'


def before_scenario(context, scenario):
    db.drop_all()
    db.create_all()
    admin = Admin()
    admin.first_name = uuid.uuid4().hex
    admin.last_name = uuid.uuid4().hex
    admin.email = "{}@example.com".format(uuid.uuid4().hex)
    admin.password = uuid.uuid4().hex
    db.session.add(admin)
    db.session.commit()
    context.admin = admin
    print context.admin.email, context.admin.password


def before_tag(context, tag):
    if tag == 'browser':
        browser = getattr(context, 'browser', 'chrome')

        if browser == 'chrome':
            context.browser = webdriver.Chrome()
        elif browser == 'firefox':
            context.browser = webdriver.Firefox()
        else:
            context.browser = webdriver.Remote(
                context.browser,
                webdriver.DesiredCapabilities.FIREFOX.copy())


def after_scenario(context, scenario):
    if hasattr(context, 'browser') and hasattr(context.browser, 'quit'):
        context.browser.quit()
