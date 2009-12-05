#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Things to do
# memcache top for 1 minute or so - maybe until vote?
# paging correctly
# images on about page
# ads set up
# vote page
# flagging
# add ability to title
# admin view flagging page
# flagged images fall out unless approved user
import os
import time
import wsgiref.handlers
import random
import cgi
import logging
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.api import memcache

import models
	
class MainHandler(webapp.RequestHandler):
	def get(self):
		user=users.get_current_user()
		path = os.path.join(os.path.dirname(__file__), 'templates/admin.html')
		self.response.out.write(template.render(path,{'user':user}))

class ajaxEmail(webapp.RequestHandler):
	"""docstring for ajaxEmail"""
	def get(self):
		user=users.get_current_user()
		if user:
			smile_id=int(self.request.get("id"))
			if smile_id:
				email=str(cgi.escape(self.request.get("email")))
				if mail.is_email_valid(email):
					try:
						mail.send_mail(user.email(),email,'Come see this drawing - TenSecondsofHappy.com','Hey,\r\n'+user.nickname()+' wanted you to see a drawing at "Ten Seconds of Happy."  We\'re a place where you can draw to your heart\'s content. Check it out!\r\n\nHere\'s the pictures they wanted you to see: http://www.tensecondsofhappy.com/view?id='+str(smile_id)+'\r\n\nEnjoy,\r\nTenSecondsofHappy.com')
						time.sleep(0.5)
						self.response.out.write("{'response':'Sent'}")
					except:
						return			

class ajaxVote(webapp.RequestHandler):	
	def get(self):
		smile_id=int(self.request.get("id"))
		vote=str(cgi.escape(self.request.get("vote")))
		user=users.get_current_user()
		if user:
			smile=models.Smiley.get_by_id(smile_id)
			if smile:
				existVote=memcache.get("user"+user.nickname()+"smile"+str(smile.key().id()))
				if existVote is None:
					existVoteQ = models.db.GqlQuery("SELECT * FROM Votes WHERE voter = :1 AND smiley_id = :2 ",user,smile_id)		
					existVote=existVoteQ.get()
				#check smile exists ups, downs, votes
				if not smile.ups:
					smile.ups=0
				if not smile.votes:
					smile.votes=0
				if not smile.downs:
					smile.downs=0
				if existVote:
					if vote =='up':
						if existVote.vote==0:
							smile.votes=smile.votes+1
							smile.ups=smile.ups+1
						elif existVote.vote==-1:
							smile.ups=smile.ups+1
							smile.downs=smile.downs-1
							smile.votes=smile.votes+2
						existVote.vote=1
					elif vote =='down':
						if existVote.vote==0:
							smile.downs=smile.downs+1
							smile.votes=smile.votes-1					
						elif existVote.vote==1:
							smile.ups=smile.ups-1
							smile.downs=smile.downs+1
							smile.votes=smile.votes-2
						existVote.vote=-1
					elif vote =='neutral': #neutral
						if existVote.vote==1:
							smile.ups=smile.ups-1
							smile.votes=smile.votes-1	
						elif existVote.vote==-1:
							smile.downs=smile.downs-1
							smile.votes=smile.votes+1
						existVote.vote=0	
					existVote.put()
					if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id()),existVote,3600):
						logging.error("Memcache set failed. Adding Vote")				
				else:
					newVote=models.Votes()
					newVote.voter=user
					newVote.smiley_id=smile_id
					if vote=='up':
						smile.ups=smile.ups+1
						smile.votes=smile.votes+1
						newVote.vote=1
					elif vote=='down':
						smile.downs=smile.downs+1
						smile.votes=smile.votes-1
						newVote.vote=-1
					newVote.put()
					if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id()),newVote,3600):
						logging.error("Memcache set failed. Adding Vote")
				smile.put()
				self.response.out.write("{'ups':'"+str(smile.ups)+"','downs':'"+str(smile.downs)+"'}")

class getMore(webapp.RequestHandler):
	def get(self):
		user=users.get_current_user()
		page=int(self.request.get("page"))
		counter=int(self.request.get("counter"))
		pageType=str(cgi.escape(self.request.get("pageType")))
		if page>0 and counter is not None and pageType is not None:
			if counter<1 or counter>12:
				count=int(models.Info().all().get().value)
				offset=((page-1)*12)+(counter-1)
				if offset>=0 and offset<=count:
					if pageType=='more':
						smile=models.Smiley().all().order('flags').filter('flags',0).order('-create_at').fetch(1,offset)
					elif pageType=='top':
						smile=models.Smiley().all().order('-votes').fetch(1,offset)
					elif pageType=='user':
						smiley_id=cgi.escape(self.request.get("smiley_id"))
						if not smiley_id:
							smile=models.Smiley().all().order('-create_at').filter('author',user).fetch(1,offset)
						else:
							smiled=models.Smiley.get_by_id(int(smiley_id))
							if smiled:
								smile=models.Smiley().all().order('-create_at').filter('author',smiled.author).fetch(1,offset)
					elif pageType=='entries':
						contest_id=cgi.escape(self.request.get("contest_id"))
						if not contest_id:
							return
						contest=models.Contests.get_by_id(int(contest_id))
						smile=models.Entries().all().order('-submitted').filter('contest',contest).fetch(1,offset)
					if smile:
						if pageType=='entries':
							self.response.out.write("{'response':'success','author':'"+str(smile[0].smiley.author)+"','date':'"+str(smile[0].smiley.create_at.strftime('%m/%d/%y @ %I:%M %p'))+"','smile_id':'"+str(smile[0].smiley.key().id())+"','ups':'"+str(smile[0].smiley.ups)+"','downs':'"+str(smile[0].smiley.downs)+"','image':'"+str(smile[0].smiley.image)+"'}")
						else:
							self.response.out.write("{'response':'success','author':'"+str(smile[0].author)+"','date':'"+str(smile[0].create_at.strftime('%m/%d/%y @ %I:%M %p'))+"','smile_id':'"+str(smile[0].key().id())+"','ups':'"+str(smile[0].ups)+"','downs':'"+str(smile[0].downs)+"','image':'"+str(smile[0].image)+"'}")
