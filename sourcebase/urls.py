"""sourcebase URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from sourcebasesite.views import *
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


urlpatterns = [
    url(r'^$', home, name='home'),
    url(r'^endpoints/verifyOrCreateUser/$', verifyOrCreateUser, name='verifyOrCreateUser'),
    # Serve text file used by scheduling server to verify this server
    url(r'^ATriggerVerify.txt$', ATriggerVerify, name='ATriggerVerify'),
    url(r'^endpoints/updateUser/$', updateUser, name='updateUser'),
    url(r'^endpoints/sendReport/$', sendReport, name='sendReport'),
    url(r'^endpoints/resendReport/$', resendReport, name='resendReport'),
    url(r'^endpoints/prepopulateFields/$', prepopulateFields, name='prepopulateFields'),
    url(r'^endpoints/checkRainAndAlertUsers/$', checkRainAndAlertUsers, name='checkRainAndAlertUsers'),
    url(r'^endpoints/getAlertHistory/$', getAlertHistory, name='getAlertHistory'),
    # url(r'^endpoints/testAppFeature/$', testAppFeature, name='testAppFeature'),
    # url(r'^endpoints/createDSTUpdateTask/$', createDSTUpdateTask, name='createDSTUpdateTask'),
    url(r'^endpoints/updateDaylightSavings/$', updateDaylightSavings, name='updateDaylightSavings')

]

