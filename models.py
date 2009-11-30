from google.appengine.ext import db

class Info(db.Model):
	name=db.TextProperty()
	value=db.TextProperty()

class Users(db.Model):
	userinfo=db.UserProperty()
	avatar=db.TextProperty()

class Smiley(db.Model):
	author=db.UserProperty()
	authorID=db.TextProperty()
	image=db.TextProperty()
	create_at=db.DateTimeProperty()
	update_at=db.DateTimeProperty(auto_now=True)
	ups=db.IntegerProperty()
	downs=db.IntegerProperty()
	flags=db.IntegerProperty()
	votes=db.IntegerProperty()

class Flags(db.Model):
	voter=db.UserProperty()
	smiley_id=db.IntegerProperty()
	flag=db.IntegerProperty()
	create_at=db.DateTimeProperty(auto_now_add=True)
	update_at=db.DateTimeProperty(auto_now=True)

class Votes(db.Model):
	voter=db.UserProperty()
	smiley_id=db.IntegerProperty()
	vote=db.IntegerProperty()
	create_at=db.DateTimeProperty(auto_now_add=True)
	update_at=db.DateTimeProperty(auto_now=True)

class Contests(db.Model):
	name=db.TextProperty()
	desc=db.TextProperty()
	start_date=db.DateProperty()
	end_date=db.DateProperty()
	num_entries=db.IntegerProperty()
	active=db.BooleanProperty()

class Entries(db.Model):
	smiley=db.ReferenceProperty(Smiley)
	author=db.UserProperty()
	contest=db.ReferenceProperty(Contests)
	submitted=db.DateTimeProperty(auto_now=True)
	rating=db.RatingProperty()