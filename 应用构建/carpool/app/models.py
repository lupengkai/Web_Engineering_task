from random import randint, seed

from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from datetime import datetime
import hashlib
from markdown import markdown
import bleach


class Permission:
    DELIVER_CARPOOL = 0X01
    JOIN_CARPOOL = 0X02

    GIVERIDE = 0X04
    TAKERIDE = 0X08

    ADMINISTER = 0Xff


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permission = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'student': Permission.DELIVER_CARPOOL | Permission.JOIN_CARPOOL | Permission.TAKERIDE,
            'teacher': Permission.GIVERIDE,
            'administrator': 0xff
        }

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permission = roles[r]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


join = db.Table('join',
                db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
                db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
                )


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    name = db.Column(db.String(64))
    grade = db.Column(db.Integer)
    about_me = db.Column(db.Text)
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    groups_joinded = db.relationship('Group', secondary=join, backref=db.backref('users', lazy='dynamic'),
                                     lazy='dynamic')

    groups_builded = db.relationship('Group', backref='build_user', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    applications = db.relationship('Application', backref='applicant', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['ADMIN']:
                self.role = Role.query.filter_by(permission=0xff).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def reset_password(self, token, password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.password = password
        db.session.add(self)
        return True

    def can(self, permission):
        return self.role is not None and \
               (self.role.permission & permission) == permission

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def is_student(self):
        return self.can(Permission.DELIVER_CARPOOL | Permission.JOIN_CARPOOL | Permission.TAKERIDE)

    def is_teacher(self):
        return self.can(Permission.GIVERIDE)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://cdn.v2ex.com/gravatar'
        else:
            url = 'http://cdn.v2ex.com/gravatar/'
        hash = self.avatar_hash or hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating
        )

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get[data['id']]

    def __repr__(self):
        return '<User %r>' % self.username


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class AnonymousUser(AnonymousUserMixin):
    def can(self, permission):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    description_html = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    start_place = db.Column(db.String(64))
    end_place = db.Column(db.String(64))
    people_amount = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    builder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='group', lazy='dynamic')
    applications = db.relationship('Application', backref='group', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']

        target.description_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    @staticmethod
    def get_ride_group_query():
        id_list = []

        teacher = Role.query.filter_by(name='teacher').first()

        ids = db.session.query(User.id).filter_by(role=teacher).all()

        for id, in ids:
            id_list.append(id)

        ride_groups_query = Group.query.filter(Group.builder_id.in_(id_list)).order_by(
            Group.start_time.desc())

        return ride_groups_query

    @staticmethod
    def get_carpool_group_query():
        id_list = []
        student = Role.query.filter_by(name='student').first()

        ids = db.session.query(User.id).filter_by(role=student).all()

        for id, in ids:
            id_list.append(id)

        carpool_groups_query = Group.query.filter(Group.builder_id.in_(id_list)).order_by(
            Group.start_time.desc())

        return carpool_groups_query


db.event.listen(Group.description, 'set', Group.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    is_passed = db.Column(db.Boolean, default=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    @staticmethod
    def get_applies(user):
        ids = db.session.query(Group.id).filter_by(build_user=user).all()
        id_list=[]

        for id, in ids:
            id_list.append(id)

        applications = db.session.query(Application).filter(Application.group_id.in_(id_list)).order_by(
             Application.timestamp.desc()).all()


        return applications
