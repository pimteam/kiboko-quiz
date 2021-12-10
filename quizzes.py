import functools, sys, pickle

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from flask_mail import Mail, Message

from flask_wtf.csrf import CSRFProtect

from werkzeug.exceptions import abort

from quiz.auth import login_required
from quiz.db import get_db
from datetime import datetime, date

from quiz.helpers import *

bp = Blueprint('quizzes', __name__)

@bp.route('/')
def index():
	db = get_db()
	quizzes = db.execute(
		'SELECT * FROM quizzes ORDER BY name'
	).fetchall()
	
	return render_template('quizzes/index.html', quizzes = quizzes)
	
@bp.route('/quiz/<int:id>', methods=('GET', 'POST'))	
def quiz(id):
	db = get_db()	

	# select quiz
	quiz = db.execute(
		""" SELECT * FROM quizzes WHERE id=?""",
		(id,)
	).fetchone()
	
	# select questions
	orderby = "RANDOM()" if quiz['randomize'] == 1 or quiz['pull_random'] > 0 else "sort_order, id"
	limit = f"LIMIT {quiz['pull_random']}" if quiz['pull_random'] > 0 else ''
	
	questions = db.execute(
		""" SELECT * FROM questions WHERE quiz_id=? AND is_inactive=0 ORDER BY %s %s """ % (orderby, limit),
		(id,)
		).fetchall()	
	
	# turn to dictionary	
	questions = [dict(row) for row in questions]	
	
	qids = ['0']
	
	for question in questions:
		qids.append(str(question['id']))	
	
	qid_sql = ', '.join(qids)	
	
	answer_orderby = 'sort_order, id' if not quiz['randomize_answers'] else 'RANDOM()';
		
	# match choices to questions
	answers = db.execute(
		f"SELECT * FROM answers WHERE question_id IN ({qid_sql}) ORDER BY {answer_orderby}"
	).fetchall()	
	
	for i, question in enumerate(questions):
		#print("question ID: " + str(question['id']) + ' ' + str(i) , file = sys.stderr)
		question_answers = []
		
		for answer in answers:			
			if answer['question_id'] == question['id']:			
				question_answers.append(answer)
		
		questions[i]['answers'] = question_answers		
		
	# text captcha?	
	text_captcha = ''
	if quiz['require_text_captcha']:
		text_captcha = generate_captcha()
		textcaptca_style = "style='display:none;'" if quiz['single_page'] else ''	
		text_captcha = f"<div id='TextCaptcha' {textcaptca_style}>{text_captcha}</div>";		
		if request.form['complete']:
			if not verify_captcha(request.form['text_captcha_question'], request.form['text_captcha_answer']): 
				return 'CAPTCHA:::Wrong answer to the verification question.'	
				
	# submit quiz
	if 'action' in request.form and request.form['action'] == 'show_exam_result':
		qids = []
		aids = []
		#print(request.form['question_ids[]'], file=sys.stderr)
		for question_id in request.form.getlist('question_ids[]'):
			qids.append(question_id)
		for answer_id in request.form.getlist('answer_ids[]'):
			aids.append(answer_id)
		
		qid_sql = (',').join(qids)
		aid_sql = (',').join(aids)
			
		# select questions and answers, then reorder them accordingly to the POST order
		questions = db.execute(
			"SELECT * FROM questions WHERE id IN (" + qid_sql + ") ",			
		).fetchall()	
		
		answers = db.execute(
			"SELECT * FROM answers WHERE id IN (" + aid_sql + ") ",			
		).fetchall()	
		
		# small helper for the below reordering		
		def search(id, items):
			#print(id, file=sys.stderr)
			return [item for item in items if item['id'] == int(id)]
		
		show_questions = [search(q, questions) for q in qids if int(q) > 0]
		show_answers = [search(a, answers) for a in aids if int(a) > 0]
		
		# add textarea answers at the end because they will not come from POST
		textarea_answers = answers = db.execute(
			"""SELECT * FROM answers JOIN questions ON questions.id = answers.question_id
			AND questions.answer_type='textarea' AND questions.quiz_id=? """,
			(id,)			
		).fetchall()
		
		show_answers.append(textarea_answers)
		#print(repr(show_answers), file=sys.stderr)	
		
		#print(show_questions, file=sys.stderr)
		final_questions = []
		
		# now loop through questions and match answers
		for i, question in enumerate(show_questions):			
			q_answers = []
			for answer in show_answers:				
				if answer[0]['question_id'] == question[0]['id']:					
					# turn to dictionary
					a_dict = dict(zip(answer[0].keys(), answer[0]))
						
					# calculate correct, points, class and assign
					request_answers = request.form['answer_' + str(question[0]['id']) + '[]'] if 'answer_' + str(question[0]['id']) + '[]' in request.form else []
					points, correct, cls, show_wrong = calculate(question[0], answer[0], request_answers)
					
					a_dict['calc_points'] = points			
					a_dict['calc_correct'] = correct
					a_dict['cls'] = cls
					a_dict['show_wrong'] = show_wrong
					a_dict['request_answers'] = request_answers								
					q_answers.append(a_dict)
			
			q_dict = dict(zip(question[0].keys(), question[0]))
			q_dict['q_answers'] = q_answers
			final_questions.append(q_dict)
			
		# construct the variable for the final screen
		answers_var = ''
		total_points = 0
		total_correct = 0
		total_max_points = 0
		total_wrong = 0
		total_empty = 0
		total_questions = len(questions)
		for question in final_questions:
			#print ("Looping question " + str(len(question['q_answers'])), file=sys.stderr)				
			answers_var += """<div class='show-question'>
				<div class='show-question-content'>
					{question}		
				</div>
				<ul>""".format(question=question['question'])
			
			max_points = calc_max_points(question)	
			total_max_points += max_points
			correct = 0
			
			# Unanswered?
			if question['answer_type'] != 'textarea':
				empty = 0 if 'answer_' + str(question['id']) + '[]' in request.form else 1				
			else: 				
				empty = 0 if ('answer_' + str(question['id']) + '[]' in request.form and request.form['answer_' + str(question['id']) + '[]'] != '') else 1				
			total_empty += empty
					
			for answer in question['q_answers']:
				# correct and points are added by the calculate function only if they are selected by the user. 
				# So it's OK to add them here without further checks
				total_points += to_float(answer['calc_points'])
				if answer['calc_correct']:
					correct = 1		
				
				#print ("Looping" + str(answer['id']), file=sys.stderr)						
				if question['answer_type'] != "textarea":
					checkmark = ''
					if answer['cls'].find('correct-answer') != -1:
						checkmark = ' <var class="correct">&check;</var>';
					elif answer['show_wrong']:
						checkmark = ' <var class="wrong">&#x2715;</var>';
					
					answers_var += '''<li class="{answer_class}">
								<span class='answer'>{answer}</span>
							</li>'''.format(answer=answer['answer'] + checkmark, answer_class=answer['cls'])
							
				# for textareas the answer can be correct only once. If the user has wrongly entered same word multiple times (or with case sensitivity in mind) we have to ensure the question won't add
				# points and num correct answers multiple times.			
				if question['answer_type'] == "textarea":
					if answer['calc_correct']:						
						correct = 1
					
			# end for each answer			
					
			# answered wrongly?			
			wrong = 1 if (empty == 0 and correct == 0) else 0			
			total_wrong += wrong		
			
			# whole question answered correctly?
			if correct:
				total_correct += 1
				
			# textareas
			if question['answer_type'] == "textarea" and 'answer_' + str(question['id']) + '[]' in request.form and request.form['answer_' + str(question['id']) + '[]']:				
				textarea_class = 'answer'
				checkmark = ''
				if len(question['q_answers']) and not question['is_survey']:
					textarea_class = 'answer '
					if correct:
						textarea_class += ' correct-answer'
						checkmark = ' <var class="correct">&check;</var>';
					else:
						checkmark = ' <var class="wrong">&#x2715;</var>';	
				
				#print(question['q_answers'], file=sys.stderr)
				answers_var += '''<li class='user-answer {textarea_class}'><span class='answer'>{request_answer}</span></li>'''.format(
					textarea_class = textarea_class, request_answer = request.form['answer_' + str(question['id']) + '[]'] + checkmark)
					
			if question['answer_type'] == "textarea" and empty:
				answers_var += '<li>The question was not answered.</li>'		
				
			answers_var += """</ul>
			</div>	"""	
		
		final_output = nl2br(quiz['final_screen'])
		
		# calculate grade if any
		grade = {'title' : 'None', 'description':'', 'id' : 0}
		grades = db.execute("SELECT * FROM grades WHERE quiz_id=?",
			(id,)).fetchall()
		
		for g in grades:
			if g['gfrom'] <= total_points <= g['gto']: 
				grade = g
		
		# percent correct
		percent_correct = round(100 * total_correct / total_questions) if total_questions else 0	
		
		# avg points
		avg_points = ''
		if '%avg-points%' in final_output:
			avg_points = str(round(db.execute("SELECT AVG(points) as avg_points FROM takings WHERE quiz_id=?", (quiz['id'],)).fetchone()['avg_points'], 2))
		
		chart = ''	
		if '%basic-chart%' in final_output:
			chart = do_basic_chart(total_points, quiz['id'])
		
		replace_vars = {'%avg-points%' : avg_points, '%answers%' : answers_var, '%correct%' : str(total_correct),
			'%wrong%' : str(total_wrong), '%empty%': str(total_empty), '%percent%' : str(percent_correct), '%points%' : str(total_points),
			'%max-points%' : str(total_max_points), '%gtitle%': grade['title'], '%gdescription%': nl2br(grade['description']), '%basic-chart%': chart}	
		
		# replace variables
		final_output = replace_all(final_output, replace_vars)
		
		# Insert taking	
		user_id = session.get('user_id') or 0
		taking_id = complete_quiz(quiz_id = quiz['id'], user_id = user_id, date = datetime.today().strftime('%Y-%m-%d'), points = total_points, 
		 	grade_id = grade['id'], result = grade['title'], snapshot = final_output, email = '', percent_correct = percent_correct,
		 	num_correct = total_correct, num_wrong = total_wrong, num_empty = total_empty)
		 	
		# send emails		
		
		# first need to prepare the email output and replace vars 
		if quiz['email_output'] != '':
			email_output = nl2br(quiz['email_output'])			
			email_output = replace_all(email_output, replace_vars)	
		else:
			email_output = final_output
			
		if quiz['notify_admin']: notify(quiz, email_output, 'admin')		
		if quiz['notify_user']: notify(quiz, email_output, 'user')
		
		index_url = request.url_root + url_for('quizzes.index')
		quiz_url = request.base_url 
		final_output += f"""<p><input type="button" value="Take Again" onclick="window.location = '{quiz_url}';">
			<input type="button" value="Back to Quizzes" onclick="window.location = '{index_url}';"></p>"""
		
		return final_output
	
	return render_template('quizzes/quiz.html', quiz = quiz, questions=questions, qid_sql=qid_sql, request = request)	
	
