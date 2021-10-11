
# -*- coding: utf-8 -*-

############ Django Imports ####################################
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from models import *

############ Google Imports ####################################
from google.oauth2 import id_token
from google.auth.transport import requests as googlerequests
import requests_toolbelt.adapters.appengine

from google.appengine.api import users, mail
from google.appengine.ext import webapp
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from models import *
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine


############ App Imports ####################################

import urllib, urllib2
import datetime
import pytz
import re
import requests
import json
import logging
from twilio.rest import Client
import sys, os





############ Project Settings ####################################

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Appengine sockets patch
# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()





############ Templates ####################################

def home(request):
    return render(request, "sourcebasesite/home.html")





############ User Verification ####################################

def _getClaims(request):
    '''
    Extracts Google OAuth2 Token from the HTTP_AUTHORIZATION header and constructs Google
    claims object containing user info.

    Args: HttpRequest object
    Returns: claims dict if successful, else None
    '''
    try:
        id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
        return google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST)
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return None


def verifyOrCreateUser(request):
    '''
    Verifies whether a user exists by constructing its key from the Google Oauth2 User ID 
    present in the claims dict returned by _getClaims. If not, creates and puts user 
    object in the Datastore.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
        
        userKey = ndb.Key(User, claims['sub'])
        user = userKey.get()
        
        if user:
            return HttpResponse(json.dumps({'status':'success'}))
        else:
            try:
                claims['email']
                user = User(name = claims['name'], userID = claims['sub'], email = claims['email'])
            except:
                user = User(nameame = claims['name'], userID = claims['sub'])
            user.key = userKey
            user.put()
        return HttpResponse(json.dumps({'status':'success'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err':'Sorry, there was an error.'}, status=401))




############ Google Maps ####################################

def _getGeoString(zipcode):
    '''
    Gets a geolocation based on a zipcode via the Google Maps API, and returns as 
    a joined string of latitude and longitude.

    Args: zipcode string
    Returns: 'latitude,longitude' combined string
    '''
    try:
        # Google Maps API reverse geolocation using zipcode
        GOOGLE_MAPS_KEY = Settings.get('GOOGLE_MAPS_KEY')
        getGeoLocURL = ('https://maps.googleapis.com/maps/api/geocode/' + 
            'json?key=' + GOOGLE_MAPS_KEY + '&address=' + zipcode)
        geoResponse = requests.get(getGeoLocURL)
        location = geoResponse.json()['results'][0]['geometry']['location']
        return str(location['lat']) + ',' + str(location['lng'])

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return None





############ Rain Alerts ####################################

def _getPrecipProbNextHour(geoString):
    '''
    Given a geolocation, obtains the precipitation probability for the next earliest hour
    via Dark Sky Weather API. 

    Args: geolocation as 'latitude,longitude' cobmined single string
    Returns: precipitation probability int
    '''
    try:
        DARK_SKY_KEY = Settings.get('DARK_SKY_KEY')
        excludeList = 'currently,minutely,daily,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + DARK_SKY_KEY + '/' + 
        geoString + '?exclude=' + excludeList)
        forecastResponse = requests.get(getForecastURL)
        hourlyForecast = forecastResponse.json()['hourly']
        rainProb = int(round(hourlyForecast['data'][1]['precipProbability'] * 100))
        return rainProb
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


# TODO later: implement pagination for when alert number becomes high, not required for now
# Deferred task: csrf exempt to ensure GCP Queues work
@csrf_exempt
def _alertUser(userKey):
    '''
    Given a user's key, get()s user by key and verifies whether user still has receive rain
    alert setting at time of this enqueued task's execution. If so, fetches precipitation 
    probability for the next hour and alerts user if probability is >= 30%. 

    Args: a user's Key object
    Returns: None
    '''
    try:
        # lookup by key is strongly consistent
        user = userKey.get()
        # double check that user still wants to receive alert at time of task execution
        if user.receive_rain:
            precipProbability = _getPrecipProbNextHour(user.geoString)
            if precipProbability >= 30:
                nowUTCDatetime = datetime.datetime.utcnow()
                alert = Alert(user=userKey, datetime=nowUTCDatetime, precipitation=precipProbability)
                alert.put()
                alertBody = u'\nHey {}!\n\nIn about an hour, the chance of rain will be {}%.'.format(
                    user.name, 
                    alert.precipitation)
                _sendMessage(userKey, alertBody, rainAlert=True)
        return None
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return None


# csrf exempt to ensure cron jobs work. Secured by setting login: admin in app.yaml
@csrf_exempt
def checkRainAndAlertUsers(request):
    '''
    Cron job which fetches the keys of users who are currently signed up to receive rain
    alerts, creates an iterator object based on the query, and iterates through the user
    keys, passing each to a deferred (enqueued) task _alertUser which alerts the user.
    Datastore batches get() operations, so having a task for each individual user, which 
    get()s user, isn't so bad, while allowing the app to handle large amount of users.

    Args: HttpRequest object
    Returns: HttpResponse success object if successful, error response otherwise
    '''
    try:
        userKeysQuery = User.query(User.receive_rain=='on')
        # keys_only makes this a strongly consistent query as long as index is updated, since 
        # only keys are fetced. Iterator is used on query to allow handling large # of users.
        for userKey in userKeysQuery.iter(keys_only=True):
            deferred.defer(_alertUser, userKey, _queue='alerts-queue')
            
        return HttpResponse(json.dumps({'status':'success'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err':'Sorry! There was an error!'}, status=500))


def getAlertHistory(request):
    '''
    Given a request containing a header with the appropriate authorization token, returns the
    alert history for the user corresponding to the token in the header as JSON payload containing 
    {'alerts': [{alert1}, {alert2}, ...]}, where each alert contains two keys: precipProbability 
    and datetime, ordered desc on datetime.

    Args: HttpRequest object
    Returns: HttpResponse with JSON payload
    '''
    try:
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
        userKey = ndb.Key(User, claims['sub'])
        alerts = Alert.query(Alert.user==userKey).order(-Alert.datetime).fetch()
        alertsList = []
        for alert in alerts:
            alertDict = {}
            alertDict['precipProbability'] = alert.precipitation
            alertDict['datetime'] = alert.datetime.isoformat()
            alertsList.append(alertDict)
        alertsDict = {}
        alertsDict['alerts'] = alertsList
        alerts = json.dumps(alertsDict)
        return HttpResponse(alerts)

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err':'Sorry! There was an error!'}, status=500))






############ Weather Reports ####################################

def _getWeather(geoString):
    '''
    Given a geolocation, obtains weather info via Dark Sky API and returns info as list. 

    Args: geolocation as 'latitude,longitude' cobmined single string
    Returns: list containing daily summar string, daily low temp int, daily high temp int,
    and daily precip % int.
    '''
    try:
        # Dark Sky Weather API daily forecast
        DARK_SKY_KEY = Settings.get('DARK_SKY_KEY')
        excludeList = 'currently,minutely,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + DARK_SKY_KEY + '/' + 
        geoString + '?exclude=' + excludeList)
        forecastResponse = requests.get(getForecastURL)
        hourlyForecast = forecastResponse.json()['hourly']
        dailyForecast = forecastResponse.json()['daily']
        dailySummary = hourlyForecast['summary']
        dailyRainProb = int(round(dailyForecast['data'][0]['precipProbability'] * 100))
        dailyLow = int(round(dailyForecast['data'][0]['temperatureLow']))
        dailyHigh = int(round(dailyForecast['data'][0]['temperatureHigh']))
        return [dailySummary, dailyLow, dailyHigh, dailyRainProb]
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


# Deferred task: csrf exempt to ensure GCP Queues work
@csrf_exempt
def _sendMessage(userKey, body, rainAlert=False):
    '''
    Given a user key, message body, and boolean indicating whether the message is
    a rain alert, checks user's notification settings and sends message via SMS
    and/or email depending on the notification settings.

    Args: userKey Key object, message body string, and rainAlert boolean
    Returns: HttpResponse object
    '''
    try:
        error = ''
        user = userKey.get()
        if user.receive_sms:
            try:
                authToken = Settings.get('TWILIO_AUTH_TOKEN')
                accountSID = Settings.get('TWILIO_ACCOUNT_SID')
                twilioNumber = Settings.get('TWILIO_ACCT_PHONE_NUMBER')

                client = Client(accountSID, authToken)
                message = client.messages.create(
                    body=body,
                    to= '+1' + user.phone,
                    from_=twilioNumber,
                )
            except Exception as e:
                error = "Sorry! We were not able to send you SMS at this time!:" + e

        if user.receive_email:
            if rainAlert:
                subject = 'Rain Alert'
            else:
                subject = 'Your daily weather report from Grow'

            senderAddress = 'omar.ali11231@gmail.com'
            recepientAddress = user.email
            mail.send_mail(sender=senderAddress,
                           to=recepientAddress,
                           subject=subject,
                           body=body + '\n\n' + error
                           )
        return HttpResponse(json.dumps({'status':'success'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err':'Sorry! There was an error!'}, status=500))


def _getTimeZone(zipcode):
    '''
    Given a zipcode string, gets timezone info via Zipcode API, and returns the timezone
    identifier as a string.

    Args: zipcode string
    Returns: timezone identifier string or error string as second item in tuple
    '''
    try:
        TimeZoneURL = ('https://www.zipcodeapi.com/rest/P2XWrO6FkXTl2yfjS85Wl4kHJT' +
        'XoyizlPOT1A6IjBWzWeFDWSXv3WMbOWrJ4VMMH/info.json/' + zipcode + '/degrees')
        TZResponse = requests.get(TimeZoneURL).json()
        if 'error_msg' in TZResponse:
            logging.info(TZResponse['error_msg'])
            return 'err', TZResponse['error_msg']
        elif 'timezone' in TZResponse:
            return '', TZResponse['timezone']['timezone_identifier']
        else:
            return 'err', 'Unknown error! Sorry!'
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return 'err', 'Unknown error! Sorry!'


def _getReportDatetime(timezone):
    '''
    Given a timezone identifier, constructs the appropriate datetime.datetime object for the first
    execution time of the report task. Returns in ISO 8601 format as string.

    Args: timezone identifier string
    Returns: ISO 8601 formatted datetime.datetime object representing date and time of first report
    '''
    try:
        # Tricky stuff! Be careful!

        # time right now in UTC
        nowUTCDatetime = pytz.utc.localize(datetime.datetime.utcnow(), is_dst=True)
        # user's timezone
        userTimezoneObj = pytz.timezone(timezone)
        # time right now in user's timezone
        nowUserDatetime = nowUTCDatetime.astimezone(userTimezoneObj)
        # 8 am today in user's timezone, possible time to start reporting
        possibleReportDatetime = nowUserDatetime.replace(hour=8, minute=0, second=0, microsecond=0)
        # Report signup time should be at least 10s before report time to allow time for task processing
        if possibleReportDatetime - nowUserDatetime >= datetime.timedelta(seconds=10):
            reportDatetime = possibleReportDatetime
        # otherwise, just start at 8 am next day.
        else:
            reportDatetime = possibleReportDatetime + datetime.timedelta(days=1)
        # logging.info(reportDatetime.isoformat())
        return reportDatetime.isoformat()

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


# Deferred task: csrf exempt to ensure GCP Queues work
@csrf_exempt
def _updateATriggerTask(userKey):
    '''
    Given a user's key, checks whether user is currently opting to receive reports, and whether a task
    to send reports already exists. If yes and no, respectively, a task is created, and task_exists is
    changed to True. Only if receive reports setting is off, and a task exists, a request is sent to 
    delete the task

    Args: user Key object
    Returns: ISO 8601 formatted datetime.datetime object representing date and time of first report
    '''
    try:

        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
        # TODO in future, only fetch the two attributes for this function
        user = userKey.get()

        if user.receive_reports:
            if not user.task_exists:

                reportDatetime = _getReportDatetime(user.timezone)
                # reportDatetime = '2018-09-14T12:46:47.260683-10:00'
                # Production:
                domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
                # Development:
                # domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

                addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
                '&timeSlice=1day&count=-1&url=' + domain + 
                '/endpoints/sendReport/' + 
                '&tag_ID=' + userKey.id() + '&tag_type=reports&first=' + reportDatetime + '&post=True')
                
                A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
                data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
                # Quick fix for timeout issue. Shouldn't have to deal with timeout issues, so to fix timeout 
                # problem, just send the request, and it should be executed by A Trigger.
                try:
                    addTaskResponse = requests.post(addURL, data=data, verify=True)
                except:
                    pass
                user.task_exists = True
                user.put()
        else:
            if user.task_exists:
                deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_ID=' + 
                userKey.id() + '&tag_type=reports')
                # Shouldn't have to deal with timeout issues, so to fix timeout problem, just send 
                # the request, and it should be executed by A Trigger.
                try:
                    deleteTaskResponse = requests.post(deleteURL, verify=True, timeout=20)
                except:
                    pass
                user.task_exists = False
                user.put()
        return HttpResponse()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(status=500)


# csrf exempt to allow scheduled cross-origin trigger request in. Secured via secret payload.
@csrf_exempt 
def sendReport(request):
    '''
    Given a POST request containing user ID in payload, fetch weather for the user, and enqueue a
    task that will send the appropriate message to user.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        req = request.REQUEST

        # Additional security check to make sure task was created by this app. Payload is SSL-secured.
        if Settings.get('A_TRIGGER_PAYLOAD_SECRET') != request.POST['A_TRIGGER_PAYLOAD_SECRET']:
            return HttpResponse(status=401)

        userID = request.POST['userID']
        userKey = ndb.Key(User, userID)
        user = userKey.get()
        dailySummary, dailyLow, dailyHigh, dailyRainProb = _getWeather(user.geoString)
        
        nowUTCDatetime = datetime.datetime.utcnow()

        report = Report(user=userKey, datetime=nowUTCDatetime, dailyLow=dailyLow, 
            dailyHigh=dailyHigh, summary=dailySummary, precipitation=dailyRainProb)
        report.put()

        reportBody = u'\nHey {}!\n\nHere is your forecast for today:\n\n{}\n\nDaily Low: {}\N{DEGREE SIGN}F\nDaily High: {}\N{DEGREE SIGN}F\nChance of rain: {}%'.format(
            user.name, report.summary, report.dailyLow, report.dailyHigh, report.precipitation)

        userKey = ndb.Key(User, userID)
        deferred.defer(_sendMessage, userKey, reportBody, _queue='reports-queue')
        #_sendMessage(userKey, reportBody)

        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def resendReport(request):
    '''
    Given a GET request including user token, validates user, and enqueues task to resend 
    the most recent report.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        claims = _getClaims(request)
        userKey = ndb.Key(User, claims['sub'])
        user = userKey.get()
        report = Report.query(Report.user==userKey).order(-Report.datetime).get()
        if report:
            reportBody = u'\nHey {}!\n\nHere is your forecast for today:\n\n{}\n\nDaily Low: {}\N{DEGREE SIGN}F\nDaily High: {}\N{DEGREE SIGN}F\nChance of rain: {}%'.format(
                user.name, report.summary, report.dailyLow, report.dailyHigh, report.precipitation)
            deferred.defer(_sendMessage, userKey, reportBody, _queue='reports-queue')
            return HttpResponse(json.dumps({'status':'success'}))
        else:
            return HttpResponse(json.dumps({'err':'You don\'t have any reports yet!'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        HttpResponse(status=500)





############ Update User ####################################

def _isValidPhoneNumber(phone):
    '''
    Given a US phone number as string, validates against Twilio's phone records.

    Args: US phone number as string
    Returns: is or isnt a valid number as boolean
    '''
    try:
        authToken = Settings.get('TWILIO_AUTH_TOKEN')
        accountSID = Settings.get('TWILIO_ACCOUNT_SID')
        client = Client(accountSID, authToken)
        number = client.lookups.phone_numbers('+1' + phone).fetch()
        return True
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        HttpResponse(status=500)
        return False


def _updateUserAttributes(user, post, claims, timezone):
    '''
    Given a user object, post dict, claims dict, and timezone identifier string, compares
    to user's existing info and settings, and updates if necessary, and returns boolean 
    indicating whether user was updated.

    Args: user object, post dict, claims dict, and timezone identifier string
    Returns: was user updated as boolean
    '''
    try:
        userUpdated = False

        name = claims['name']
        email = claims['email']
        phone = post['input-phone'] if 'input-phone' in post else None

        receive_reports = post['check-receive-reports'] if 'check-receive-reports' in post else None
        receive_sms = post['check-receive-sms'] if 'check-receive-sms' in post else None
        receive_email = post['check-receive-email'] if 'check-receive-email' in post else None
        receive_rain = post['check-receive-rain'] if 'check-receive-rain' in post else None

        zipcode = post['input-zip'] if 'input-zip' in post else None
        # Get geoString and save to user to save google API calls converting zipcode 
        # to geoString every time we fetch weather
        geoString = user.geoString
        if user.zipcode != zipcode or not zipcode:
            geoString = _getGeoString(zipcode)

        # Was user updated? zipcode change implies geostring and timezone changes
        userUpdated = user.name != name or user.email != email or user.phone != phone or \
        user.receive_reports != receive_reports or user.receive_sms != receive_sms or \
        user.receive_email != receive_email or user.receive_rain != receive_rain or user.zipcode != zipcode

        user.name = name
        user.email = email
        user.phone = phone
        user.receive_reports = receive_reports
        user.receive_sms = receive_sms
        user.receive_email = receive_email
        user.receive_rain = receive_rain
        user.zipcode = zipcode
        user.timezone = timezone
        user.geoString = geoString

        return userUpdated

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return False


def updateUser(request):
    '''
    Given a request object containing user's auth token, validates user, then validates input zipcode
    and phone number, calls _updateUserAttributes, commits user object to database if there were changes,
    and enqueues an update to the task in A Trigger's database.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        userUpdated = False
        claims = _getClaims(request)
        if not claims:
            error = 'Sorry! You did not provide the credentials necessary to access this resource.'
            return HttpResponse(error, status=401)
        userKey = ndb.Key(User, claims['sub'])
        user = userKey.get()

        ## Request processing 
        post = request.POST

        # Validate zipcode input and update corresponding user property
        zipcode = post['input-zip'] if 'input-zip' in post else None
        timezone = user.timezone
        if user.zipcode != zipcode or not zipcode:
            if not re.match(r"^[0-9]{5}(?:-[0-9]{4})?$", zipcode):
                return HttpResponse(json.dumps({'err': "Invalid zipcode."}))

        # Fetch timezone info for the zipcode if zipcode has changed, and update corresp. user property
            timezoneTuple = _getTimeZone(zipcode) if zipcode != user.zipcode else ('', user.timezone)
            #logging.info(timezone)
            if timezoneTuple[0] == "err":
                return HttpResponse(json.dumps({'err': timezoneTuple[1]}))
            else:
                timezone = timezoneTuple[1]

        # Validate phone input via Twilio API and update corresponding user property
        phone = post['input-phone'] if 'input-phone' in post else None
        if not phone:
            return HttpResponse(json.dumps({'err': "Invalid US phone number. Valid Format: 1234567891"}))
        elif user.phone != phone:
            if not _isValidPhoneNumber(phone):
                return HttpResponse(json.dumps({'err': "Invalid US phone number. Valid Format: 1234567891"}))
        receive_reports = post['check-receive-reports'] if 'check-receive-reports' in post else None
        updateReports = False

        if user.receive_reports != receive_reports:

            updateReports = True
        
        # Update user's info and settings
        userUpdated = _updateUserAttributes(user, post, claims, timezone)
        
        if userUpdated:
            user.put()
            if updateReports:
                # Enqueue task which updates trigger in ATrigger database. We can use 
                # defer/queueing without timing issues because task addition/deletion 
                # depends on user attr, which is being fetched with the strongly 
                # consistent get() by key method
                deferred.defer(_updateATriggerTask, userKey, _queue='ATrigger-queue')

        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(status=500)


