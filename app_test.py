# Copyright 2015 Google Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# [START imports]
import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.ext import testbed

# deferred/queues
import operator
import os
from google.appengine.api import taskqueue
from google.appengine.ext import deferred



import datetime
import pytz
# [END imports]


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


class Report(ndb.Model):
    """weather report model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    dailyLow = ndb.IntegerProperty()
    dailyHigh = ndb.IntegerProperty()
    precipitation = ndb.IntegerProperty()
    summary = ndb.StringProperty()

class Alert(ndb.Model):
    """weather report model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    precipitation = ndb.IntegerProperty()



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




class DatastoreTestCase(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        ndb.get_context().clear_cache()


    def tearDown(self):
        self.testbed.deactivate()

    def testInsertUser(self):
    	user = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', name='Omar Ali', email='omar.ali11231@gmail.com', 
			phone='6156387550', zipcode='37209', timezone='America/Chicago', geoString='36.1484862,-86.9523954',
			receive_email='on', receive_sms='on', receive_rain='on', receive_reports='on')
        user.put()
        self.assertEqual(user, user.key.get())
    def testInsertReport(self):
        report = Report(user=ndb.Key(User, 'LCaU4CoqV2foifOhhzUnsF3m9dt1'),
            datetime=datetime.datetime.now(), dailyLow=40, dailyHigh=70, precipitation=30, summary="some summary")
        report.put()
        self.assertEqual(report, Report.query().fetch()[0])
    def testInsertAlert(self):
        alert = Alert(user=ndb.Key(User, 'LCaU4CoqV2foifOhhzUnsF3m9dt1'), 
            datetime=datetime.datetime.now(), precipitation=80)
        alert.put()
        self.assertEqual(alert, Alert.query().fetch()[0])

    def testFilterByRainAlert(self):
        user1 = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', receive_rain='on')
        user2 = User(userID='MCaU4CoqV2foifOhhzUnsF3m9dt2', receive_rain=None)
        user1.put()
        user2.put()
        usersReceivingAlerts = User.query().filter(User.receive_rain=='on').fetch()
        self.assertEqual(1, len(usersReceivingAlerts))
        self.assertEqual(user1, usersReceivingAlerts[0])


from google.appengine.datastore import datastore_stub_util  


class HighReplicationTestCaseOne(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        # consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=0)
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testUserGetWithKeyConsistencyVsGlobalQueryEventualConsistency(self):
        user = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', name='Omar Ali', email='omar.ali11231@gmail.com', 
            phone='6156387550', zipcode='37209', timezone='America/Chicago', geoString='36.1484862,-86.9523954',
            receive_email='on', receive_sms='on', receive_rain='on', receive_reports='on')
        user.key = ndb.Key(User, 'LCaU4CoqV2foifOhhzUnsF3m9dt1')
        user.put()

        # Global query doesn't see the data.
        self.assertEqual(0, User.query().count())
        # Key query does see the data.
        self.assertEqual(user, user.key.get())





# Mail Tests

class MailTestCase(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def testMailSent(self):
        mail.send_mail(to='alice@example.com',
                       subject='This is a test',
                       sender='bob@example.com',
                       body='This is a test e-mail')
        messages = self.mail_stub.get_sent_messages(to='alice@example.com')
        self.assertEqual(1, len(messages))
        self.assertEqual('alice@example.com', messages[0].to)


# Queues Tests

# deferred

def _updateATriggerTask(userKey):
    '''
    Deferred task which updates the the scheduled task in A Trigger
    which sends weather reports to user at 8 am.
    '''

    A_TRIGGER_KEY = 'A_TRIGGER_KEY'
    A_TRIGGER_SECRET = 'A_TRIGGER_SECRET'
    #user = User.query(User.key==userKey).fetch(projection=[User.receive_reports, User.timezone])[0]
    user = userKey.get()
    #logging.info("++++++++++++ Update A Trgigger +++++++++++")
    #logging.info(user)
    #logging.info(user.receive_reports)
    if user.receive_reports:
        return 'add'
        reportDatetime = _getReportDatetime(user.timezone)
        #domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
        domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

        addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
        A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
        '&timeSlice=1minute&count=-1&url=' + domain + 
        '/endpoints/sendReport/' + 
        '&tag_ID=' + userKey.id() + '&tag_type=reports&first=' + '2018-09-14T12:46:47.260683-10:00' + '&post=True')
        
        #logging.info(triggerurl)
        A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
        data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
        #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
        addTaskResponse = requests.post(addURL, data=data, verify=True)
        
    else:
        return 'delete'
        deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
        A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_ID=' + 
        userKey.id() + '&tag_type=reports')
        deleteTaskResponse = requests.post(deleteURL, verify=True)
    #logging.info("####################### here in updateatrigger")
    #logging.info(addTaskResponse.json())



class TaskQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # root_path must be set the the location of queue.yaml.
        # Otherwise, only the 'default' queue will be available.
        self.testbed.init_taskqueue_stub(
            root_path=os.path.join(os.path.dirname(__file__), ''))
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=0)
        # Initialize the datastore stub with this policy.
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        # Initialize memcache stub too, since ndb also uses memcache
        self.testbed.init_memcache_stub()
        # Clear in-context cache before each test.
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testTaskAddedByDeferred(self):
        deferred.defer(operator.add, 1, 2)

        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)

        result = deferred.run(tasks[0].payload)
        self.assertEqual(result, 3)

    def testATriggerDeleteTaskDeferred(self):
        user = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', name='Omar Ali', email='omar.ali11231@gmail.com', 
            phone='6156387550', zipcode='37209', timezone='America/Chicago', geoString='36.1484862,-86.9523954',
            receive_email='on', receive_sms='on', receive_rain='on', receive_reports='on')
        user.key = ndb.Key(User, user.userID)
        user.put()
        deferred.defer(_updateATriggerTask, user.key)

        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)

        result = deferred.run(tasks[0].payload)
        self.assertEqual(result, 'add')


    def testATriggerAddTaskDeferred(self):
        user = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', name='Omar Ali', email='omar.ali11231@gmail.com', 
            phone='6156387550', zipcode='37209', timezone='America/Chicago', geoString='36.1484862,-86.9523954',
            receive_email='on', receive_sms='on', receive_rain='on', receive_reports=None)
        user.key = ndb.Key(User, user.userID)
        user.put()
        deferred.defer(_updateATriggerTask, user.key)

        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)

        result = deferred.run(tasks[0].payload)
        self.assertEqual(result, 'delete')








# [START main]
if __name__ == '__main__':
    unittest.main()
# [END main]