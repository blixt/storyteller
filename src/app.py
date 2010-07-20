#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Andreas Blixt
#
# This file is part of Storyteller.
#
# Storyteller is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# Storyteller is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# Storyteller. If not, see http://www.gnu.org/licenses/.
#

"""Entry point for the Storyteller application.

"""

import logging
import os
import wsgiref.handlers

from google.appengine.dist import use_library

# Use Django 1.1 instead of Django 0.96. This code must run before the GAE web
# framework is loaded.
os.environ['DJANGO_SETTINGS_MODULE'] = 'storyteller.settings'
use_library('django', '1.1')

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template, util

import storyteller.settings
import storyteller.urls

# Register custom Django template filters/tags.
template.register_template_library('storyteller.template_extensions')

def main():
    application = webapp.WSGIApplication(
        storyteller.urls.urlpatterns,
        debug=storyteller.settings.DEBUG)

    # Run the WSGI CGI handler with the application.
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