# Calculates the points, if the answer is correct, and the class to return	
# this happens for each answer from the DB. On textareas we do some additional checks in the loop in case the user has not given any answer
def calculate(question, answer, request_answers):
	points = 0
	cls = ''
	correct = 0
	
	if question['answer_type'] != 'textarea':		 
		if answer['correct'] == 1 and question['is_survey'] == 0: 
			cls += ' correct-answer'		
		if str(answer['id']) in request_answers:
			cls += ' user-answer'
		if str(answer['id']) in request_answers and answer['correct'] == 1 and question['is_survey'] == 0:
			correct = 1
		if str(answer['id']) in request_answers:
			points = answer['points']	

	else:
		# textareas	
		if not request_answers:
			return 0, 0, '', False
		user_answer = request_answers
		
		cls += ' user-answer'			
			
		if answer['answer'].lower() == user_answer.lower() and answer['correct'] == 1 and not question['is_survey']:
			correct = 1
			cls += ' correct-answer'
				
		if question['is_survey']:
			cls = cls.replace('user-answer', 'user-answer-survey')			
			
	# let's mark explicitly if it has to be shown as wrong
	show_wrong = False
	if cls.find('user-answer') != -1 and cls.find('correct-answer') == -1 and not question['is_survey']:
		show_wrong = True	
	
	return points, correct, cls, show_wrong
