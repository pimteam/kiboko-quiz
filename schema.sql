DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS answers;
DROP TABLE IF EXISTS grades;
DROP TABLE IF EXISTS quizzes;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS takings;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  user_level TEXT NOT NULL
);

CREATE TABLE answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER NOT NULL,
  answer TEXT NOT NULL,
  correct INTEGER NOT NULL,
  points REAL NOT NULL,
  sort_order INTEGER NOT NULL,	
  FOREIGN KEY (question_id) REFERENCES questions (id)
);

CREATE TABLE grades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quiz_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  gfrom REAL NOT NULL,
  gto REAL NOT NULL,
  redirect_url TEXT NOT NULL,
  FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
);

CREATE TABLE quizzes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,  
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  final_screen TEXT NOT NULL,
  added_on TEXT NOT NULL,
  randomize INTEGER NOT NULL,
  single_page INTEGER NOT NULL,
  require_login INTEGER NOT NULL,
  notify_admin INTEGER NOT NULL,
  randomize_answers INTEGER NOT NULL,
  pull_random INTEGER NOT NULL,
  dont_store_data INTEGER NOT NULL,
  require_text_captcha INTEGER NOT NULL,
  email_output TEXT NOT NULL,
  notify_user INTEGER NOT NULL,
  notify_email TEXT NOT NULL,  
  times_to_take INTEGER NOT NULL,
  no_ajax INTEGER NOT NULL,
  no_alert_unanswered INTEGER NOT NULL,  
  advanced_settings TEXT NOT NULL,
  email_subject TEXT NOT NULL,
  design_theme TEXT NOT NULL
);


CREATE TABLE questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quiz_id INTEGER NOT NULL,
  question TEXT NOT NULL,
  answer_type TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  is_required INTEGER NOT NULL,
  feedback TEXT NOT NULL,
  is_inactive INTEGER NOT NULL,
  is_survey INTEGER NOT NULL,
  num_columns INTEGER NOT NULL,
  FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
);

CREATE TABLE takings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quiz_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  ip TEXT NOT NULL,
  date TEXT NOT NULL,
  points REAL NOT NULL,
  grade_id INTEGER,
  result TEXT NOT NULL,
  snapshot TEXT NOT NULL,
  start_time TEXT NOT NULL,
  email TEXT NOT NULL,
  percent_correct INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  num_correct INTEGER NOT NULL,
  num_wrong INTEGER NOT NULL,
  num_empty INTEGER NOT NULL,
  FOREIGN KEY (quiz_id) REFERENCES quizzes (id),
  FOREIGN KEY (user_id) REFERENCES users (id),
  FOREIGN KEY (grade_id) REFERENCES grades (id)
);

CREATE TABLE options (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	option_key TEXT NOT NULL UNIQUE,
	option_value TEXT NOT NULL     
);