from flask import request, render_template, session, redirect, url_for, current_app, abort, flash, make_response
from flask.ext.login import login_required, current_user
from .forms import EditProfileForm, EditProfileAdminForm, EditCarpoolInfoForm, CommentForm
from app.decorators import admin_required, permission_required
from . import main
from .. import db
from ..models import User, Role, Permission, Group, Comment, Application
from ..email import send_email
from datetime import datetime, timedelta


@main.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)

    show_ride = False

    show_ride = bool(request.cookies.get('show_ride', ''))

    if show_ride:

        query = Group.get_ride_group_query()
    else:

        query = Group.get_carpool_group_query()

    pagination = query.paginate(page, per_page=current_app.config['GROUPS_PER_PAGE'], error_out=False)

    groups = pagination.items
    return render_template('index.html', groups=groups,
                           show_ride=show_ride, pagination=pagination)


@main.route('/show-carpool')
def show_carpool():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_ride', '', max_age=30 * 24 * 60 * 60)
    return resp


@main.route('/show-ride')
def show_ride():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_ride', '1', max_age=30 * 24 * 60 * 60)
    return resp


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return render_template('user.html', user=user)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.grade = form.grade.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('资料已更新！')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.grade.data = current_user.grade
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)  #
        user.name = form.name.data
        user.grade = form.grade.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('资料已更新！')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.grade.data = user.grade
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/deliver-carpool', methods=['GET', 'POST'])
@login_required
def deliver_carpool():
    form = EditCarpoolInfoForm()
    if form.validate_on_submit():
        group = Group(description=form.description.data, start_time=(form.start_time.data - timedelta(hours=8)),
                      start_place=form.start_place.data,
                      end_place=form.end_place.data, people_amount=form.people_amount.data)
        group.build_user = current_user._get_current_object()
        group.users.append(group.build_user)

        db.session.add(group)
        db.session.commit()
        flash('发布成功，请确保个人信息完善！')
        return redirect(url_for('main.carpool', id=group.id))
    return render_template('deliver_carpool.html', form=form)


@main.route('/carpool/<int:id>', methods=['GET', 'POST'])
def carpool(id):
    group = Group.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, group=group, author=current_user._get_current_object())
        db.session.add(comment)
        flash('您的评论已被提交')
        return redirect(url_for('.carpool', id=group.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (group.comments.count() - 1) // \
               current_app.config['COMMENTS_PER_PAGE'] + 1

    pagination = group.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items



    return render_template('carpool.html', group=group, comments=comments, form=form,pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    group = Group.query.get_or_404(id)
    if current_user != group.build_user and \
            not current_user.is_administrator():
        abort(403)
    form = EditCarpoolInfoForm()
    if form.validate_on_submit():
        group.description = form.description.data
        group.start_time = form.start_time.data
        group.start_place = form.start_place.data
        group.end_place = form.end_place.data
        group.people_amount = form.people_amount.data

        db.session.add(group)
        flash('信息已修改！')
        return redirect(url_for('main.carpool', id=group.id))

    form.description.data = group.description
    form.start_time.data = group.start_time + timedelta(hours=8)
    form.start_place.data = group.start_place
    form.end_place.data = group.end_place
    form.people_amount.data = group.people_amount

    return render_template('edit_carpool.html', form=form)


@main.route('/delete-comment/<int:id>')
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    group = comment.group
    if comment.author == current_user or current_user.is_administrator():
        db.session.delete(comment)
        flash('评论已被删除')
    return redirect(url_for('main.carpool', id=group.id))


@main.route('/delete-carpool/<int:id>')
@login_required
def delete_carpool(id):
    group = Group.query.get_or_404(id)
    if group.build_user == current_user or current_user.is_administrator():
        comments = group.comments
        users = group.users
        applications = group.applications
        for comment in comments:
            db.session.delete(comment)
        for user in users:
            group.users.remove(user)
        for application in applications:
            db.session.delete(application)
        db.session.delete(group)
        flash('拼车信息已被删除')
    return redirect(url_for('main.index'))


@main.route('/apply/<int:group_id>')
@login_required
def apply(group_id):
    group = Group.query.get_or_404(group_id)

    applicants = []

    for application in group.applications:
        if not application.is_passed:
            applicants.append(application.applicant)

    if current_user in group.users:
        flash('您已经是组内成员，请勿重复申请加入！')
    elif current_user in applicants:
        flash('您已提交申请，请勿重复提交，请耐心等待回复！')
    else:
        application = Application(applicant=current_user._get_current_object(), group=group)
        apply = current_user.username + '申请加入'
        comment = Comment(body=apply, group=group, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        db.session.add(application)
        flash('申请已提交!')
    return redirect(url_for('main.carpool', id=group_id))


@main.route('/approve/<int:application_id>')
@login_required
def approve(application_id):
    application = Application.query.get_or_404(application_id)

    if application.applicant in application.group.users:
        flash('成员已在组中，不需重复添加！')
        return redirect(url_for('main.applies_received'))

    if current_user != application.group.build_user:
        abort(403)
    else:
        application.is_passed = True
        application.group.users.append(application.applicant)
        reply = '已批准' + application.applicant.username + '加入'
        comment = Comment(body=reply, group=application.group, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        db.session.add(application)

        flash('已批准')

        return redirect(url_for('main.applies_received'))


@main.route('/applies-received')
@login_required
def applies_received():
    applications = Application.get_applies(current_user)

    return render_template('applies_received.html', applications=applications)


@main.route('/applies-raised')
@login_required
def applies_raised():
    applications = current_user.applications
    return render_template('applies_raised.html', applications=applications)


@main.route('/quit/<int:group_id>')
@login_required
def quit(group_id):
    group = Group.query.get_or_404(group_id)
    if not current_user in group.users:
        flash('您不是本组成员，无法退出！')
    elif current_user == group.build_user:
        flash('您是发起人不能退出！')
    else:
        group.users.remove(current_user._get_current_object())
        db.session.commit()
    return redirect(url_for('main.carpool', id=group_id))


@main.route('/carpools')
@login_required
def carpools():
    user = User.query.filter_by(username=current_user.username).first()
    if user is None:
        abort(404)
    groups = user.groups_builded.order_by(Group.timestamp.desc())

    return render_template('carpools.html', groups=groups)

