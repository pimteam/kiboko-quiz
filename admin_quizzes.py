import functools, time, logging, sys

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.exceptions import abort

from quiz.auth import login_required, admin_login_required
from quiz.db import get_db

# See: https://stackoverflow.com/questions/54444776/how-can-i-break-up-a-flask-blueprint-into-multiple-files-within-a-subfolder answers to breakdown in subfolders

bp = Blueprint('admin_quizzes', __name__)

@bp.route('/admin/quiz/', methods=('GET', 'POST'))
@bp.route('/admin/quiz/<int:id>/', methods=('GET', 'POST'))	
@admin_login_required
def quiz(id = 0):
	db = get_db()
	
	if request.method == 'POST' and request.form['del'] == '1':		
		db.execute(
			'DELETE FROM quizzes WHERE id=?',
			(id, )
		)
		db.commit()
		return redirect(url_for('admin.index'))
	
	if request.method == 'POST':
		# add / edit quiz
		name = request.form['name']		
		description = request.form['description']
		randomize = request.form['randomize'] if 'randomize' in request.form else 0 
		pull_random = request.form['pull_random']
		randomize_answers = request.form['randomize_answers'] if "randomize_answers" in request.form else 0
		final_screen = request.form['final_screen']
		email_output = request.form['email_output']
		email_subject = request.form['email_subject']
		notify_email = request.form['notify_email'] if "notify_email" in request.form else 0
		single_page = request.form['single_page'] if "single_page" in request.form else 0
		require_login = request.form['require_login'] if "require_login" in request.form else 0
		notify_admin = request.form['notify_admin'] if "notify_admin" in request.form else 0
		notify_user = request.form['notify_user'] if "notify_user" in request.form else 0
		dont_store_data = request.form['dont_store_data'] if "dont_store_data" in request.form else 0
		times_to_take = request.form['times_to_take']
		no_ajax = request.form['no_ajax'] if "no_ajax" in request.form else 0
		no_alert_unanswered = request.form['no_alert_unanswered'] if "no_alert_unanswered" in request.form else 0

		# temporary initialize as blank
		advanced_settings = design_theme = ''		
		added_on = time.strftime('%A %B, %d %Y %H:%M:%S')
		require_text_captcha = 0
				
		error = None
		
		if not name:
			error = 'Name is required.'
		
		if id:
			if error is not None:
				flash(error)
			else:
				db.execute(
					"""UPDATE quizzes SET name=?, description=?, randomize=?, pull_random=?, randomize_answers=?, final_screen=?, single_page=?, require_login=?, 
					 notify_admin=?, dont_store_data=?, require_text_captcha=?, email_output=?, notify_user=?, notify_email=?, times_to_take=?, no_ajax=?,
					 no_alert_unanswered=?, advanced_settings=?, email_subject=?, design_theme=? WHERE id=?""",					
					(name, description, randomize, pull_random, randomize_answers, final_screen, single_page, require_login, notify_admin,
					dont_store_data, require_text_captcha, email_output, notify_user, notify_email, times_to_take, no_ajax, no_alert_unanswered,
					advanced_settings, email_subject, design_theme, id)
				)
				db.commit()
				return redirect(url_for('admin.index'))
		else:
			if error is not None:
				flash(error)
			else:	
				db.execute(
					"""INSERT INTO quizzes (name, description, randomize, pull_random, randomize_answers, final_screen, added_on, single_page, require_login, 
					 notify_admin, dont_store_data, require_text_captcha, email_output, notify_user, notify_email, times_to_take, no_ajax,
					 no_alert_unanswered, advanced_settings, email_subject, design_theme) 
					VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
					(name, description, randomize, pull_random, randomize_answers, final_screen, added_on, single_page, require_login, notify_admin,
					dont_store_data, require_text_captcha, email_output, notify_user, notify_email, times_to_take, no_ajax, no_alert_unanswered,
					advanced_settings, email_subject, design_theme)
				)
				db.commit()
				return redirect(url_for('admin.index'))
	
	# load quiz or a quiz form	
	quiz = None
	
	if id:	
		quiz = db.execute(
			"""SELECT tE.*, COUNT(tQ.id) as cnt_questions, COUNT(tT.id) as cnt_takings
			FROM quizzes tE LEFT JOIN questions tQ ON tE.id = tQ.quiz_id 
			LEFT JOIN takings tT ON tE.id = tT.quiz_id 
			WHERE tE.id=?""",
			(id,)
		).fetchone()	
		
	return render_template('admin/quiz.html', quiz = quiz) 
	# end quiz()