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

from datetime import datetime
import logging
import re
import string
import uuid

from google.appengine.ext import db

import storyteller
from storyteller import settings

def get_key(value, kind, parent=None):
    """Returns a key from value.

    """
    if not isinstance(kind, basestring):
        if issubclass(kind, db.Model):
            kind = kind.kind()
        else:
            raise TypeError(
                'Invalid type (kind); should be a Model subclass or a string.')

    if isinstance(value, db.Key):
        assert value.kind() == kind, 'Tried to use a Key of the wrong kind.'
        assert value.parent() == parent, 'Invalid Key parent.'
        return value
    elif isinstance(value, db.Model):
        assert value.kind() == kind, 'Tried to use a Model of the wrong kind.'
        assert value.parent_key() == parent, 'Invalid Model parent.'
        return value.key()

    if isinstance(value, (basestring, int, long)):
        return db.Key.from_path(kind, value, parent=parent)
    else:
        raise TypeError('Invalid type (value); expected string, number, Key '
                        'or %s.' % kind)

def get_instance(value, model, parent=None):
    """Returns a model instance from value. If value is a string, gets by key
    name; if value is an integer, gets by id; if value is a key, gets by key
    and if value is an instance, returns the instance.

    """
    if not issubclass(model, db.Model):
        raise TypeError('Invalid type (model); expected subclass of Model.')

    if isinstance(value, basestring):
        return model.get_by_key_name(value, parent=parent)
    elif isinstance(value, (int, long)):
        return model.get_by_id(value, parent=parent)
    elif isinstance(value, db.Key):
        return db.get(value)
    elif isinstance(value, model):
        return value
    else:
        raise TypeError('Invalid type (value); expected string, number, Key '
                        'or %s.' % model.__name__)


def _create_branch(story, paragraph, text):
    new_story = Story(
        branches=story.branches + [paragraph.key()],
        length=paragraph.number + 1)
    new_story.put()

    new_paragraph = Paragraph(
        key_name=str(new_story.length),
        parent=new_story.key(),
        number=new_story.length,
        follows=paragraph.key(),
        text=text)
    new_paragraph.put()

    return new_story, new_paragraph

def _create_paragraph(paragraph_key, text):
    story = Story.get(paragraph_key.parent())
    if not story:
        raise storyteller.StoryNotFoundError(
            'Could not find the specified story.')
    paragraph = Paragraph.get(paragraph_key)
    if not paragraph:
        raise storyteller.ParagraphNotFoundError(
            'Could not find the specified paragraph.')

    if story.length != paragraph.number:
        # Cannot continue story since it has already been continued. A branch
        # should be created instead.
        return paragraph, story, None, True

    story.length += 1
    story.put()

    new_paragraph = Paragraph(
        key_name=str(story.length),
        parent=story.key(),
        number=story.length,
        follows=paragraph_key,
        text=text)
    new_paragraph.put()

    paragraph.num_branches += 1
    paragraph.put()

    return paragraph, story, new_paragraph, False


class Story(db.Model):
    branches = db.ListProperty(db.Key, indexed=False)
    length = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    @classmethod
    def add_paragraph(cls, story_id, paragraph_number, text):
        """Adds a paragraph to a story. Does not save anything to the
        datastore.

        Takes the id of a story and the number of the paragraph to add after.

        Returns the paragraph being continued, the story instance used, the
        paragraph instance created and a boolean indicating whether the story
        used was a new branch (True) or the story that was specified originally
        (False).

        """
        if not isinstance(story_id, (int, long)):
            raise TypeError('Story id must be an integer.')
        if not isinstance(paragraph_number, (int, long)):
            raise TypeError('Paragraph number must be an integer.')
        if not isinstance(text, basestring):
            raise TypeError('Invalid text; it must be a string.')

        # Replace repeating spaces, newlines, etc. with single spaces.
        text = re.sub(r'\s+', ' ', text)

        if len(text) < 5:
            raise ValueError('That paragraph is too short.')
        if len(text) > 140:
            raise ValueError('That paragraph is too long.')

        story_key = db.Key.from_path('Story', story_id)
        paragraph_key = db.Key.from_path('Paragraph', str(paragraph_number),
                                         parent=story_key)

        base_paragraph, story, paragraph, needs_branch = db.run_in_transaction(
            _create_paragraph, paragraph_key, text)
        if not needs_branch:
            return base_paragraph, story, paragraph, False

        # A paragraph was never created, which means a branch is needed to
        # continue from the specified paragraph.
        new_story, new_paragraph = db.run_in_transaction(_create_branch,
            story, base_paragraph, text)
        try:
            # This part has to run outside a transaction since the branched
            # story is stored in a different entity group.
            base_paragraph.num_branches += 1
            base_paragraph.put()
        except:
            logging.exception(
                'Failed to increment branch count for a paragraph:')
        return base_paragraph, new_story, new_paragraph, True

class Paragraph(db.Model):
    number = db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    text = db.StringProperty(indexed=False, required=True)
    follows = db.SelfReferenceProperty(collection_name='branches')
    num_branches = db.IntegerProperty(default=0)
    good = db.ListProperty(int, indexed=False)
    bad = db.ListProperty(int, indexed=False)

    @classmethod
    def get_range(cls, story, start=1, end=None):
        """Gets a range of paragraphs from the specified story. This function
        takes branching into consideration, and may return paragraphs that
        belong to a story that the specified story was branched off of.

        The range defaults to all paragraphs for the specified story.

        """
        # Build a list of keys, fetching from the appropriate stories if the
        # story has been branched.
        keys = []
        story = get_instance(story, Story)
        if not end:
            end = story.length
        branch_end = 0
        for branch in story.branches:
            branch_start = branch_end + 1
            branch_end = int(branch.name())

            if branch_end < start:
                # The current branch ends before the desired paragraph. Check
                # next one.
                continue

            for i in xrange(branch_start, branch_end + 1):
                if i > end:
                    # The key list has been built. Exit the loop.
                    break
                keys.append(db.Key.from_path(cls.kind(), str(i),
                                             parent=branch.parent()))
            # This is a trick to allow the above break statement to break
            # two levels of for loops.
            else:
                continue
            break

        # Any remaining paragraphs are from the current story.
        for i in xrange(start + len(keys), end + 1):
            keys.append(db.Key.from_path(cls.kind(), str(i),
                                         parent=story.key()))

        paragraphs = db.get(keys)
        return paragraphs[:paragraphs.index(None)]
