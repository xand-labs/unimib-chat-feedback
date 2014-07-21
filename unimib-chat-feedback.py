import os

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Post(ndb.Model):
    """Models an individual post entry."""
    subject = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    #author = qualcosa

class Reply(ndb.model):
    """Models an individual post entry."""
    #post = legata al post
    content = ndb.TextProperty(required = True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    #author = qualcosa

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


class NewPost(Handler):
    def render_new_post(self, subject="", content="", error=""):
        self.render('new_post.html', subject=subject, content=content, error=error)

    def get(self):
        self.render('new_post.html')

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if content and subject:
            b = Post(subject = subject, content = content)
            b.put()
            key = b.key().id()
            self.redirect('/blog/' + str(key))
        else:
            error = "gnegnegne"
            self.render_new_post(subject, content, error)

class SinglePost(Handler):
    def get(self, blog_id):
        blog = Post.get_by_id(int(blog_id))
        if blog:
            self.render('index.html', blogs=[blog])

class Login(Handler):
    def get(self):
        # Checks for active Google account session
        user = users.get_current_user()

        if user:
            params = {}
            params['nick'] = user.nickname()
            params['logout'] = users.create_logout_url(self.request.uri)
            self.render('welcome.html', **params)
        else:
            self.redirect(users.create_login_url(self.request.uri))



application = webapp2.WSGIApplication([
    (r'/', Login),
    (r'/newpost', NewPost),
    (r'/post/(\d+)', SinglePost)
], debug=True)