import os
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import mail
import jinja2
import webapp2
import datetime
import time
import uuid
import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class Resource(ndb.Model):
	resourceId =  ndb.StringProperty(indexed=True)
	resourceName = ndb.StringProperty(indexed=True)
	startTime = ndb.TimeProperty(indexed=False)
	endTime = ndb.TimeProperty(indexed=False)
	tags = ndb.StringProperty(indexed=False, repeated = True)
	owner = ndb.StringProperty(indexed=True)
	lastReservationTime = ndb.DateTimeProperty(indexed=True)
	count = ndb.IntegerProperty(indexed=False)
	
def getAllResources():
	resources_query = Resource.query()
	allResources = resources_query.order(-Resource.lastReservationTime).fetch()
	return allResources
	
def getResourcesByUser(user):
    resources_query = Resource.query(Resource.owner == str(user))
    userResources = resources_query.fetch()
    return userResources
	
def getResourceById(id):
    resources_query = Resource.query(Resource.resourceId == id)
    namedResource = resources_query.fetch()
    return namedResource[0]
	
class Reservation(ndb.Model):
	reservationId = ndb.StringProperty(indexed=True)
	resourceId =  ndb.StringProperty(indexed=True)
	resourceName =  ndb.StringProperty(indexed=True)
	startTime = ndb.DateTimeProperty(indexed=True)
	endTime = ndb.DateTimeProperty(indexed=True)
	duration = ndb.TimeProperty(indexed=False)
	reservationTime = ndb.DateTimeProperty(indexed=False)
	user = ndb.StringProperty(indexed=True)
	
def getAllReservations():
	reservations_query = Reservation.query()
	allReservations = reservations_query.order(Reservation.startTime, Reservation.endTime).fetch()
	return allReservations
	
def getReservationsByUser(user):
	reservations_query = Reservation.query(Reservation.user == str(user))
	reservations = reservations_query.order(Reservation.user).order(Reservation.startTime, Reservation.endTime).fetch()
	return reservations

def getReservationById(id):
	reservations_query = Reservation.query(Reservation.reservationId == id)
	reservations = reservations_query.fetch()
	return reservations[0]
	
def getReservationsByResource(resource):
	reservations_query = Reservation.query(Reservation.resourceId == resource.resourceId)
	reservations = reservations_query.order(Reservation.resourceId).order(Reservation.startTime, Reservation.endTime).fetch()
	return reservations
	
def getReservationsByUserTime(user):
	currentTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
	reservations_query = Reservation.query(Reservation.user == str(user), Reservation.endTime >= currentTime)
	reservations = reservations_query.order(Reservation.user, Reservation.endTime).order(Reservation.user,Reservation.startTime, Reservation.endTime).fetch()
	logging.info("hi");
	logging.info(reservations);
	return reservations
	
def getReservationsByResourceTime(resource):
	currentTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
	reservations_query = Reservation.query(Reservation.resourceId == resource.resourceId, Reservation.endTime >= currentTime);
	reservations = reservations_query.order(Reservation.resourceId, Reservation.endTime).order(Reservation.startTime, Reservation.endTime).fetch()
	return reservations
	
