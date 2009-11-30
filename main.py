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
# images on about page
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

from google.appengine.api import quota
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.api import memcache

import models

class Smiles(webapp.RequestHandler):
	def post(self):
		imageData=str(self.request.get('imageData'))
		if imageData:
			if imageData[0:14]=='data:image/png':
				temp=models.Info.all().get()
				if not temp:
					temp= models.Info()
					temp.name='count'
					temp.value='0'
				temp.value=str(int(temp.value)+1)
				temp.put()
				smile=models.Smiley()
				smile.ups=0
				smile.downs=0
				smile.votes=0
				smile.flags=0
				smile.create_at=datetime.datetime.now()+datetime.timedelta(hours=-4)
				if users.get_current_user():
					cur_user=users.get_current_user()
					smile.author=cur_user
					smile.authorID=cur_user.user_id()
				smile.image=imageData
				smile.put()
				self.redirect('/')

class newRSS(webapp.RequestHandler):
	"""docstring for newRSS"""
	def get(self):
		smiles=models.Smiley.all().order('-create_at').fetch(10)
		self.response.headers["Content-Type"] = "application/rss+xml"
		path = os.path.join(os.path.dirname(__file__), 'templates/newRSS.html')
		self.response.out.write(template.render(path,{'smiles':smiles}))

class Voting(webapp.RequestHandler):
	"""docstring for Voting"""
	def get(self):
		maxe=int(models.Info.all().get().value)
		shift=random.randint(0,1000000)%maxe
		smile=models.Smiley.all().fetch(1,shift)
 		if not smile[0].flags:
			smile[0].flags=0
			smile[0].put()
		while smile[0].flags:
			shift=random.randint(0,1000000)%maxe
			smile=models.Smiley.all().fetch(1,shift)			
		user=users.get_current_user()
		smileID = int(smile[0].key().id())
		if smile:
			eVote=0
			if user:
				existVote=memcache.get("user"+user.nickname()+"smile"+str(smile[0].key().id()))
				if existVote is None:
					existVoteQ = models.db.GqlQuery("SELECT * FROM Votes WHERE voter = :1 AND smiley_id = :2 ",user,smile[0].key().id())		
					existVote=existVoteQ.get()
				if existVote:
					if not memcache.set("user"+user.nickname()+"smile"+str(smile[0].key().id()),existVote,3600):
						logging.error("Memcache set failed. Random Vote")
					eVote=existVote.vote
			img=smile[0].image
			path = os.path.join(os.path.dirname(__file__), 'templates/vote.html')
	   		self.response.out.write(template.render(path,{'info':smile[0],'user':user,'eVote':int(eVote)}))
		else:
			self.redirect('/vote')		


class ViewSmiles(webapp.RequestHandler):
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
							logging.error("Memcache set failed. View Smile")
						eVote=existVote.vote
			path = os.path.join(os.path.dirname(__file__), 'templates/view.html')
	   		self.response.out.write(template.render(path,{'info':smile,'user':user,'eVote':int(eVote)}))
		else:
			self.redirect('/more')

class MoreSmiles(webapp.RequestHandler):
	"""docstring for MoreSmiles"""
	def get(self):
		try:
			page=int(self.request.get("page"))
			if page<1:
				page=1
		except:
			page=1
		user=users.get_current_user()
#		start = quota.get_request_cpu_usage()
		smiles_q=models.Smiley.all().order('flags').filter('flags',0).order('-create_at')
#		stepa = quota.get_request_cpu_usage()
		smiles=smiles_q.fetch(12,(page-1)*12)
#		stepb = quota.get_request_cpu_usage()
		path = os.path.join(os.path.dirname(__file__), 'templates/more.html')
#		stepc = quota.get_request_cpu_usage()
   		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page,'smilelength':len(smiles),'pageName':'more'}))
#		stepd = quota.get_request_cpu_usage()
#		logging.info("create GQL query: %d" % (start - stepa))
#		logging.info("fetch GQL query: %d" % (stepa - stepb))
#		logging.info("set path for template: %d" % (stepb - stepc))
#		logging.info("call template: %d" % (stepc - stepd))
	

