import os
import jinja2
import webapp2
import datetime
import time
import uuid
import logging
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import mail

RSS_FLAG = False;

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
	reservationTime = ndb.DateTimeProperty(indexed=True)
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
	
def getReservationsByResourceDay(resource, currentTime):
	currentDayStart = currentTime - datetime.timedelta(hours = currentTime.time().hour, minutes = currentTime.time().minute);
	reservations_query = Reservation.query(Reservation.resourceId == resource.resourceId, Reservation.startTime >= currentDayStart)
	reservations = reservations_query.fetch()
	
	logging.info(currentDayStart);
	logging.info(reservations);
	
	
	return reservations
	
def getReservationsByUserTime(user):
	currentTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
	reservations_query = Reservation.query(Reservation.user == str(user), Reservation.endTime >= currentTime)
	reservations = reservations_query.order(Reservation.user, Reservation.endTime).order(Reservation.user,Reservation.startTime, Reservation.endTime).fetch()
	return reservations
	
def getReservationsByResourceTime(resource):
	currentTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
	reservations_query = Reservation.query(Reservation.resourceId == resource.resourceId, Reservation.endTime >= currentTime);
	reservations = reservations_query.order(Reservation.resourceId, Reservation.endTime).order(Reservation.startTime, Reservation.endTime).fetch()
	return reservations
	
def getAllReservationsStartingNow():
	currentTimeBefore1 = datetime.datetime.now() - datetime.timedelta(hours = 4, minutes = 1)
	currentTime = datetime.datetime.now() - datetime.timedelta(hours = 4)
	reservations_query = Reservation.query(Reservation.startTime > currentTimeBefore1, Reservation.startTime <= currentTime);
	reservations = reservations_query.fetch()
	return reservations

	
class MainPage(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user:
			nickname = user.nickname()
			all_resources = getAllResources();
			user_resources = getResourcesByUser(user.email());
			user_reservations = getReservationsByUserTime(user.email());
			url_logout = users.create_logout_url(self.request.uri);
			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout,
				'user_resources': user_resources,
				'all_resources': all_resources,
				'user_reservations': user_reservations,
				'rss_flag': RSS_FLAG
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
		resource.owner = str(users.get_current_user().email());
		resource.count = 0;
		resource.put();
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
		resource.owner = str(users.get_current_user().email());
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
				'url_logout': url_logout,
				'rss_flag': RSS_FLAG
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
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri)
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);
			
			startTimeString = self.request.get('startTime');
			startTime = datetime.datetime.strptime(startTimeString, '%m-%d-%Y %H:%M');
			durationString = self.request.get('duration');
			duration = datetime.datetime.strptime(durationString, '%H:%M').time();
			endTime = startTime + datetime.timedelta(hours = duration.hour, minutes = duration.minute);
			reservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4);
			
			error_flag = False;
			
			if(startTime < reservationTime):
				error_flag = True;
				error_msg = "Start Time is before the Current Time. We do not support past reservations."
			
			if(not error_flag):
			
				userReservations = getReservationsByUser(user.email());
				
				for userR in userReservations:
					if( (startTime >= userR.startTime and startTime < userR.endTime) or
						(endTime > userR.startTime and endTime <= userR.endTime) or
						( startTime <= userR.startTime and endTime >= userR.endTime)):
							error_flag = True;
							error_msg = "You already have a reservation coming up during this requested time interval. Reservations cannot overlap.";
			
			if(not error_flag):
			
				resourceReservations = getReservationsByResourceDay(resource, startTime);
				
				for resourceR in resourceReservations:
					if( (startTime >= resourceR.startTime and startTime < resourceR.endTime) or
						(endTime > resourceR.startTime and endTime <= resourceR.endTime) or
						( startTime <= resourceR.startTime and endTime >= resourceR.endTime)):
							error_flag = True;
							error_msg = "Resource already has a reservation for the full or part of the requested time interval. Cannot be Booked";
			
			
			if error_flag:
				template_values = {
					'user': user,
					'user_email': user.email(),
					'nickname' : nickname,
					'resource': resource,
					'url_logout': url_logout,
					'start_time': startTimeString,
					'duration': durationString,
					'error_flag': error_flag,
					'error_msg': error_msg
				}
			
				template = JINJA_ENVIRONMENT.get_template('AddReservation.html')
				self.response.write(template.render(template_values))
			else :
			
				reservation = Reservation();
				reservation.reservationId = str(uuid.uuid4());
				reservation.resourceId = resource.resourceId;
				reservation.resourceName = resource.resourceName;
				reservation.startTime = startTime;
				reservation.duration = duration;
				reservation.endTime = endTime;
				reservation.reservationTime = reservationTime;
				reservation.user = str(user.email());
				reservation.put();

				resource.count = resource.count + 1;
				resource.lastReservationTime = datetime.datetime.now() - datetime.timedelta(hours = 4);
				resource.put();
				
				message = mail.EmailMessage(
					sender="ReserveBook@reservebook-ost.appspotmail.com",
					subject="New Reservation");

				message.to = str(user.email());
    
				message.body = """Hi """ + user.nickname() + """,
Your reservation for """ + resource.resourceName + """ at """ + str(reservation.startTime) + """ - """ + str(reservation.endTime) + """ has been Confirmed.
Thanks.
ReserveBook (jm6474@nyu.edu)"""

				try:
					message.send();
				except:
					logging.info(message);
			
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
			resource = getResourceById(reservation.resourceId);
			resource.count -= 1;
			resource.put();
			self.redirect('/');
			
		else:
			self.redirect(users.create_login_url(self.request.uri))
						
