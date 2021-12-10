import functools, sys

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.exceptions import abort

from quiz.auth import login_required
from quiz.db import get_db
from datetime import datetime