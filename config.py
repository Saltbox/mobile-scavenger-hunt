import os

ENV_VAR = {
    var: os.environ[var]
    for var in [
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL'
    ] if var in os.environ
}
