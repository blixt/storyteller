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

import time

import oauth2

from storyteller import settings

def _get_value(obj, name):
    """Gets a value from an object. First tries to get the attribute with the
    specified name. If that fails, it tries to use the object as a dict
    instead. If the value is callable, the return value of the callable is
    used.

    """
    try:
        value = getattr(obj, name)
    except AttributeError:
        try:
            # If the attribute doesn't exist, attempt to use the object as a dict.
            value = obj[name]
        except:
            # Failing that, just return None.
            return None
    # If the value is callable, call it and use its return value.
    return value() if callable(value) else value

def get_dict(obj, attributes):
    """Returns a dict with keys/values of a list of attributes from an object.

    """
    result = dict()
    for attr in attributes:
        if isinstance(attr, basestring):
            alias = None
        else:
            # If a value in the attributes list is not a string, it should be
            # two packed values: the attribute name and the key name it should
            # have in the dict.
            attr, alias = attr

        # Since the obj variable is needed for future iterations, its value is
        # stored in a new variable that can be manipulated.
        value = obj

        if '.' in attr:
            # Dots in the attribute name can be used to fetch values deeper
            # into the object structure.
            for sub_attr in attr.split('.'):
                value = _get_value(value, sub_attr)
            if not alias:
                alias = sub_attr
        else:
            value = _get_value(value, attr)

        # Store the value in the dict.
        result[alias if alias else attr] = value

    return result

def oauth_req(url, http_method='GET', post_body=None, http_headers=None):
    consumer = oauth2.Consumer(key=settings.TWITTER_CONSUMER_KEY,
                               secret=settings.TWITTER_CONSUMER_SECRET)
    token = oauth2.Token(key=settings.TWITTER_USER_KEY,
                         secret=settings.TWITTER_USER_SECRET)
    client = oauth2.Client(consumer, token)

    resp, content = client.request(
        url,
        method=http_method,
        body=post_body,
        headers=http_headers)
    return content

def public(func):
    """A decorator that defines a function as publicly accessible.

    """
    func.__public = True
    return func

def set_cookie(handler, name, value, expires=None, path='/'):
    # Build cookie data.
    if expires:
        ts = time.strftime('%a, %d-%b-%Y %H:%M:%S GMT', expires.timetuple())
        cookie = '%s=%s; expires=%s; path=%s' % (name, value, ts, path)
    else:
        cookie = '%s=%s; path=%s' % (name, value, path)

    # Send cookie to browser.
    handler.response.headers['Set-Cookie'] = cookie
    handler.request.cookies[name] = value
