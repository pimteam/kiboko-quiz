import functools, time, logging, sys, pickle

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.exceptions import abort

from quiz.auth import login_required, admin_login_required
from quiz.db import get_db


# See: https://stackoverflow.com/questions/54444776/how-can-i-break-up-a-flask-blueprint-into-multiple-files-within-a-subfolder answers to breakdown in subfolders

bp = Blueprint('admin', __name__)

@bp.route('/admin/')
@admin_login_required
def index():
	db = get_db()
	quizzes = db.execute(
		"""SELECT tE.*, COUNT(DISTINCT tQ.id) as cnt_questions, COUNT(DISTINCT tT.id) as cnt_takings 
		FROM quizzes tE LEFT JOIN questions tQ ON tQ.quiz_id=tE.id 
		LEFT JOIN takings tT ON tT.quiz_id = tE.id
		GROUP BY tE.id
		ORDER BY tE.name"""
	).fetchall()
	
	return render_template('admin/index.html', quizzes = quizzes)

# Manage questions	
@bp.route('/admin/questions/<int:quiz_id>', methods=('GET', 'POST'))	
@admin_login_required
def questions(quiz_id):
	db = get_db()
	# select quiz
	quiz = db.execute(
		'SELECT * FROM quizzes WHERE id=?',
		(quiz_id,)
	).fetchone()
	
	if quiz is None:
		return "No such quiz"
		
	# delete question
	if request.args.get('del'):
		question_id = request.args.get('del')
		
		db.execute(
		   """DELETE FROM answers WHERE question_id=?""",
		   (question_id,)
		)
		db.commit()		
		
		db.execute(
		   """DELETE FROM questions WHERE id=?""",
		   (question_id,)
		)
		db.commit()
		return redirect(url_for('admin.questions', quiz_id = quiz_id))
	
	# select questions	
	questions = db.execute(
		"""SELECT tQ.*, COUNT(tA.id) as cnt_answers 
			FROM questions tQ LEFT JOIN answers tA ON tA.question_id = tQ.id 
			WHERE tQ.quiz_id=? GROUP BY tQ.id ORDER BY tQ.sort_order, tQ.id""",
		(quiz_id,)
	).fetchall()
	
	return render_template('admin/questions.html', quiz = quiz, questions = questions, cls = '') 
# end questions	

# add / edit question
@bp.route('/admin/question/<int:quiz_id>/<int:id>', methods=('GET', 'POST'))	
@bp.route('/admin/question/<int:quiz_id>', methods=('GET', 'POST'))	
def question(quiz_id, id = 0):
	db = get_db()
	
	quiz = db.execute(
		'SELECT * FROM quizzes WHERE id=?',
		(quiz_id,)
	).fetchone()
	
	# add/save question
	if request.method == 'POST':
		# prepare variables
		question = request.form['question'] or ''
		answer_type = request.form['answer_type'] or 'radio'
		is_required = 1 if "is_required" in request.form else 0
		is_inactive = 1 if "is_inacitve" in request.form else 0
		is_survey = 1 if "is_survey" in request.form else 0				
		feedback = request.form['feedback'] or ''		
		num_columns = 1 #temp
		
		if id:
			db.execute(
				"""UPDATE questions 
				SET question=?, answer_type=?, sort_order=?, is_required=?, feedback=?, is_inactive=?, is_survey=?, num_columns=?
				WHERE id=?""",
				(question, answer_type, 1, is_required, feedback, is_inactive, is_survey, num_columns, id,)
			)
			db.commit()		
			
			# update or delete existing answers
			answers = db.execute(
				"""SELECT id FROM answers WHERE question_id=?""",
				(id,)
			).fetchall()
			
			for answer in answers:
				ans_text = request.form['answer_' + str(answer['id'])]
				# print(str(answer['id']) + ": " + ans_text, file=sys.stderr)	
				if ans_text == '':
					#print("delete "  + str(answer['id']) + ": " + ans_text, file=sys.stderr)		
					# delete answer
					db.execute(
						"""DELETE FROM answers WHERE id=?""",
						(answer['id'],)
					)
					db.commit()
				else:
					# update					
					correct = 0 if "correct_"+str(answer['id']) not in request.form else 1
					points = request.form['points_' + str(answer['id'])]
					
					if ans_text != '':				
						# print("insert "  +  ans_text, file=sys.stderr)			
						db.execute("""	UPDATE answers SET answer=?, correct=?, points=?, sort_order=1 WHERE id=?""",
							(ans_text, correct, points, answer['id'])					
						)
						db.commit()
			
			question_id = id
		else:
			db.execute(
				"""INSERT INTO questions (quiz_id, question, answer_type, sort_order, is_required, feedback, is_inactive, is_survey, num_columns)
				VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
				(quiz_id, question, answer_type, 1, is_required, feedback, is_inactive, is_survey, num_columns)
			)
			db.commit()
			
			question_id = db.execute('SELECT last_insert_rowid() as last_id').fetchone()
			question_id = question_id['last_id']
			
		# add new answer if any
		for answer, points, correct in zip(request.form.getlist('answer'),
													  request.form.getlist('points'),
													  request.form.getlist('points')):
			
			 if answer != '':											  				
				 db.execute(
				 	"""INSERT INTO answers (question_id, answer, correct, points, sort_order)
							 	VALUES (?, ?, ?, ?, ?)""",
					(question_id, answer, correct, points, 1)			 	
				 )
				 db.commit()
			 
			 return redirect(url_for('admin.questions', quiz_id = quiz_id))
	if id:
		question = db.execute(
			'SELECT * FROM questions WHERE id=?',
			(id, )
		).fetchone()
		
		answers = db.execute(
				"""SELECT * FROM answers WHERE question_id=?""",
				(id,)
			).fetchall()
		count_answers = len(answers)	
	else:
		question = None	
		answers = None
		count_answers = 0
		
	return render_template('admin/question.html', quiz = quiz, question = question, answers=answers, count_answers = count_answers)

# global settings	
@bp.route('/admin/settings', methods=('GET', 'POST'))	
@admin_login_required
def settings():
	db = get_db()
	if request.form:
		# email sender
		db.execute("INSERT OR REPLACE INTO options (option_key, option_value) VALUES ('email_sender',?)", (request.form['sender'],))
		db.commit()
		
		db.execute("INSERT OR REPLACE INTO options (option_key, option_value) VALUES ('email_sender_name',?)", (request.form['sender_name'],))
		db.commit()
		
		# email config as serialized dict
		email_config = {
			'server' : request.form['mail_server'],
			'port' : request.form['mail_port'],
			'username' : request.form['mail_username'],
			'pass' : request.form['mail_pass'],
			'use_tls' : 1 if 'mail_use_tls' in request.form else 0,
			'use_ssl' :  1 if 'mail_use_ssl' in request.form else 0,
		}
		email_config = pickle.dumps(email_config)
		db.execute("INSERT OR REPLACE INTO options (option_key, option_value) VALUES ('email_config',?)", (email_config,))
		db.commit()
	
	sender = db.execute("SELECT option_value FROM options WHERE option_key = 'email_sender' ").fetchone()
	sender_name = db.execute("SELECT option_value FROM options WHERE option_key = 'email_sender_name' ").fetchone()
	
	email_config = db.execute("SELECT option_value FROM options WHERE option_key = 'email_config' ").fetchone()
	email_config = pickle.loads(email_config['option_value']) if email_config else None
	return render_template('admin/settings.html', sender = sender, sender_name = sender_name, email_config = email_config)	
	
	
	
	