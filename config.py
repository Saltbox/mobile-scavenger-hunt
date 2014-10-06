import os

ENV_VAR = {
    var: os.environ.get(var)
    for var in [
        'DEBUG',
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL'
    ]
}
