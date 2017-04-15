import os
import webapp2
import jinja2
import time
import string
import random
import hashlib
import hmac
import ConfigParser
from google.appengine.ext.webapp.util import run_wsgi_app
from blogdatabase import *

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja2_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True)
config = ConfigParser.SafeConfigParser()
config.read('simpleblog.cfg')

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def get(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja2_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):
    def get(self):
        self.redirect("/blog")

class BlogPage(Handler):
    def render_front(self, title="", blog="", error="", visits=""):
        blogs = db.GqlQuery("SELECT * from Blog ORDER BY created DESC LIMIT 10")
        self.render("front.html", title=title, blog=blog, error=error, blogs=blogs, visits=visits)
    
    def get(self):
        visits = self.request.cookies.get('visits', '0')
        if visits.isdigit():
            visits = int(visits) + 1
        else:
            visits = 0
        self.response.headers.add_header('Set-Cookie', 'visits=%s' % visits)
        self.render_front(visits=visits)
    
    def post(self):
        title = self.request.get("title")
        blog = self.request.get("blog")
        
        if title and blog:
            b = Blog(title = title, blog = blog)
            b.put()
            time.sleep(0.1)
            self.redirect("/blog/"+str(b.key().id()))
        else:
            error = "we need both a title and a blog"
            self.render_front(title, blog, error)

class NewPost(Handler):
    def render_newpost(self, title="", blog="", error=""):
        self.render("newpost.html", title=title, blog=blog, error=error)
    
    def get(self):
        self.render_newpost()
    
    def post(self):
        title = self.request.get("subject")
        blog = self.request.get("content")
        
        if title and blog:
            b = Blog(title = title, blog = blog)
            b.put()
            time.sleep(0.1)
            self.redirect("/blog/"+str(b.key().id()))
        else:
            error = "Please fill out title and blog."
            self.render_newpost(title, blog, error)
        
class BlogHandler(Handler):
    def get(self, blog_id):
        blog = Blog.get_by_id(long(blog_id))
        if blog:
            self.render("blog.html", title=blog.title, blog=blog.blog, error="",
                        date=blog.created)
        else:
            self.render("blog.html", error="Blog not available")

class Welcome(Handler):
    def get_userid_from_safe(self, user_id_safe):
        (user_id, sec) = user_id_safe.split('|')
        key = config.get("security", "hash_key")
        if hmac.new(key, user_id).hexdigest() == sec:
            return user_id
        else:
            return None
        
    
    def get(self):
        user_id_safe = self.request.cookies.get('userid', '0')
        
        user_id = self.get_userid_from_safe(user_id_safe)
        
        if user_id:
            user = User.get_by_id(long(user_id))
            if user:
                self.render("welcome.html", username = user.username)
            else:
                self.redirect("/blog/signup")

class Signup(Handler):
    def render_signup(self, username="", password="", verify="", email="", error=""):
        self.render("signup.html", username=username, password=password,
                    verify=verify, email=email, error=error)
    
    def make_salt(self):
        salt_length = int(config.get("security", "salt_length"))
        return "".join(random.choice(string.letters) for _ in xrange(salt_length))
    
    def calc_hash(self, username, password, salt=None):
        if salt == None:
            salt = self.make_salt()
            
        h = hashlib.sha256(username + password + salt).hexdigest()
        
        return '%s|%s' % (h, salt)
    
    def make_secure_val(self, s):
        key = config.get("security", "hash_key")
        return "%s|%s" % (s, hmac.new(key, s).hexdigest())
    
    def get(self):
        self.render("signup.html")
        
    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        verify   = self.request.get("verify")
        email    = self.request.get("email")
        
        if username and password and verify:
            users_with_name = list(db.GqlQuery("SELECT * from User where username='%s'" % username))
            
            if users_with_name.__len__() > 0:
                error = "Username %s not available" % users_with_name[0]
                self.render_signup(username, password, verify, email, error)
            elif (password != verify):
                error = "Password is not consistent"
                self.render_signup(username, password, verify, email, error)
            else:                   
                pwd_hash = self.calc_hash(username, password)
                
                u = User(username=username, pwd_hash=pwd_hash, email=email)
                u.put()
                
                userid = str(u.key().id())
                secure_userid = self.make_secure_val(userid)
                self.response.headers.add_header('Set-Cookie', 'userid=%s; Path=/'
                                                  % secure_userid)
                time.sleep(0.1)
                self.redirect("/blog/welcome")
        else:
            error = "Some"
            self.render_signup(username, password, verify, email, error)

application = webapp2.WSGIApplication([(r'/', MainPage),                                       
                                       (r'/blog', BlogPage),
                                       (r'/blog/signup', Signup),
                                       (r'/blog/welcome', Welcome),
                                       (r'/blog/newpost', NewPost),
                                       (r'/blog/(\d+)', BlogHandler)], debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