class TopSmiles(webapp.RequestHandler):
	def get(self):
		try:
			page=int(self.request.get("page"))
			if page<1:
				page=1			
		except:
			page=1
		user=users.get_current_user()
		smiles_q=models.Smiley.all().order('-votes')
		smiles=smiles_q.fetch(12,(page-1)*12)
		path = os.path.join(os.path.dirname(__file__), 'templates/top.html')
   		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page,'smilelength':len(smiles),'pageName':'top'}))

class AllTop(webapp.RequestHandler):
	def get(self):
		page=1
		user=users.get_current_user()
		smiles_q=models.Smiley.all().order('-votes')
		smiles=smiles_q.fetch(120)
		path = os.path.join(os.path.dirname(__file__), 'templates/more.html')
   		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page}))

class Terms(webapp.RequestHandler):
	"""docstring for Terms"""
	def get(self):
		user=users.get_current_user()
		path = os.path.join(os.path.dirname(__file__), 'templates/terms.html')
	   	self.response.out.write(template.render(path,{'user':user}))
		

class MainHandler(webapp.RequestHandler):
  def get(self):
	user=users.get_current_user()
	path = os.path.join(os.path.dirname(__file__), 'templates/draw.html')
   	self.response.out.write(template.render(path,{'user':user}))


class AllContests(webapp.RequestHandler):
	"""docstring for Contests"""
	def get(self):
		user=users.get_current_user()
		contests=models.Contests().all().fetch(100)
		path = os.path.join(os.path.dirname(__file__), 'templates/allContest.html')
   		self.response.out.write(template.render(path,{'user':user,'contests':contests}))

class ContestEntries(webapp.RequestHandler):
	"""docstring for ContestEntries"""
	def get(self):
		try:
			page=int(self.request.get("page"))
			if page<1:
				page=1			
		except:
			page=1
		contest_id=cgi.escape(self.request.get("contest_id"))
		if contest_id:
			user=users.get_current_user()
			contest=models.Contests.get_by_id(int(contest_id))
			entries=models.Entries().all().order('-submitted').filter('contest',contest).fetch(12,(page-1)*12)
			path = os.path.join(os.path.dirname(__file__), 'templates/entries.html')
			self.response.out.write(template.render(path,{'contest':contest,'smiles':entries,'user':user,'page':page,'smilelength':len(entries),'pageName':'entries'}))
		else:
			self.redirect('/AllContests')
	
	
class enterLogin(webapp.RequestHandler):
	"""docstring for enterLogin"""
	def get(self):
		contest_id=cgi.escape(self.request.get("contest_id"))
		if contest_id:
			self.redirect(users.create_login_url('/enter?contest_id='+str(contest_id)))
		else:
			self.redirect('/AllContest')