class UserPage(webapp2.RequestHandler):

    def get(self):
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
			
class GenerateRssPage(webapp2.RequestHandler):

    def get(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname()
			url_logout = users.create_logout_url(self.request.uri);
			resourceId = self.request.GET['resourceId']
			resource = getResourceById(resourceId);
			reservations = getReservationsByResource(resource);
			
			rssString = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n";
			rssString += "<rss version=\"2.0\">\n";
			rssString += "<channel>\n";
			rssString += "\t<Resource>\n";
			rssString += "\t\t<ResourceId>" + resource.resourceId + "</ResourceId>\n";
			rssString += "\t\t<ResourceName>" + resource.resourceName + "</ResourceName>\n";
			rssString += "\t\t<Availability>\n";
			rssString += "\t\t\t<StartTime>" + str(resource.startTime) + "</StartTime>\n";
			rssString += "\t\t\t<EndTime>" + str(resource.endTime) + "</EndTime>\n";
			rssString += "\t\t</Availability>\n";
			rssString += "\t\t<TotalReservations>" + str(resource.count) + "</TotalReservations>\n";
			rssString += "\t\t<Owner>" + resource.owner + "</Owner>\n";
			rssString += "\t\t<LastReservationTime>" + str(resource.lastReservationTime) + "</LastReservationTime>\n";
			
			rssString += "\t\t<Tags>\n";
			for t in resource.tags:
				rssString += "\t\t\t<Tag>" + str(t).strip() + "</Tag>\n";
			rssString += "\t\t</Tags>\n";
			
			rssString += "\t\t<Reservations>\n";
			for r in reservations:
				rssString += "\t\t\t<Reservation>\n";
				rssString += "\t\t\t\t<ReservationId>" + r.reservationId + "</ReservationId>\n";
				rssString += "\t\t\t\t<StartTime>" + str(r.startTime) + "</StartTime>\n";
				rssString += "\t\t\t\t<EndTime>" + str(r.endTime) + "</EndTime>\n";
				rssString += "\t\t\t\t<Duration>" + str(r.duration) + "</Duration>\n";
				rssString += "\t\t\t\t<ReservationTime>" + str(r.reservationTime) + "</ReservationTime>\n";
				rssString += "\t\t\t\t<User>" + r.user + "</User>\n";
				rssString += "\t\t\t</Reservation>\n";
			rssString += "\t\t</Reservations>\n";
			
			rssString += "\t</Resource>\n";
			rssString += "</channel>\n";
			rssString += "</rss>\n";
			
			template_values = {
				'resource': resource,
				'rss_string': rssString,
				'nickname' : nickname,
				'url_logout': url_logout,
				'user': user,
				'user_email': user.email()
				}
			template = JINJA_ENVIRONMENT.get_template('Rss.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))

			
class GenerateReminderMail(webapp2.RequestHandler):

	def get(self):
		reservations = getAllReservationsStartingNow();
		for reservation in reservations:
			message = mail.EmailMessage(
						sender="ReserveBook@reservebook-ost.appspotmail.com",
						subject="Reservation Starting");

			message.to = str(reservation.user);
    
			message.body = """Hi,
Your reservation for """ + reservation.resourceName + """ is starting Now.
Thanks.
ReserveBook (jm6474@nyu.edu)"""
			
			try:
				message.send();
			except:
				logging.info(message);
			
			
class GenerateSearchNamePage(webapp2.RequestHandler):

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
			
			template = JINJA_ENVIRONMENT.get_template('SearchName.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))		

	def post(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname();
			url_logout = users.create_logout_url(self.request.uri);
			searchName = startTimeString = self.request.get('searchName');
			
			resources = getAllResources();
			resultResources = [];
			
			for r in resources:
				if searchName.lower() in r.resourceName.lower():
					resultResources.append(r);
			
			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout,
				'searchName': searchName,
				'resources': resultResources
				}
			
			template = JINJA_ENVIRONMENT.get_template('SearchName.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))		
					
					
class GenerateSearchAvailabilityPage(webapp2.RequestHandler):

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
			
			template = JINJA_ENVIRONMENT.get_template('SearchAvailability.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))		

	def post(self):
		user = users.get_current_user()
		if user:
			nickname = user.nickname();
			url_logout = users.create_logout_url(self.request.uri);
			
			startTimeString = self.request.get('startTime');
			startTime = datetime.datetime.strptime(startTimeString, '%H:%M');
			durationString = self.request.get('duration');
			duration = datetime.datetime.strptime(durationString, '%H:%M').time();
			endTime = startTime + datetime.timedelta(hours = duration.hour, minutes = duration.minute);
			
			startTime = startTime.time();
			endTime = endTime.time();
			
			
			resources = getAllResources();
			resultResources = [];
			
			for r in resources:
				if r.startTime <= startTime and r.endTime >= endTime:
					resultResources.append(r);
			
			template_values = {
				'user': user,
				'nickname' : nickname,
				'url_logout': url_logout,
				'startTime': startTimeString,
				'duration': durationString,
				'resources': resultResources
				}
			
			template = JINJA_ENVIRONMENT.get_template('SearchAvailability.html')
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
	('/User', UserPage),
	('/GenerateRss', GenerateRssPage),
	('/SendReminderMail', GenerateReminderMail),
	('/SearchName', GenerateSearchNamePage),
	('/SearchAvailability', GenerateSearchAvailabilityPage)
], debug=True)
