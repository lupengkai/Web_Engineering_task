from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField,DateTimeField, IntegerField
from wtforms.validators import DataRequired, Length, Email, Regexp, ValidationError
from flask.ext.pagedown.fields import PageDownField

from app.models import Role, User


class EditProfileForm(Form):
    name = StringField('真实姓名', validators=[Length(0, 64)])
    grade = SelectField('年级', choices=[('大一', '大一'), ('大二', '大二'), ('大三', '大三'), ('大四', '大四')])
    about_me = TextAreaField('关于我')
    submit= SubmitField('提交')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Usernames must have only letters, '
                                              'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    grade = SelectField('年级', choices=[('大一', '大一'), ('大二', '大二'), ('大三', '大三'), ('大四', '大四')])
    about_me = TextAreaField('关于我')
    submit = SubmitField('提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class EditCarpoolInfoForm(Form):
    start_time = DateTimeField('出发时间', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    start_place = StringField('起点', validators=[DataRequired()])
    end_place = StringField('终点', validators=[DataRequired()])

    people_amount = IntegerField('预期人数', validators=[DataRequired(), ])

    description = PageDownField('详细描述', validators=[DataRequired()])
    submit = SubmitField('提交')


class CommentForm(Form):
    body = PageDownField('输入你的评论', validators=[DataRequired()])
    submit = SubmitField('提交')