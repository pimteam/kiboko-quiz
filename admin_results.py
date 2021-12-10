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

bp = Blueprint('admin_results', __name__)

# list results on a quiz
@bp.route('/admin/results/<int:quiz_id>/', methods=('GET', 'POST'))	
@admin_login_required
def index(quiz_id ):
	db = get_db()
	cursor = db.cursor()
	
	quiz = db.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
	
	# view taking details  by Ajax
	if request.args.get('view_taking_id'):
		return view_result(taking_id = request.args.get('view_taking_id'))
	
	if request.args.get('del'):		
		db.execute("DELETE FROM takings WHERE id=?", (int(request.args.get('del')),))
		db.commit()
		return redirect(url_for('admin_results.index', quiz_id=quiz_id))
		
	# mass delete NYI
	if 'del_takings' in request.form and request.form['del_takings']:
		del_ids = ['0']
		for id in request.form.getlist('ids'):
			del_ids.append(str(to_int(id)))
		
		# now delete
		id_sql = ", ".join(del_ids)
		db.execute(f"""DELETE FROM takings WHERE id IN ({id_sql})""")
		db.commit()
		return redirect(url_for('admin_results.index', quiz_id=quiz_id))
	
		
	# prepare ordering and filters and select records
	dir = request.args.get('dir') or 'DESC'
	if dir not in ['ASC', 'DESC']:
		dir = 'DESC'	
	odir = 'ASC' if dir == "DESC" else "DESC"	
		
	ob = request.args.get('ob') or 'takings.id'
	offset  = to_int(request.args.get('offset')) or 0
	limit = 10
	limit_sql = f"LIMIT {offset}, {limit}" if not request.args.get('export') else '' 	
	
	# filter / search?
	filters = []
	joins = []
	vars = [] # this will be passed as tuple with vars to the SQL query
	join_sql = "LEFT JOIN users tU ON tU.id = tT.user_id";
	
	# date filter
	# see https://realpython.com/prevent-python-sql-injection/
	if request.args.get('date'):
		datef = request.args.get('datef')
		date = request.args.get('date')
		vars.append(date)
		if datef == 'less':
			flt = " takings.date < ? "			
		elif datef == 'more':
			flt = " takings.date > ? "
		else:
			flt = " takings.date = ? "
			
		filters.append(flt)	
	
	# points	
	if request.args.get('points'):
		pointsf = request.args.get('pointsf')
		points = request.args.get('points')
		vars.append(points)
		if pointsf == 'less':
			flt = " takings.points < ? "			
		elif datef == 'more':
			flt = " takings.points > ? "
		else:
			flt = " takings.points = ? "	
			
		filters.append(flt)		
		
	# grade
	if request.args.get('grade_id'):
		grade_id = to_int(request.args.get('grade_id'))
		flt = " takings.grade_id=? "
		filters.append(flt)		
		
	# now select
	filters_sql = " AND " + " AND ".join(filters) if filters else ''
	vars = [quiz_id]  + vars 

	vars = tuple(vars)
	
	results = db.execute(f"""SELECT takings.*, grades.title as grade_title, users.username as username 
		FROM takings 
		LEFT JOIN grades ON takings.grade_id = grades.id
		LEFT JOIN users ON takings.user_id = users.id
		WHERE takings.quiz_id=? {filters_sql} ORDER BY {ob} {dir} {limit_sql}""", vars).fetchall()	
		
	count = db.execute(f"""SELECT COUNT(*) as cnt
		FROM takings 
		LEFT JOIN grades ON takings.grade_id = grades.id
		LEFT JOIN users ON takings.user_id = users.id
		WHERE takings.quiz_id=? {filters_sql}""", vars).fetchone()		
		
	#print(results, file=sys.stderr)	
	
	return render_template('admin/results.html', quiz = quiz, results = results, count = count['cnt'], limit = limit, offset = offset) 

# details of a single taking
@admin_login_required
def view_result(taking_id):
	db = get_db()
	
	taking = db.execute("""SELECT * FROM takings WHERE id=?""", (taking_id,)).fetchone()
	if taking is None:
		return "AAAAAAAAAA"
		
	quiz = db.execute("""SELECT * FROM quizzes WHERE id=?""", (taking['quiz_id'],)).fetchone()
	username = None
	if taking['user_id']: 
		username = db.execute("""SELECT username FROM users WHERE id=?""", (taking['user_id'],)).fetchone()
		username = username['username']
	
	return render_template('quizzes/taking-details.html', taking = taking, quiz = quiz, 
		admin_user = True, username = username)	
	
	