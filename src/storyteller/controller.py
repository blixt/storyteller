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

"""A set of functions that control the application.

The purpose of this module is to provide a bridge between the user (through
views) and the back-end (models and data logic).

"""

from datetime import datetime, timedelta
import os

from google.appengine.api import memcache

import storyteller
from storyteller import model, settings, utils
from storyteller.utils import public

def _get_paragraphs(story, page=None):
    if page < 1:
        page = 1

    if isinstance(story, (int, long)):
        story_id = story
    else:
        story_id = story.key().id()

    cache_key = 'paragraphs:%d:%d' % (story_id, page)
    data = memcache.get(cache_key)
    if data:
        return data

    # Calculate the numbers of the first and last paragraphs to get.
    start = (page - 1) * settings.PAGE_SIZE + 1
    end = start + settings.PAGE_SIZE - 1

    data = [{'number': p.number, 'text': p.text, 'created': p.created}
            for p in model.Paragraph.get_range(story, start, end)]
    memcache.set(cache_key, data)

    return data

def _set_can_vote(handler, story_data):
    if story_data['state'] == 'pending':
        ip = handler.request.remote_addr
        story_data['can_vote'] = ip not in story_data['pending_yes'] and \
                                 ip not in story_data['pending_no']
        del story_data['pending_yes']
        del story_data['pending_no']
    return story_data

def _vote(handler, story_id, keep):
    story, paragraph = model.Story.vote(
        story_id, handler.request.remote_addr, keep)

    if paragraph:
        page = (story.length - 1) / settings.PAGE_SIZE + 1
        memcache.delete_multi([
            'story:%d' % story_id,
            'paragraphs:%d:%d' % (story_id, page)])

        # Only tweet for one story (currently id 1).
        if settings.TWITTER_USERNAME and story.key().id() == 1:
            utils.oauth_req(
                'http://api.twitter.com/1/statuses/update.json',
                'POST', 'status=%s' % paragraph.text)
    else:
        memcache.delete('story:%d' % story_id)

@public
def branch_story(handler, id, paragraph=None):
    """Branches a story, allowing users to write an alternate version parallel
    to the original. If a paragraph is specified, the story will branch at that
    paragraph, otherwise it will branch at the latest paragraph of the story.

    """
    new_story = model.Story.branch(id, paragraph)
    return new_story.key().id()

@public
def get_paragraphs(handler, story_id, page=None):
    """Retrieves one page of paragraphs from the specified story.

    """
    if not isinstance(page, (int, long)) or page < 1:
        raise TypeError('Page must be a positive number.')

    data = _get_paragraphs(story_id, page)

    # Allow full (and thus static) pages to be cached by clients and Frontend.
    if len(data) == settings.PAGE_SIZE:
        cache_time = timedelta(days=365)
        expires = datetime.now() + cache_time

        res = handler.response
        res.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        res.headers['Cache-Control'] = 'public, max-age=%d' % (
            cache_time.days * 86400 + cache_time.seconds)

    return data

@public
def get_story(handler, id=None):
    """Retrieves a single story.
    
    """
    if id is not None and not isinstance(id, (int, long)):
        raise TypeError('Id must be a number.')

    if id:
        data = memcache.get('story:%d' % id)
        if data:
            return _set_can_vote(handler, data)

        story = model.Story.get_by_id(id)
        if not story:
            raise storyteller.StoryNotFoundError('Story not found.')
    else:
        # Get first story, or create one.
        story = model.Story.all().get()
        if not story:
            story = model.Story()
            story.put()
        id = story.key().id()

        data = memcache.get('story:%d' % id)
        if data:
            return _set_can_vote(handler, data)

    data = {'id': id, 'length': story.length, 'state': story.get_state()}

    cache_time = None
    if data['state'] == 'locked':
        cache_time = (story.lock - datetime.now()).seconds - 1
    elif data['state'] == 'pending':
        data.update({
            'paragraph': story.pending_text,
            'pending_yes': story.pending_yes,
            'pending_no': story.pending_no,
            'yes_votes': len(story.pending_yes),
            'no_votes': len(story.pending_no)})

    data['paragraphs'] = _get_paragraphs(story)

    if cache_time is None:
        memcache.set('story:%d' % id, data)
    elif cache_time > 0:
        memcache.set('story:%d' % id, data, cache_time)

    return _set_can_vote(handler, data)

@public
def lock_story(handler, id):
    """Lock a story from editing by others. The authentication key returned
    must be used to add a paragraph to the story while it is locked. The lock
    will time out after a while.

    """
    story = model.Story.get_lock(id)
    memcache.delete('story:%d' % id)
    return {'auth': story.auth, 'time': story.lock - datetime.now()}

@public
def suggest_paragraph(handler, story_id, text, auth=None):
    """Suggests a new paragraph to a story.

    """
    if not isinstance(text, basestring):
        raise TypeError('Invalid text.')
    model.Story.new_paragraph(
        story_id, text, handler.request.remote_addr, auth)
    memcache.delete('story:%d' % story_id)

@public
def vote_no(handler, story_id):
    """Vote to delete the currently pending paragraph.

    """
    _vote(handler, story_id, False)

@public
def vote_yes(handler, story_id):
    """Vote to keep the currently pending paragraph.

    """
    _vote(handler, story_id, True)