# end calculate()	
	
# calculate max_points of a question
def calc_max_points(question):
	max_points = 0
	
	if len(question['q_answers']) == 0:
		return max_points
		
	if question['answer_type'] in ['radio', 'textarea']:		
		max = 0
		for answer in question['q_answers']:
			if to_float(answer['points']) > max:
				max = answer['points']
		
		max_points += max
		
	if question['answer_type'] == 'checkbox':
		for answer in question['q_answers']:			
			if to_float(answer['points']) > 0:
				max_points += answer['points']	
	
	return max_points	
	# end calc_max_points()
	
# insert the taking record when the quiz is completed	
def complete_quiz(quiz_id, user_id, date, points, grade_id, result, snapshot, email, percent_correct, num_correct, num_wrong, num_empty):
	db = get_db()
	db.execute("""INSERT INTO takings (quiz_id, user_id, date, points, grade_id, result, snapshot, 
		email, percent_correct, num_correct, num_wrong, num_empty, ip, start_time, source_url)
		VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '') """,
		(quiz_id, user_id, date, points, grade_id, result, snapshot, email, percent_correct, num_correct, num_wrong, num_empty))
	db.commit()	
	
	taking_id = db.execute('SELECT last_insert_rowid() as last_id').fetchone()
	return taking_id['last_id']	
	# end complete_quiz
	
