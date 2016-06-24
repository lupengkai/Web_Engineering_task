from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User


class LoginForm(Form):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('保持登陆')
    submit = SubmitField('登陆')


class RegistrationForm(Form):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                                                         '用户名只能包含字母，数字，和下划线。')])
    role =  RadioField('角色', choices=[('student', '学生'), ('teacher', '老师')], validators=[DataRequired()])
    password = PasswordField('密码',
                             validators=[DataRequired(), EqualTo('password2', message='两次密码输入必须一致。')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField('注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已经被注册')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用')


class ChangePasswordForm(Form):
    old_password = PasswordField('旧密码', validators=[DataRequired()])
    password = PasswordField('新密码',
                             validators=[DataRequired(), EqualTo('password2', message='两次密码输入必须一致。')])
    password2 = PasswordField('确认新密码', validators=[DataRequired()])
    submit = SubmitField('修改密码')


class PasswordResetRequestForm(Form):
    email = email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('重置密码')


class PasswordResetForm(Form):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('密码',
                             validators=[DataRequired(), EqualTo('password2', message='两次密码输入必须一致。')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField('重置密码')

    def validate_email(self, field):  # function name is used.
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('未知的邮箱')
