import functools, time, logging, sys

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.exceptions import abort

from inspect import getmembers
from pprint import pprint

from quiz.auth import login_required, admin_login_required
from quiz.db import get_db
from quiz.helpers import *

# See: https://stackoverflow.com/questions/54444776/how-can-i-break-up-a-flask-blueprint-into-multiple-files-within-a-subfolder answers to breakdown in subfolders

bp = Blueprint('admin_grades', __name__)

@bp.route('/admin/grades/<int:quiz_id>/', methods=('GET', 'POST'))	
@admin_login_required
def grades(quiz_id ):
	db = get_db()
	
	quiz = db.execute(
			"""SELECT tE.*, COUNT(tQ.id) as cnt_questions, COUNT(tT.id) as cnt_takings
			FROM quizzes tE LEFT JOIN questions tQ ON tE.id = tQ.quiz_id 
			LEFT JOIN takings tT ON tE.id = tT.quiz_id 
			WHERE tE.id=?""",
			(quiz_id,)
		).fetchone()	
	
	#print(quiz, file=sys.stderr)	
	
	if quiz['id'] is None:
		return abort(404)	
		
	
	if request.method == 'POST':
		title = request.form['title'] or ''
		description = request.form['description'] or ''		
		gfrom = to_float(request.form['gfrom']) or 0
		gto = to_float(request.form['gto']) or 0
		redirect_url = request.form['redirect_url'] or ''
		
		# add grade
		if 'add' in request.form and request.form['add']:
			db.execute(
				"""INSERT INTO grades (quiz_id, title, description, gfrom, gto, redirect_url) 
				VALUES (?, ?, ?, ?, ?, ?)""",
				(quiz_id, title, description, gfrom, gto, redirect_url)
			)
			db.commit()
			return redirect(url_for('admin_grades.grades', quiz_id=quiz_id))
			
		# delete grade	
		if 'del' in request.form and request.form['del'] and request.form['id']:
			db.execute('DELETE FROM grades WHERE id=?', (request.form['id'] ))
			db.commit()
			return redirect(url_for('admin_grades.grades', quiz_id=quiz_id))	
			
		# edit grade
		if 'save' in request.form and request.form['save'] and request.form['id']:
			db.execute("""UPDATE grades SET title=?, description=?, gfrom=?, gto=?, redirect_url=?	WHERE id=?""",
			   (title, description, gfrom, gto, redirect_url, request.form['id'])
			)
			db.commit()
		
		
	# select existing grades
	grades = db. execute(
		"""SELECT * FROM grades WHERE quiz_id=? ORDER BY id""",
		(quiz_id,)
	).fetchall()	
	
	return render_template('admin/grades.html', quiz = quiz, grades = grades) 