def prepopulateFields(request):
    '''
    Given a request object containing user's auth token, validates user, then gets user from
    database, and responds with a response containing user's settings and info as JSON payload

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)

        name = claims['name']
        email = claims['email']

        user = ndb.Key(User, claims['sub']).get()

        return HttpResponse(json.dumps({'receive_reports': user.receive_reports, \
            'receive_rain': user.receive_rain, 'receive_email': user.receive_email, \
            'receive_sms': user.receive_sms, 'phone': user.phone, 'zipcode': user.zipcode}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(status=500)





############ Daylight Savings Update ####################################

# Deferred task: csrf exempt to ensure GCP Queues work. May work sometimes without decorator.
@csrf_exempt
def _updateUserReportTimeDST(userKey):
    '''
    Given a user Key object, creates task to replace the task that was deleted in updateDaylightSavings().

    Args: user Key object
    Returns: HttpResponse object
    '''
    try:
        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
        user = userKey.get()
        # task_exists ensures that not only is user signed up to get reports, but that the task exists in
        # A Trigger in order to avoid duplicate tasks. Otherwise, user is not signed up or task is queued
        # for creation
        if user.receive_reports and user.task_exists:
            # allow 2 hours extra after daylight time switch (4 am instead of 2 am)
            reportDatetime = _getReportDatetime(user.timezone)
            domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
            #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

            addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
                '&timeSlice=1day&count=-1&url=' + domain + 
                '/endpoints/sendReport/' + 
                '&tag_ID=' + userKey.id() + '&tag_type=reports&first=' + reportDatetime + '&post=True')

            A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
            data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
            # Quick fix for timeout issue. Shouldn't have to deal with timeout issues, so to fix timeout 
            # problem, just send the request, and it should be executed by A Trigger.
            try:
                addTaskResponse = requests.post(addURL, data=data, verify=True)
            except:
                pass
        return HttpResponse()
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(status=500)


# csrf exempt to allow scheduled cross-origin trigger request in. Secured via secret payload.
@csrf_exempt
def updateDaylightSavings(request):
    '''
    Given a request object, deletes all tasks for users who are currently opted in to receive
    reports, and for whom tasks exist, then enqueues the addition of the same task with updated
    datetime start time for each user.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    try:
        req = request.REQUEST
        if Settings.get('A_TRIGGER_PAYLOAD_SECRET') != request.POST['A_TRIGGER_PAYLOAD_SECRET']:
            return HttpResponse(status=401)
        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')

        deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_type=reports')
        # Quick fix for timeout issue. Shouldn't have to deal with timeout issues, so to fix timeout 
        # problem, just send the request, and it should be executed by A Trigger.
        try:
            deleteTaskResponse = requests.post(deleteURL, verify=True)
        except:
            pass

        # task_exists ensures that not only is user signed up to get reports, but that the task exists in
        # A Trigger in order to avoid duplicate tasks. Otherwise, user is not signed up or task is queued
        # for creation
        userKeysQuery = User.query(User.receive_rain=='on', User.task_exists==True)
        logging.info(userKeysQuery.fetch())
        for userKey in userKeysQuery.iter(keys_only=True):
            deferred.defer(_updateUserReportTimeDST, userKey, _queue='DST-queue')
        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(status=500)



