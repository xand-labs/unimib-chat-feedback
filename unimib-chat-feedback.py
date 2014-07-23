import os
import jinja2
import webapp2
import json

from urllib import urlencode
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import ndb



template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Post(ndb.Model):
    """Models an individual post entry."""
    subject = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.UserProperty()

class Comment(ndb.Model):
    """Models an individual post entry."""
    #post = ndb.KeyProperty(kind = Post)
    content = ndb.TextProperty(required = True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.UserProperty()

    @classmethod
    def query_post(cls, ancestor_key):
        return cls.query(ancestor=ancestor_key).order(cls.date)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        user = users.get_current_user()
        if user:
            kw['user'] = user
        kw['logout'] = users.create_logout_url(self.request.uri)
        self.write(self.render_str(template, **kw))


class NewPost(Handler):
    def render_new_post(self, subject="", content="", error=""):
        self.render('new_post.html', subject=subject, content=content, error=error)

    def get(self):
        params = {}
        self.render('new_post.html', **params)

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if content and subject:
            user = users.get_current_user()
            post = Post(subject = subject, 
                        content = content, 
                        author = user)
            post_key = post.put()

            self.slack(subject, str(post_key.id()), user)

            self.redirect('/post/' + str(post_key.id()))
        else:
            error = "fai attenzione e completa bene"
            self.render_new_post(subject, content, error)

    @staticmethod
    def slack(subject, post_id, user):

        conf = open('config.json').read()
        conf = json.loads(conf)

        key = conf['slack'][0]['key']
        channel = conf['slack'][0]['channel']

        url = 'https://slack.com/api/chat.postMessage'
        link = 'http://unimib-chat-feedback.appspot.com/post/' + post_id
        data = dict(token=key, 
                    channel=channel,
                    text='*' + subject + '* _' + user.nickname() + '_ \n' + link, 
                    username='feedback', 
                    icon_url='http://unimib-chat-feedback.appspot.com/static/img/xand.png')
        request = url + '?' + urlencode(data)

        urlfetch.fetch(request)


class SinglePost(Handler):
    def get(self, post_id):
        post = Post.get_by_id(int(post_id))
        if post:
            params = {}
            params['post'] = post
            ancestor_key = ndb.Key("Post", post.key.id())
            params['comments'] = Comment.query_post(ancestor_key).fetch()
            self.render('post.html', **params)
        else:
            self.redirect('/')

    def post(self, post_id):
        content = self.request.get("content")
        print(post_id)
        post = Post.get_by_id(int(post_id))
        if content and post:
            comment = Comment(parent = ndb.Key("Post", post.key.id()),
                              content = content,
                              author = users.get_current_user())
            comment.put()
            params = {}
            params['post'] = post
            ancestor_key = ndb.Key("Post", post.key.id())
            params['comments'] = Comment.query_post(ancestor_key).fetch()
            self.render('post.html', **params)
        else:
            self.redirect('/')


class Login(Handler):
    def get(self):
        # Checks for active Google account session
        user = users.get_current_user()

        if user and (user.email()[-9:] != 'unimib.it' and user.email() not in ['alfio.emanuele.f@gmail.com',
                                                                         'luca.desano@gmail.com']):
            self.redirect(users.create_logout_url('http://xkcd.com'))
        elif user:
            params = {}
            params['posts'] = Post().query().order(-Post.date)
            self.render('welcome.html', **params)
        else:
            self.redirect(users.create_login_url(self.request.uri))



application = webapp2.WSGIApplication([
    (r'/', Login),
    (r'/newpost', NewPost),
    (r'/post/(\d+)', SinglePost)
], debug=True)