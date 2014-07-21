import os

#from google.appengine.api import users
from google.appengine.ext import db

import jinja2
import webapp2
import string
import hashlib
import random
import re
import string

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def make_salt():
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.sample(char_set*5, 5))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (h, salt)

def valid_pw_hash(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name,pw, salt)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Blog(db.Model):
    """Models an individual blog entry."""
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    date = db.DateTimeProperty(auto_now_add=True)

class User(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
    email = db.StringProperty(required = False)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):
    def get(self):
        blogs = db.GqlQuery("SELECT * FROM Blog "
                            "ORDER BY date DESC ")
        self.render('index.html', blogs = blogs)

class NewPost(Handler):
    def render_new_post(self, subject="", content="", error=""):
        self.render('new_post.html', subject=subject, content=content, error=error)

    def get(self):
        self.render('new_post.html')

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if content and subject:
            b = Blog(subject = subject, content = content)
            b.put()
            key = b.key().id()
            self.redirect('/blog/' + str(key))
        else:
            error = "gnegnegne"
            self.render_new_post(subject, content, error)

class SingleBlog(Handler):
    def get(self, blog_id):
        blog = Blog.get_by_id(int(blog_id))
        if blog:
            self.render('index.html', blogs=[blog])
        

class SignUp(Handler):
    def get(self):
        self.render('register.html')

    def post(self):
        have_error = False
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        params = dict(username = username, 
                      email = email)

        if not valid_username(username):
            params['error_username'] = "That's not a valid username."
            have_error = True
        elif User.all().filter("username =", username).get():
            print(User.all().filter("username =", username).get())
            params['error_username'] = "Username already in use."
            have_error = True

        if not valid_password(password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif password != verify:
            params['error_password'] = "password mismath"
            have_error = True

        if not valid_email(email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('register.html', **params)
        else:
            password_hash = make_pw_hash(username, password)
            u = User(username=username, password=password_hash, email=email)
            u.put()
            key = str(u.key().id())
            key_hash = hashlib.md5(key).hexdigest()
            self.response.headers.add_header('Set-Cookie', 'user-id=%s|%s; Path=/' % (key, key_hash))
            self.redirect('/blog/welcome?username=' + username)

class Login(Handler):
    def get(self):
        self.render('login.html')

    def post(self):
        have_error = False
        username = self.request.get("username")
        password = self.request.get("password")

        params = dict(username = username)

        if not valid_username(username):
            params['error'] = "Login error"
            have_error = True

        if not valid_password(password):
            params['error'] = "Login error"
            have_error = True

        user = User.all().filter("username =", username).get()
        if user is None:
            params['error'] = "Login error"
            have_error = True
        elif not valid_pw_hash(username, password, user.password):
            params['error'] = "Login error"
            have_error = True

        if have_error:
            self.render('login.html', **params)
        else:
            key = str(user.key().id())
            key_hash = hashlib.md5(key).hexdigest()
            self.response.headers.add_header('Set-Cookie', 'user-id=%s|%s; Path=/' % (key, key_hash))
            self.redirect('/blog/welcome')

class Index(Handler):
    def get(self):
        self.write('Hello, Udacity!')

class Welcome(Handler):
    def get(self):
        user_id, user_hash = self.request.cookies.get('user-id').split('|')
        user = User.get_by_id(int(user_id))
        if user_hash == hashlib.md5(user_id).hexdigest():
            self.render('welcome.html', user=user)
        else:
            self.redirect('/blog/signup')

class Logout(Handler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', 'user-id=; Path=/')
        self.redirect('/blog/signup')

class Rot13(Handler):
    def get(self):
        self.render('rot13.html')

    def post(self):
        text = self.request.get('text')
        lo = string.ascii_lowercase
        up = string.ascii_uppercase
        newtext = ''
        for c in text:
            if c in lo:
                newtext += list(lo)[(lo.index(c) + 13) % 26]
            elif c in up:
                newtext += list(up)[(up.index(c) + 13) % 26]
            else:
                newtext += c
        self.render('rot13.html', text=newtext)

application = webapp2.WSGIApplication([
    (r'/', Index),
    (r'/rot13', Rot13),
    (r'/blog', MainPage),
    (r'/blog/newpost', NewPost),
    (r'/blog/(\d+)', SingleBlog),
    (r'/blog/signup', SignUp),
    (r'/blog/welcome', Welcome),
    (r'/blog/login', Login),
    (r'/blog/logout', Logout)
], debug=True)