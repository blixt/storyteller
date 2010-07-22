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

    data = [{'story_id': p.key().parent().id(), 'number': p.number,
             'created': p.created, 'text': p.text,
             'num_branches': p.num_branches}
            for p in model.Paragraph.get_range(story, start, end)]
    memcache.set(cache_key, data)

    return data


@public
def add_paragraph(handler, story_id, paragraph_number, text):
    """Adds a new paragraph after a certain paragraph. Note that this might
    branch the story and return a different story id than the one that was
    passed in. Check the "branched" boolean to see if this has happened.

    """
    base_paragraph, story, paragraph, branched = model.Story.add_paragraph(
        story_id, paragraph_number, text)

    # Keep in mind in the code below that story_id refers to the original story
    # and story.length could be the length of a new story (and thus very
    # different from the length of the original story).
    page = (story.length - 1) / settings.PAGE_SIZE + 1

    keys = ['paragraph:%d:%d' % (story_id, paragraph_number),
            'paragraphs:%d:%d' % (story_id, page)]
    if page == 1:
        # Since story data is returned with the first page, the story cache
        # needs to be purged.
        keys.append('story:%d' % story_id)
    elif story.length % settings.PAGE_SIZE == 1:
        # This is the first paragraph of a page, meaning that the previous page
        # needs to be purged as well (so that the new num_branches value can be
        # returned).
        keys.append('paragraphs:%d:%d' % (story_id, page - 1))

    if branched:
        # Since the branch count is cached in the list of branches, the cached
        # parent of the base paragraph will need to be purged.
        parent_key = base_paragraph._entity['follows']
        keys.append('paragraph:%d:%s' % (parent_key.parent().id(),
                                         parent_key.name()))

    memcache.delete_multi(keys)

    # Only tweet for one story (currently id 1).
    # Twitter is currently disabled since with no voting, abuse is easy.
    #if settings.TWITTER_USERNAME and story.key().id() == 1:
    #    utils.oauth_req(
    #        'http://api.twitter.com/1/statuses/update.json',
    #        'POST', 'status=%s' % paragraph.text)

    return {'story_id': story.key().id(), 'paragraph_number': paragraph.number,
            'branched': branched}

@public
def get_paragraph(handler, story_id, number):
    """Retrieves a single paragraph and its branches.

    """
    if not isinstance(story_id, (int, long)):
        raise TypeError('Story id must be an integer.')
    if not isinstance(number, (int, long)):
        raise TypeError('Paragraph number must be an integer.')

    cache_key = 'paragraph:%d:%d' % (story_id, number)
    data = memcache.get(cache_key)
    if data:
        return data

    story_key = model.get_key(story_id, 'Story')
    paragraph = model.Paragraph.get_by_key_name(str(number), parent=story_key)
    if not paragraph:
        raise storyteller.ParagraphNotFoundError('Paragraph not found.')

    data = {'story_id': story_id, 'number': paragraph.number,
            'created': paragraph.created, 'text': paragraph.text,
            'branches': [{'story_id': p.key().parent().id(),
                          'number': p.number, 'created': p.created,
                          'text': p.text, 'num_branches': p.num_branches}
                         for p in paragraph.branches]}

    memcache.set(cache_key, data)
    return data

@public
def get_story(handler, id=None):
    """Retrieves a single story.
    
    """
    if id is not None and not isinstance(id, (int, long)):
        raise TypeError('Story id must be an integer.')

    if id:
        data = memcache.get('story:%d' % id)
        if data:
            return data

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
            return data

    data = {'id': id, 'length': story.length,
            'branches': [{'story_id': b.parent().id(),
                          'paragraph_number': int(b.name())}
                         for b in story.branches],
            'paragraphs': _get_paragraphs(story)}

    memcache.set('story:%d' % id, data)
    return data
