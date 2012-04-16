#!/usr/bin/env python
#
import logging
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from string import punctuation
from operator import itemgetter

def get_top_words(text,top):
  words=[word.strip(punctuation).lower() for word in text.split()]
  freqs={}
  for word in words:
    freqs[word]=freqs.get(word,0)+1
  return sorted(freqs.items(),key=itemgetter(1),reverse=True)[:top]

class Bin(db.Model):
  user=db.UserProperty(auto_current_user_add=True)
  name=db.StringProperty(required=True)
  date=db.DateTimeProperty(auto_now=True)

class Item(db.Model):
  title=db.StringProperty(required=True)
  link=db.StringProperty()
  body=db.TextProperty()
  date=db.DateTimeProperty(auto_now=True)
  user=db.UserProperty(auto_current_user_add=True)
  bin=db.ReferenceProperty(Bin)
  num_comments=db.IntegerProperty()

class Comment(db.Model):
  body=db.StringProperty(required=True)
  user=db.UserProperty(auto_current_user_add=True)
  date=db.DateTimeProperty(auto_now=True)
  item=db.ReferenceProperty(Item)

class MainHandler(webapp.RequestHandler):
    def get(self):
        user=users.get_current_user()

        if user:

          bins=db.GqlQuery("SELECT * FROM Bin WHERE user = :1",user)
          all_items=[]

          name=self.request.get('bin')
          if name is not None:
            this_bin=Bin.gql("WHERE name=:1 AND user=:2",name,user).get()

          if this_bin is not None:
            items=db.GqlQuery("SELECT * FROM Item WHERE bin=:1",this_bin)
            for item in items:
              all_items.append(item)
          else:
            for bin in bins:
              items=db.GqlQuery("SELECT * FROM Item WHERE bin = :1",bin)
              for item in items:
                all_items.append(item)

          javascript="javascript:function social_bin_add(){var d=document,z=d.createElement('script'),b=d.body,l=d.location;try{if(!b)throw(0);z.setAttribute('src','http://socialbin.appspot.com/add?link='+encodeURIComponent(l.href)+'&title='+encodeURIComponent(d.title));b.appendChild(z);}catch(e){alert('Please wait until the page has loaded.');}} social_bin_add();void(0)"  
          path=os.path.join(os.path.dirname(__file__),'index.html')
          template_values={'bins':bins, 'items':all_items}
          self.response.out.write(template.render(path,template_values))
        else:
          self.redirect(users.create_login_url(self.request.uri))

class PeopleHandler(webapp.RequestHandler):
    def get(self):
      self.response.out.write('sources')

class BinsHandler(webapp.RequestHandler):
    def get(self):
      user=users.get_current_user()
      bins=Bin.all()
      path=os.path.join(os.path.dirname(__file__),'bins.html')
      template_values={'bins':bins}
      self.response.out.write(template.render(path,template_values))

class TopicsHandler(webapp.RequestHandler):
    def get(self):
      user=users.get_current_user()
      topics=[]
      for bin in Bin.all():
        words=''
        for item in Item.gql("WHERE bin = :1",bin):
          words=words+' '+item.title
        top_words=get_top_words(words,10)
        for word,freq in top_words:
          self.response.out.write(word+": "+str(freq))
          self.response.out.write("<BR>")

class SourcesHandler(webapp.RequestHandler):
    def get(self):
      self.response.out.write('sources')

class DeleteItemHandler(webapp.RequestHandler):
    def get(self,key):
      item=Item.get(key)
      if item is not None:
        item.delete()
      self.response.out.write('success')

class AddBinHandler(webapp.RequestHandler):
    def post(self):
      name=self.request.get("name");
      bin=Bin(name=name)
      bin.put()
      self.response.out.write(name)

class AddCommentHandler(webapp.RequestHandler):
    def post(self):
        user=users.get_current_user()
        if user:
          comment=self.request.get('comment')
          key=self.request.get('key')
          logging.info('key='+key)
          item=Item.get(key)
          if item is not None:
            if item.num_comments is None:
              item.num_comments=1
            else:
              item.num_comments=item.num_comments+1
            item.put()
            new_comment=Comment(user=user,body=comment,item=item)
            new_comment.put()
        self.response.out.write('success')

class ItemHandler(webapp.RequestHandler):
    def get(self,key):
        user=users.get_current_user()
        item=Item.get(key)
        if item:
          comments=Comment.gql("WHERE item=:1",item)
          path=os.path.join(os.path.dirname(__file__),'item.html')
          template_values={'item':item,'comments':comments}
          self.response.out.write(template.render(path,template_values))
        else:
          self.redirect('/')

class AddItemHandler(webapp.RequestHandler):
    def get(self):
        user=users.get_current_user()
        if user:
          default_bin=Bin.gql("WHERE name='Inbox' AND user = :1",user).get()
          if default_bin is None:
            default_bin=Bin(name='Inbox')
            default_bin.put()
          item=Item(title=self.request.get('title'),
              link=self.request.get('link'),
              body=self.request.get('body'),
              bin=default_bin)
          item.put()
          self.response.out.write('Added: '+item.title)
        else:
          self.redirect(users.create_login_url(self.request.uri))


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/add',AddItemHandler),
                                          ('/people',PeopleHandler),
                                          ('/bins/add',AddBinHandler),
                                          ('/item/comment/add',AddCommentHandler),
                                          ('/item/delete/(.*)',DeleteItemHandler),
                                          ('/item/(.*)',ItemHandler),
                                          ('/bins',BinsHandler),
                                          ('/topics',TopicsHandler),
                                          ('/sources',SourcesHandler)
                                        ],
                                         debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
