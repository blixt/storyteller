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

from datetime import datetime, timedelta
import logging
import os
import sys
import time
import traceback

from django.utils import simplejson
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import storyteller
from storyteller import controller, settings


def _json(data):
    return simplejson.dumps(jsonify(data), separators=(',', ':'))


class TemplatedRequestHandler(webapp.RequestHandler):
    """Simplifies handling requests. In particular, it simplifies working
    with templates, with its render() method.

    """

    def handle_exception(self, exception, debug_mode):
        """Called if this handler throws an exception during execution.

        """
        logging.exception(exception)

        # Also show a traceback if debug is enabled, or if the currently logged
        # in Google user is an application administrator.
        if debug_mode or users.is_current_user_admin():
            tb = ''.join(traceback.format_exception(*sys.exc_info()))
        else:
            tb = None

        self.render(settings.ERROR_TEMPLATE, traceback=tb)

    def head(self, *args, **kwargs):
        self.get(*args, **kwargs)

    def initialize(self, request, response):
        super(TemplatedRequestHandler, self).initialize(request, response)

    def not_found(self, template_name=None, **kwargs):
        """Similar to the render() method, but with a 404 HTTP status code.
        Also, the template_name argument is optional. If not specified, the
        NOT_FOUND_TEMPLATE setting will be used instead.

        """
        if not template_name:
            template_name = settings.NOT_FOUND_TEMPLATE
        self.response.set_status(404)
        self.render(template_name, **kwargs)

    def render(self, template_name, **kwargs):
        """Renders the specified template to the output.

        The template will have the following variables available, in addition
        to the ones specified in the render() method:
        - settings: Access to the application settings.
        - request: The current request object. Has attributes such as 'path',
                   'query_string', etc.

        """
        kwargs.update({'request': self.request,
                       'settings': settings})

        path = os.path.join(settings.TEMPLATE_DIR, template_name)
        self.response.out.write(template.render(path, kwargs))


def jsonify(obj):
    """Takes complex data structures and returns them as data structures that
    simplejson can handle.

    """
    # Return datetimes as a UNIX timestamp (seconds since 1970).
    if isinstance(obj, datetime):
        return int(time.mktime(obj.timetuple()))

    # Return timedeltas as number of seconds.
    if isinstance(obj, timedelta):
        return obj.days * 86400 + obj.seconds + obj.microseconds / 1e6

    # Since strings are iterable, return early for them.
    if isinstance(obj, basestring):
        return obj

    # Handle dicts specifically.
    if isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.iteritems():
            new_obj[key] = jsonify(value)
        return new_obj

    # Walk through iterable objects and return a jsonified list.
    try:
        iterator = iter(obj)
    except TypeError:
        # Return non-iterable objects as they are.
        return obj
    else:
        return [jsonify(item) for item in iterator]

class ApiHandler(TemplatedRequestHandler):
    """Opens up the controller module to HTTP requests. Arguments should be
    JSON encoded. Result will be JSON encoded.

    """
    def get(self, action):
        res = self.response

        # Attempt to get the attribute in the controller module.
        attr = getattr(controller, action, None)
        if not attr:
            res.set_status(404)
            res.out.write('{"status":"not_found"}')
            return
        # Require that the attribute has been marked as public.
        if not getattr(attr, '__public', False):
            res.set_status(403)
            res.out.write('{"status":"forbidden"}')
            return

        req = self.request

        try:
            # Build a dict of keyword arguments from the request parameters.
            # All arguments beginning with an underscore will be ignored.
            kwargs = {}
            for arg in req.arguments():
                if arg.startswith('_'): continue
                kwargs[str(arg)] = simplejson.loads(req.get(arg))

            data = attr(self, **kwargs) if callable(attr) else attr
            result = {'status': 'success',
                      'response': jsonify(data)}
        except BaseException, e:
            logging.exception('API error:')

            res.set_status(400)
            result = {'status': 'error',
                      'response': str(e),
                      'module': type(e).__module__,
                      'type': type(e).__name__}

        # Write the response as JSON.
        res.headers['Content-Type'] = 'application/json'
        res.out.write(simplejson.dumps(result, separators=(',', ':')))

class StoryHandler(TemplatedRequestHandler):
    def get(self, story_id=None, paragraph_number=None):
        if story_id is not None:
            story_id = int(story_id)

        try:
            story = controller.get_story(self, story_id)
        except storyteller.NotFoundError:
            self.not_found()
            return

        if not story_id:
            self.redirect('/%d' % story['id'])
            return

        if paragraph_number is None:
            paragraph_number = story['length']
        else:
            paragraph_number = int(paragraph_number)
            if not 1 <= paragraph_number <= story['length']:
                self.not_found()
                return
            if paragraph_number < story['length']:
                del story['paragraphs'][paragraph_number:]

        if paragraph_number:
            paragraph = controller.get_paragraph(self, story_id,
                                                 paragraph_number)
        else:
            paragraph = None

        self.render('story.html',
            json_story=_json(story), story=story,
            json_paragraph=_json(paragraph), paragraph=paragraph)

class NotFoundHandler(TemplatedRequestHandler):
    def get(self):
        self.not_found()
    post = get
