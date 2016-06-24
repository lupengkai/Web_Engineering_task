import os
from app import create_app, db
from app.models import User, Role,Group,Comment
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

app = create_app('production')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Group=Group, Comment=Comment)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def deploy():
    from flask.ext.migrate import upgrade
    from app.models import Role, User

    upgrade()

    Role.insert_roles()



if __name__ == '__main__':
    manager.run()


# if __name__ == '__main__':
#     app.run(debug=True)