#							self.response.out.write("{'response':'success','author':'"+str(smile[0].author)+"','date':'"+str(smile[0].create_at+datetime.timedelta(hours=-4))+"','smile_id':'"+str(smile[0].key().id())+"','ups':'"+str(smile[0].ups)+"','downs':'"+str(smile[0].downs)+"','image':'"+str(smile[0].image)+"'}")
					else:
						self.response.out.write("{'response':'end'}")					
				else:
					self.response.out.write("{'response':'end'}")					
			else: 
				self.response.out.write("{'response':'end'}")

class ajaxFlag(webapp.RequestHandler):
	"""docstring for ajaxFlag"""
	def get(self):
		user=users.get_current_user()
		if user:
			smile_id=int(self.request.get("id"))
			smile=models.Smiley.get_by_id(smile_id)
			if smile:
				flag=int(self.request.get("flag"))
				if flag:
					existFlag=memcache.get("user"+user.nickname()+"smile"+str(smile.key().id())+"flag")
					if existFlag is None:
						existFlagQ = models.db.GqlQuery("SELECT * FROM Flags WHERE voter = :1 AND smiley_id = :2 ",user,smile_id)		
						existFlag=existFlagQ.get()
					#check smile exists ups, downs, votes
					if not smile.flags:
						smile.flags=0
					if existFlag:
						if flag==1:
							if existFlag.flag==0:
								smile.flags=smile.flags+1
							existFlag.flag=1
						elif flag =='0':
							if existFlag.flag==1:
								smile.flags=smile.flags-1
							existFlag.flags=0	
						existFlag.put()
						if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id())+"flag",existFlag,3600):
							logging.error("Memcache set failed. Adding Flag")				
					else:
						newFlag=models.Flags()
						newFlag.voter=user
						newFlag.smiley_id=smile_id
						if flag==1:
							smile.flags=smile.flags+1
							newFlag.flag=1
						elif flag==0:
							newFlag.vote=0
						newFlag.put()
						if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id())+"flag",newFlag,3600):
							logging.error("Memcache set failed. Adding Flag")
					smile.put()
					self.response.out.write("{response:'success', flags:'"+str(smile.flags)+"'}")


class checkVote(webapp.RequestHandler):
		def get(self):
			user=users.get_current_user()
			smile=models.Smiley.get_by_id(int(self.request.get("id"))) 
			if smile:
				eVote=0
				if user:
					existVote=memcache.get("user"+user.nickname()+"smile"+str(smile.key().id()))
					if existVote is None:
						existVoteQ = models.db.GqlQuery("SELECT * FROM Votes WHERE voter = :1 AND smiley_id = :2 ",user,smile.key().id())		
						existVote=existVoteQ.get()
					if existVote:
						if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id()),existVote,3600):
							logging.error("Memcache set failed. Checking Vote")
						eVote=existVote.vote
					existFlag=memcache.get("user"+user.nickname()+"smile"+str(smile.key().id())+"flag")
					if existFlag is None:
						existFlagQ = models.db.GqlQuery("SELECT * FROM Flags WHERE voter = :1 AND smiley_id = :2 ",user,smile.key().id())		
						existFlag=existFlagQ.get()
					if existFlag:
						if not memcache.set("user"+user.nickname()+"smile"+str(smile.key().id())+"flag",existFlag,3600):
							logging.error("Memcache set failed. Adding Flag")				
				exist='neutral'
				eFlag=0
				if existFlag:
					eFlag=existFlag.flag
				if eVote>0:
					exist='up'
				elif eVote<0:
					exist='down'
				self.response.out.write("{'ups':'"+str(smile.ups)+"','downs':'"+str(smile.downs)+"','myVote':'"+str(exist)+"','flag':'"+str(eFlag)+"'}")

def main():
	application = webapp.WSGIApplication([('/ajax/checkVote',checkVote),
	('/ajax/ajaxVote',ajaxVote),
	('/ajax/ajaxEmail',ajaxEmail),
	('/ajax/ajaxFlag',ajaxFlag),
	('/ajax/getMore',getMore)],
                                       debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()