class retrieveDraw(webapp.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			memcache_id=int(self.request.get("memID"))
			if memcache_id:
				tempImage=memcache.get("tempsmile"+str(memcache_id))
				if tempImage is not None:
					temp=models.Info.all().get()
					if not temp:
						temp= models.Info()
						temp.name='count'
						temp.value='0'
					temp.value=str(int(temp.value)+1)
					temp.put()
					smile=models.Smiley()
					smile.ups=0
					smile.downs=0
					smile.votes=0
					smile.flags=0
					smile.create_at=datetime.datetime.now()+datetime.timedelta(hours=-4)
					smile.author=user
					smile.authorID=user.user_id()
					smile.image=tempImage
					smile.put()
					memcache.delete("tempsmile"+str(memcache_id))
					self.redirect('/')
				else:
					self.redirect('/')
			else:
				self.redirect('/')					
		else:
			self.redirect('/')

class loginDraw(webapp.RequestHandler):
	"""docstring for loginEnter"""
	def post(self):
		imageData=str(self.request.get('imageData'))
		if imageData:
			if imageData[0:14]=='data:image/png':
				tempid=random.randint(0,1000000000)
				if not memcache.set("tempsmile"+str(tempid),imageData,7200):
					logging.error("Memcache set failed. Temp Image")
					self.redirect('/')
				else:
					self.redirect(users.create_login_url('/retrieveDraw?memID='+str(tempid)))
			else:	
				self.redirect('/')
		else:
			self.redirect('/')

class Enter(webapp.RequestHandler):
	def get(self):
		user=users.get_current_user()
		if user:
			contest_id=cgi.escape(self.request.get("contest_id"))
			if contest_id:
				contest=models.Contests.get_by_id(int(contest_id))
				path = os.path.join(os.path.dirname(__file__), 'templates/enter.html')
				self.response.out.write(template.render(path,{'contest':contest,'user':user}))
			else:
				self.redirect('/AllContests')
	def post(self):
		user=users.get_current_user()
		if user:
			imageData=str(self.request.get('imageData'))
			if imageData:
				if imageData[0:14]=='data:image/png':
					temp=models.Info.all().get()
					if not temp:
						temp= models.Info()
						temp.name='count'
						temp.value='0'
					temp.value=str(int(temp.value)+1)
					entry=models.Entries()
					contest_id=int(self.request.get("contest_id"))
					contest=models.Contests.get_by_id(int(contest_id))
					contest.num_entries=contest.num_entries+1
					smile=models.Smiley()
					smile.ups=0
					smile.downs=0
					smile.votes=0
					smile.flags=0
					smile.author=user
					smile.authorID=user.user_id()
					smile.image=imageData
					smile.create_at=datetime.datetime.now()+datetime.timedelta(hours=-4)
					smile.put()
					entry.smiley=smile
					entry.author=user
					entry.contest=contest
					entry.rating=0
					entry.put()
					temp.put()
					contest.put()
					self.redirect('/entries?contest_id='+str(contest_id))
			
			
			
		
		

class User(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'templates/user.html')
		try:
			page=int(self.request.get("page"))
			if page<1:
				page=1
		except:
			page=1
		user=users.get_current_user()
		smiley_id=cgi.escape(self.request.get("smiley_id"))
		author=user
		if not smiley_id:
			smile_q=models.db.GqlQuery("SELECT * FROM Smiley where author =:1 order by create_at desc",user)
			smile_id=0
		if smiley_id:
			smile=models.Smiley.get_by_id(int(smiley_id))
			if smile:
				smile_q=models.db.GqlQuery("SELECT * FROM Smiley where author =:1 order by create_at desc",smile.author)
				author=smile.author
			else:
				smile_q=models.db.GqlQuery("SELECT * FROM Smiley where author =:1 order by create_at desc",user)
		smiles=smile_q.fetch(12,(page-1)*12)
		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page,'smilelength':len(smiles),'smiley_id':smiley_id,'author':author,'pageName':'user'}))
		
			
				
   		
class about(webapp.RequestHandler):
  def get(self):
	user=users.get_current_user()
	path = os.path.join(os.path.dirname(__file__), 'templates/about.html')
   	self.response.out.write(template.render(path,{'user':user}))

class Login(webapp.RequestHandler):
	def get(self):
		self.redirect(users.create_login_url('/'))

class Logout(webapp.RequestHandler):
	def get(self):
		self.redirect(users.create_logout_url('/'))

def profile_main():
	 # This is the main function for profiling 
	 # We've renamed our original main() above to real_main()
	 import cProfile, pstats, StringIO
	 prof = cProfile.Profile()
	 prof = prof.runctx("real_main()", globals(), locals())
	 stream = StringIO.StringIO()
	 stats = pstats.Stats(prof, stream=stream)
	 stats.sort_stats("time")  # Or cumulative
	 stats.print_stats(80)  # 80 = how many to print
	 # The rest is optional.
	 # stats.print_callees()
	 # stats.print_callers()
	 logging.info("Profile data:\n%s", stream.getvalue())
	
def real_main():
  application = webapp.WSGIApplication([('/', MainHandler),
										('/post',Smiles),
										('/view',ViewSmiles),
										('/more',MoreSmiles),
										('/vote',Voting),
										('/newRSS',newRSS),
										('/top',TopSmiles),
										('/user',User),
										('/all',AllTop),
										('/enter',Enter),
										('/tos',Terms),
										('/loginDraw',loginDraw),
										('/retrieveDraw',retrieveDraw),
										('/enterLogin',enterLogin),
										('/AllContests',AllContests),
										('/entries',ContestEntries),
										('/about',about),
										('/login',Login),
										('/logout',Logout)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  real_main()
