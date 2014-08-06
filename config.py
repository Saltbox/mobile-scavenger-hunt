import os

ENV_VAR = {
    var: os.environ.get(var)
    for var in [
        'DEBUG',
        'SECRET_KEY',
        'USERNAME',
        'PASSWORD',
        'WAX_LOGIN',
        'WAX_PASSWORD',
        'WAX_SITE'
    ]
}
ENV_VAR['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']