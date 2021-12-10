from flask import current_app, g
import base64, random

# convert possibly invalid string to float
def to_float(num):
	try: 
		num = float(num)
		return num
	except:
		return 0	  

# convert possibly invalid string to int		
def to_int(num):
	try: 
		num = int(num)
		return num
	except:
		return 0	  		

# verify a text captcha		
def verify_captcha(question, answer):
	questions = db.execute("SELECT option_value FROM options WHERE option_key='captcha_questions'").fetchone()
	questions = questions['option_value'].splitlines()
	
	base64_question = question.encode('ascii')
	question_bytes = base64.b64decode(base64_question)
	question = question_bytes.decode('ascii')

	for captcha_question in questions:
		[q, a] = captcha_question.split('=')
		q = strip(q)
		a = strip(a)
		
		if(q == question and a.lower() == answer.lower()):
			return TRUE
		
	return FALSE
	# end verify text captcha
	
# generate a text captcha
def generate_captcha():
	questions = db.execute("SELECT option_value FROM options WHERE option_key='captcha_questions'").fetchone()
	questions = questions['option_value'].splitlines()
	
	# just get random
	random.shuffle(questions)
	question = strip(questions[0])
	[q, a] = question.split('=')
	
	q_bytes = q.encode("ascii")
	base64_bytes = base64.b64encode(q_bytes)
	base64_string = base64_bytes.decode("ascii")
		
	return strip(q) + " <input type='text' name='text_captcha_answer'>\n<input type='hidden' name='text_captcha_question' value=\"" + base64_string + "\">";			
	
# PHP's nl2br	
def nl2br(s):
    return s.replace("\n", "<br>")		
   
# Replace all variables from a dictionary     
def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text    