############ A Trigger Verification ####################################

# TODO check security of serving file this way, and with static server in production
def ATriggerVerify(request):
    '''
    Given a request object, returns the ATriggerVerify.txt file as text file content.

    Args: HttpRequest object
    Returns: HttpResponse object
    '''
    #ATriggerFilePath = BASE_DIR + '/static/sourcebasesite/ATriggerVerify.txt'
    #txtfile = open(ATriggerFilePath, 'r')
    txtfile = Settings.get('A_TRIGGER_FILE')
    response = HttpResponse(content=txtfile)
    response['Content-Type'] = 'text/javascript'
    return response






'''

########### Create DST Update Scheduled Tasks #################

def createDSTUpdateTask(request):
    A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
    A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
    eastern = pytz.timezone('US/Eastern')
    # allow 2 hours extra after daylight time switch (4 am instead of 2 am)
    # DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2019, 3, 11, 4), is_dst=True).isoformat()
    DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2018, 11, 4, 4), is_dst=True).isoformat()

    
    logging.info(DSTStartOrEndDateTime)

    domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
    #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

    addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
    A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
    '&timeSlice=1year&count=-1&url=' + domain + 
    '/endpoints/updateDaylightSavings/' + '&tag_type=DST&first=' + DSTStartOrEndDateTime + '&post=True')

    A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
    data = {'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
    #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
    addDSTTaskResponse = requests.post(addURL, data=data, verify=True)
    return HttpResponse(json.dumps(addDSTTaskResponse.json()))

'''