# basic barchart your points vs avg points
# taking is manually construct dict of necessary
# the table is in HTML for two reasons: it is loaded by Ajax, and it may need to be sent by email (so chartjs is no good here)
def do_basic_chart(points, quiz_id):
	db = get_db()
	
	your_color = 'green'
	avg_color = 'gray'
	step = 2
	
	# get average points
	avg_points = round(db.execute("SELECT AVG(points) as avg_points FROM takings WHERE quiz_id=?", (quiz_id,)).fetchone()['avg_points'], 2)
	
	# the points step should roughly make the higher points bar 200px high
	more_points = avg_points if avg_points > points else points
	if more_points <= 0:
		more_points = 1 # set to non-zero for division
	points_step = round(200 / more_points, 2)
	
	# create & return the chart HTML
	content = '<table class="watu-basic-chart"><tr>'
	
	# normalize points here, shouldn't be less than zero when calculating the bar height
	if points < 0:
		points = 0;		
		
	height = round(points_step * points)
	avg_height = round(points_step * avg_points)		
	
	content += '<td style="vertical-align:bottom;"><table class="basic-chart-points"><tr><td align="center" style="vertical-align:bottom;">';
	content += f"<div style=\"background-color:{your_color};width:100px;height:{height}px;\">&nbsp;</div>"; 
	content +='</td><td align="center" style="vertical-align:bottom;">';
	content += f"<div style=\"background-color:{avg_color};width:100px;height:{avg_height}px;\">&nbsp;</div>";
	content += f'</td></tr><tr><td align="center">Your points: {points}</td><td align="center">Avg. points: {avg_points}</td></tr>';
	content += '</table></td>';			
	
	content += '</tr></table>';
	
	return content
	# end do_basic_chart
	
# the function that sends email to user and / or admin
def notify(quiz, content, whom):
	db = get_db()
	
	sender = db.execute("SELECT option_value FROM options WHERE option_key = 'email_sender' ").fetchone()
	sender = sender['option_value']
	sender_name = db.execute("SELECT option_value FROM options WHERE option_key = 'email_sender_name' ").fetchone()
	sender_name = sender_name['option_value']
	user_name = g.user['username'] if g.user else "Guest"
	quiz_name = quiz['name']
	
	if whom == 'admin':
		receiver = quiz['notify_email']
		subject = f"Results of {user_name} on quiz {quiz_name}"
	else:
		receiver = request.form['email'] if 'email' in request.form else ''
		subject = f"Your results on quiz {quiz_name}"
		
	if receiver == '': return False
	
	# split content?
	if '{{split}}' in content:
		parts = content.split('{{split}}')
		content = parts[0] if whom == 'admin' else parts[1]	
		
	email_config = db.execute("SELECT option_value FROM options WHERE option_key = 'email_config' ").fetchone()
	email_config = pickle.loads(email_config['option_value']) if email_config else None		
	if email_config is None: return False 
	
	app = current_app
	app.config['MAIL_SERVER']= email_config['server']
	app.config['MAIL_PORT'] =  email_config['port']
	app.config['MAIL_USERNAME'] = email_config['username']
	app.config['MAIL_PASSWORD'] = email_config['pass']
	app.config['MAIL_USE_TLS'] = True if email_config['use_tls'] else False
	app.config['MAIL_USE_SSL'] = True if email_config['use_ssl'] else False
	mail = Mail(app)
	
	msg = Message(quiz['email_subject'], sender = (sender_name, sender), recipients = [receiver])
	msg.html = content
	mail.send(msg)
	
	return True

	