from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.assets import Environment, Bundle


app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)


logger = app.logger


################ ASSETS MANAGEMENT ################
# right now just minification and concatenation

assets = Environment(app)
assets.url = app.static_url_path

css_all = Bundle(
    'css/*.css',
    filters='cssmin',
    output='dist/css_all.css'
)

my_js = Bundle(
    'js/*.js',
    filters='jsmin',
    output='dist/my_js.js'
)

vendor_js = Bundle(
    'js/vendor/*.js',
    output='dist/vendor_js.js'
)

assets.register('css_all', css_all)
assets.register('my_js', my_js)

assets.add(css_all)
assets.add(my_js)

my_js.build()
css_all.build()


from views import *

if __name__ == '__main__':
    app.run()
