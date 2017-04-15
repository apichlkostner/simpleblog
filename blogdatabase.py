from google.appengine.ext import db

class Blog(db.Model):
    title = db.StringProperty(required = True)
    blog = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    
class User(db.Model):
    username = db.StringProperty(required = True)
    pwd_hash = db.StringProperty(required = True)
    email    = db.StringProperty(required = False)
    created = db.DateTimeProperty(auto_now_add = True)