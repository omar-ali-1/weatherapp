from __future__ import unicode_literals

from django.db import models

from google.appengine.ext import ndb

from django.template.defaultfilters import slugify




class User(ndb.Model):
    # User Info
    userID = ndb.StringProperty(required=True)
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    phone = ndb.StringProperty()
    zipcode = ndb.StringProperty()
    timezone = ndb.StringProperty()
    geoString = ndb.StringProperty()
    # User Settings
    receive_email = ndb.StringProperty()
    receive_sms = ndb.StringProperty()
    receive_rain = ndb.StringProperty()
    receive_reports = ndb.StringProperty()
    task_exists = ndb.BooleanProperty()


class Report(ndb.Model):
    """weather report model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    dailyLow = ndb.IntegerProperty()
    dailyHigh = ndb.IntegerProperty()
    precipitation = ndb.IntegerProperty()
    summary = ndb.StringProperty()

class Alert(ndb.Model):
    """rain alert model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    precipitation = ndb.IntegerProperty()


# TODO future: use Google Key Management Service
# Taken from Martin Omander's answer here https://stackoverflow.com/questions/21393107/python-and-yaml-gae-app-settings-file
class Settings(ndb.Model):
  name = ndb.StringProperty()
  value = ndb.StringProperty()

  @staticmethod
  def get(name):
    NOT_SET_VALUE = "NOT SET"
    retval = Settings.query(Settings.name == name).get()
    if not retval:
      retval = Settings()
      retval.name = name
      retval.value = NOT_SET_VALUE
      retval.put()
    if retval.value == NOT_SET_VALUE:
      raise Exception(('Setting %s not found in the database. A placeholder ' +
        'record has been created. Go to the Developers Console for your app ' +
        'in App Engine, look up the Settings record with name=%s and enter ' +
        'its value in that record\'s value field.') % (name, name))
    return retval.value



