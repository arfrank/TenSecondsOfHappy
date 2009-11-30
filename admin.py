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

class DeleteDrawing(webapp.RequestHandler):
	def get(self):
		if users.is_current_user_admin():
			user=users.get_current_user()
			try:
				page=int(self.request.get("page"))
				if page<1:
					page=1
			except:
				page=1
			smiles_q=models.Smiley.all().order('-create_at')
			smiles=smiles_q.fetch(12,(page-1)*12)
			path = os.path.join(os.path.dirname(__file__), 'templates/adminDelete.html')
	   		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page}))		
		else:
			self.redirect('/')

	def post(self):
		if users.is_current_user_admin():
			smile_id=int(self.request.get("smileid"))
			temp=models.Smiley.get_by_id(smile_id)
			models.db.delete(temp)
			temp=models.Info.all().get()
			temp.value=str(int(temp.value)-1)
			temp.put()				

class AddContest(webapp.RequestHandler):
	"""docstring for AddContest"""
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'templates/addContest.html')
   		self.response.out.write(template.render(path,{}))
	def post(self):
		newContest=models.Contests()
		newContest.name=str(cgi.escape(self.request.get("name")))
		newContest.num_entries=0
		newContest.desc=str(cgi.escape(self.request.get("desc")))
		tempstart=datetime.datetime.strptime(str(cgi.escape(self.request.get("start"))),"%m-%d-%y")
		tempend=datetime.datetime.strptime(str(cgi.escape(self.request.get("end"))),"%m-%d-%y")
		newContest.start_date=datetime.date(tempstart.year,tempstart.month,tempstart.day)
		newContest.end_date=datetime.date(tempend.year,tempend.month,tempend.day)
		newContest.active=bool(cgi.escape(self.request.get("activate")))
		newContest.put()
		self.redirect('/admin/changeContest')
		

class ChangeContest(webapp.RequestHandler):
	def get(self):
		contest_id=self.request.get("id")
		if contest_id:
			contests=models.Contests.get_by_id(int(self.request.get("id"))) 
			if contests is not None:
				path = os.path.join(os.path.dirname(__file__), 'templates/changeContest.html')
				self.response.out.write(template.render(path,{'contests':contests}))			
		else:
			contests=models.Contests().all().fetch(100)
			path = os.path.join(os.path.dirname(__file__), 'templates/adminallContest.html')
			self.response.out.write(template.render(path,{'contests':contests}))
	def post(self):
		contest_id=self.request.get("key")
		if contest_id:
			contests=models.Contests.get_by_id(int(contest_id)) 
			if contests is not None:
				contests.name=str(cgi.escape(self.request.get("name")))
				contests.desc=str(cgi.escape(self.request.get("desc")))
				tempstart=datetime.datetime.strptime(str(cgi.escape(self.request.get("start"))),"%m-%d-%y")
				tempend=datetime.datetime.strptime(str(cgi.escape(self.request.get("end"))),"%m-%d-%y")
				contests.start_date=datetime.date(tempstart.year,tempstart.month,tempstart.day)
				contests.end_date=datetime.date(tempend.year,tempend.month,tempend.day)
				contests.active=bool(cgi.escape(self.request.get("activate")))
				contests.put()
				self.redirect('/admin/changeContest')
		
class FlagDraw(webapp.RequestHandler):
	"""docstring for FlagDraw"""
	def get(self):
		if users.is_current_user_admin():
			user=users.get_current_user()
			try:
				page=int(self.request.get("page"))
				if page<1:
					page=1
			except:
				page=1
			smiles_q=models.Smiley.all().order('-create_at')
			smiles=smiles_q.fetch(12,(page-1)*12)
			path = os.path.join(os.path.dirname(__file__), 'templates/adminFlag.html')
	   		self.response.out.write(template.render(path,{'smiles':smiles,'user':user,'page':page}))		
		else:
			self.redirect('/')
		


def main():
	application = webapp.WSGIApplication([('/admin/', MainHandler),('/admin/delete',DeleteDrawing),
											('/admin/addContest',AddContest),
											('/admin/changeContest',ChangeContest),
											('/admin/flagDraw',FlagDraw)],
                                       debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()