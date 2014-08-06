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
        'WAX_SITE',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL'
    ]
}