class MainPage(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user:
			nickname = user.nickname()
			all_resources = getAllResources();
			user_resources = getResourcesByUser(user);
			user_reservations = getReservationsByUserTime(user);
			url_logout = users.create_logout_url(self.request.uri);
			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout,
				'user_resources': user_resources,
				'all_resources': all_resources,
				'user_reservations': user_reservations
				}
			template = JINJA_ENVIRONMENT.get_template('Index.html')
			self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class AddResourcePage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout
				}
			
			template = JINJA_ENVIRONMENT.get_template('AddResource.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
			
	def post(self):
		startTime = self.request.get('startTime');
		endTime = self.request.get('endTime');
		
		tagsString = self.request.get('tags');
		tags = tagsString.split(" ");
		tags = [ str(tag).strip() for tag in tags ];

		resource = Resource();
		resource.resourceId = str(uuid.uuid4());
		resource.resourceName = self.request.get('resourceName');
		resource.startTime = datetime.datetime.strptime(startTime, '%H:%M').time();
		resource.endTime = datetime.datetime.strptime(endTime, '%H:%M').time();
		resource.lastReservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
		resource.tags = tags;
		resource.owner = str(users.get_current_user());
		resource.count = 0;
		resource.put();
		logging.info(resource);
		self.redirect('/');
		
class EditResourcePage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);
			
			tags = "";
			for t in resource.tags:
				tags = tags + " " + str(t).strip();
				
			startTime = resource.startTime.strftime("%H:%M");
			endTime = resource.endTime.strftime("%H:%M");
			
			
			template_values = {
				'user': user,
				'user_email': user.email(),
				'nickname' : nickname,
				'resource': resource,
				'tags': tags.strip(),
				'startTime': startTime,
				'endTime': endTime,
				'url_logout': url_logout
				}
			
			template = JINJA_ENVIRONMENT.get_template('EditResource.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
			
	def post(self):
		startTime = self.request.get('startTime');
		endTime = self.request.get('endTime');
		
		tagsString = self.request.get('tags');
		tags = tagsString.split(" ");
		tags = [ str(tag).strip() for tag in tags ];

		resourceId = self.request.GET['resourceId']
		resource = getResourceById(resourceId);
		resource.resourceName = self.request.get('resourceName');
		resource.startTime = datetime.datetime.strptime(startTime, '%H:%M').time();
		resource.endTime = datetime.datetime.strptime(endTime, '%H:%M').time();
		resource.lastReservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
		resource.tags = tags;
		resource.owner = str(users.get_current_user());
		resource.put();
		for reservation in getReservationsByResource(resource):
			reservation.resourceName = resource.resourceName;
			reservation.put();
		self.redirect('/');

class TagPage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			tag = self.request.GET['tag']
			resources = getAllResources()
			taggedResources = []
			for r in resources:
				for t in r.tags:
					if tag.lower() == t.lower():
						taggedResources.append(r)

			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout,
				'tag': tag,
				'tagged_resources': taggedResources
				}
			
			template = JINJA_ENVIRONMENT.get_template('Tag.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
	
class ResourcePage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);
			reservations = getReservationsByResourceTime(resource);
			
			template_values = {
				'user': user,
				'user_email': user.email(),
				'nickname' : nickname,
				'resource': resource,
				'reservations' : reservations,
				'url_logout': url_logout
				}
			
			template = JINJA_ENVIRONMENT.get_template('Resource.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
	

class AddReservationPage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);

			template_values = {
				'user': user,
				'user_email': user.email(),
				'nickname' : nickname,
				'resource': resource,
				'url_logout': url_logout
				}
			
			template = JINJA_ENVIRONMENT.get_template('AddReservation.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
			
	def post(self):
		user = users.get_current_user()
		if user:
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);
			
			reservation = Reservation();
			reservation.reservationId = str(uuid.uuid4());
			reservation.resourceId = resource.resourceId;
			reservation.resourceName = resource.resourceName;
			startTime = self.request.get('startTime');
			reservation.startTime = datetime.datetime.strptime(startTime, '%m-%d-%Y %H:%M');
			duration = self.request.get('duration');
			reservation.duration = datetime.datetime.strptime(duration, '%H:%M').time()
			reservation.endTime = reservation.startTime + datetime.timedelta(hours = reservation.duration.hour, minutes = reservation.duration.minute);
			reservation.reservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
			reservation.user = str(user);
			reservation.put();

			resource.count = resource.count + 1;
			resource.lastReservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4);
			resource.put();
			
			self.redirect('/');
			
		else:
			self.redirect(users.create_login_url(self.request.uri))
			
class DeleteReservationPage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			reservationId = self.request.GET['reservationId']
			reservation = getReservationById(reservationId);

			template_values = {
				'user': user,
				'user_email': user.email(),
				'nickname' : nickname,
				'reservation': reservation,
				'url_logout': url_logout
				}
			
			template = JINJA_ENVIRONMENT.get_template('DeleteReservation.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))
			
	def post(self):
		user = users.get_current_user()
		if user:
			reservationId = self.request.GET['reservationId']
			reservation = getReservationById(reservationId);
			reservation.key.delete();
			self.redirect('/');
			
		else:
			self.redirect(users.create_login_url(self.request.uri))
						
class UserPage(webapp2.RequestHandler):

    def get(self):
        #Checks for active Google session
        user = users.get_current_user()
        if user:
			nickname = user.nickname()
			owner = self.request.GET['user']
			user_resources = getResourcesByUser(owner);
			user_reservations = getReservationsByUserTime(owner);
			url_logout = users.create_logout_url(self.request.uri);
			template_values = {
				'user': user,
				'user_email': user.email(),
				'owner': owner,
				'nickname' : nickname,
				'url_logout': url_logout,
				'user_resources': user_resources,
				'user_reservations': user_reservations
				}
			template = JINJA_ENVIRONMENT.get_template('User.html')
			self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

app = webapp2.WSGIApplication([
    ('/', MainPage),
	('/AddResource', AddResourcePage),
	('/EditResource', EditResourcePage),
	('/Tag', TagPage),
	('/Resource', ResourcePage),
	('/AddReservation', AddReservationPage),
	('/DeleteReservation', DeleteReservationPage),
	('/User', UserPage)
], debug=True)
