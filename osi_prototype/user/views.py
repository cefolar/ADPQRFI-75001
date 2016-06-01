# -*- coding: utf-8 -*-
"""User views."""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from osi_prototype.assets import uploads
from osi_prototype.database import db
from osi_prototype.user.forms import EditForm, MessageForm
from osi_prototype.user.models import Message, User

blueprint = Blueprint('user', __name__, static_folder='../static')


@blueprint.route('/profile/')
@login_required
def profile():
    """Show profile dashboard page."""
    profile_photo = None
    if current_user.profile_photo:
        profile_photo = uploads.url(current_user.profile_photo)

    return render_template('user/profile.html',
                           profile_photo=profile_photo)


@blueprint.route('/profile/edit', methods=('POST',))
@login_required
def edit_profile():
    """Show profile dashboard page."""
    form = EditForm(request.form)
    if form.validate_on_submit():
        updates = {k: v for k, v in form.data.items()
                   if k in request.form}
        current_user.update(commit=True, **updates)
        return json.dumps({'success': True})
    else:
        errors = list(form.errors.values())
        message = 'server error'
        # Get first error.
        for field_errors in errors:
            for error in field_errors:
                message = error
                break
        return json.dumps({'success': False, 'message': message})


@blueprint.route('/messages/')
@login_required
def messages():
    """Show private messaging page."""
    threads = current_user.threads_involved_in()
    if current_user.user_type == 'parent':
        users = User.query.filter_by(user_type='agent')
    else:
        users = User.query.filter_by(user_type='parent')
    return render_template('user/threads.html', threads=threads, users=users)


@blueprint.route('/messages/<to_username>', methods=['GET', 'POST'])
@login_required
def message_thread(to_username):
    """Show message thread page."""
    to_user = User.get_by_username(to_username, show_404=True)

    form = MessageForm(request.form, csrf_enabled=False)
    if form.validate_on_submit():
        Message.create(from_user=current_user,
                       to_user=to_user,
                       body=form.body.data,
                       is_unread=1)
        flash('Your message has been sent!', 'success')
    messages = current_user.messages_between(to_user)

    ordered_messages = messages.order_by(Message.created_at.desc()).all()
    rendered = render_template('user/messages.html',
                               messages=ordered_messages,
                               to_user=to_user,
                               form=form)

    # Update messages to this user as read.
    messages.filter_by(to_user_id=current_user.id).update({'is_unread': 0})
    db.session.commit()

    return rendered


@blueprint.route('/upload/', methods=['POST'])
@login_required
def upload():
    print(request.form)
    if 'photo' in request.files:
        filename = uploads.save(request.files['photo'])
        current_user.update(profile_photo=filename)
        print(filename)
        flash('Photo saved.', 'success')
    else:
        flash('Please provide a photo!', 'error')
    return redirect(url_for('.profile'))
