from flask import render_template, redirect, request, url_for, flash, abort,current_app
from flask.ext.login import login_user, logout_user, login_required
from . import auth
from ..models import User,Role
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm
from .. import db
from ..email import send_email
from flask.ext.login import current_user


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()  # 调用init方法，再把数据库中的数据赋上
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)  # whether remember
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or password.')

    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You hava been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data,
                    role=Role.query.filter_by(name=form.role.data).first()
                    )
        if user.email ==  current_app.config['ADMIN']:
            user.role = Role.query.filter_by(permission=0xff).first()
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
        flash('验证邮件已发送至邮箱。')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to by email.')
    return redirect(url_for('main.index'))


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/change-password', methods=['POST', 'GET'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been updated!')
            return redirect(url_for('main.index'))
        else:
            flash('Invaid password.')
    return render_template('auth/change_password.html', form=form)


@auth.route('/reset', methods=['POST', 'GET'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect('main.index')
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_confirmation_token()
            send_email(user.email, 'Reset your password', 'auth/email/reset_password', user=user, token=token,
                       next=request.args.get('next'))
            flash('An email with instructions to reset your password has been '
                  'sent to you.')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect('main.index')
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('The email has not registered')
            return redirect(url_for('auth.register'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been reset')
            return redirect(url_for('auth.login'))
        else:
            flash('Your reset password link is invalid or has expired.')
            return redirect(url_for('auth.password_reset_request'))
    return render_template('auth/reset_password.html', form=form)
