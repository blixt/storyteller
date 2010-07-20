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
import string
import uuid

from google.appengine.ext import db

import storyteller
from storyteller import settings

def get_key(value, kind, parent=None):
    """Returns a key from value.

    """
    if issubclass(kind, db.Model):
        kind = kind.kind()
    elif not isinstance(kind, basestring):
        raise TypeError('Invalid type (kind); should be a Model subclass or a '
                        'string.')

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


def _lock_story(story_key):
    story = db.get(story_key)
    if not story:
        raise storyteller.StoryNotFoundError('Story not found.')

    story._do_auth()
    story.lock = datetime.now() + settings.LOCK_DURATION
    story.put()

    return story

def _new_paragraph(story_key, paragraph, ip, auth=None):
    if len(paragraph) < 5:
        raise ValueError('That paragraph is too short.')
    if len(paragraph) > 140:
        raise ValueError('That paragraph is too long.')

    story = db.get(story_key)
    if not story:
        raise storyteller.StoryNotFoundError('Story not found.')

    story._do_auth(auth)
    story.lock = None
    story.pending = True
    story.pending_text = paragraph
    story.pending_yes = [ip]
    story.pending_no = []
    story.put()

    return story

def _vote(story_key, ip, keep):
    if not isinstance(ip, basestring):
        raise TypeError('IP must be a string.')

    story = db.get(story_key)
    if not story:
        raise storyteller.StoryNotFoundError('Story not found.')

    if not story.pending:
        raise storyteller.VotesNotPossibleError(
            'It is currently not possible to vote on that story.')

    if ip in story.pending_yes:
        if keep:
            return story, None
        story.pending_yes.remove(ip)
    elif ip in story.pending_no:
        if not keep:
            return story, None
        story.pending_no.remove(ip)

    if keep:
        story.pending_yes.append(ip)
        if len(story.pending_yes) >= settings.VOTES_REQUIRED:
            story.length += 1
            paragraph = Paragraph(
                key_name=str(story.length),
                parent=story,
                number=story.length,
                text=story.pending_text)
            paragraph.put()
        else:
            story.put()
            return story, None
    else:
        story.pending_no.append(ip)
        if len(story.pending_no) < settings.VOTES_REQUIRED:
            story.put()
            return story, None
        paragraph = None

    # This code is only reached if the voting has finished.
    story.auth = None
    story.pending = False
    story.pending_text = None
    story.pending_yes = []
    story.pending_no = []
    story.put()

    return story, paragraph


class Story(db.Model):
    branches = db.ListProperty(db.Key, indexed=False)
    length = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    auth = db.StringProperty(indexed=False)
    lock = db.DateTimeProperty()
    pending = db.BooleanProperty()
    pending_text = db.StringProperty(indexed=False)
    pending_yes = db.StringListProperty(indexed=False)
    pending_no = db.StringListProperty(indexed=False)

    @classmethod
    def branch(cls, story, paragraph=None):
        story = get_instance(story, Story)

        branch = cls(length=story.length)
        p = get_instance(paragraph or str(story.length), Paragraph,
                         parent=story.key())
        if p:
            branch.branches = story.branches + [p.key()]
        elif paragraph:
            # The specified paragraph didn't exist.
            raise storyteller.ParagraphNotFoundError(
                'The specified paragraph could not be found.')
        else:
            # The story that is being branched didn't have any paragraphs.
            # Instead, branch the story that the specified story branches.
            branch.branches.extend(story.branches)
        branch.put()

        return branch

    @classmethod
    def get_lock(cls, story):
        return db.run_in_transaction(_lock_story, get_key(story, cls))

    @classmethod
    def new_paragraph(cls, story, paragraph, ip, auth=None):
        return db.run_in_transaction(_new_paragraph,
            get_key(story, cls), paragraph, ip, auth)

    @classmethod
    def vote(cls, story, ip, keep):
        return db.run_in_transaction(_vote,
            get_key(story, cls), ip, keep)

    def _do_auth(self, auth=None):
        """Checks whether a person may change a story. The story either needs
        to be in an editable state, or the person needs to provide a valid
        authentication key.

        If no error is raised, the person has been authenticated successfully.

        This function may change the auth attribute. If the new auth value is
        passed on, it's very important that the story is put to the datastore
        so that data consistency is kept.
        
        """
        if self.auth and auth == self.auth:
            return
        if self.is_locked():
            raise storyteller.StoryLockedError(
                'The story is locked and can only be changed by the person '
                'who locked it.')
        if self.pending:
            raise storyteller.StoryPendingError(
                'The story currently has a pending paragraph and needs votes '
                'before it can be changed.')

        self.auth = uuid.uuid4().get_hex()

    def get_state(self):
        if self.is_editable():
            return 'open'
        elif self.is_locked():
            return 'locked'
        elif self.pending:
            return 'pending'
        else:
            raise storyteller.Error('Story has an unknown state.')

    def is_editable(self, auth=None):
        if auth and auth == self.auth:
            return True
        if self.pending:
            return False
        return not self.is_locked()

    def is_locked(self):
        if not self.lock:
            return False
        return datetime.now() < self.lock

class Paragraph(db.Model):
    number = db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    text = db.StringProperty(indexed=False, required=True)

    @classmethod
    def get_range(cls, story, start, end):
        """Gets a range of paragraphs from the specified story. This function
        takes branching into consideration, and may return paragraphs that
        belong to a story that the specified story was branched off of.

        """
        # Build a list of keys, fetching from the appropriate stories if the
        # story has been branched.
        keys = []
        story = get_instance(story, Story)
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
                keys.append(db.Key.from_path('Paragraph', str(i),
                            parent=branch.parent()))
            else:
                # This is a trick to allow the above break statement to break
                # two levels of for loops.
                continue
            break

        # Any remaining paragraphs are from the current story.
        for i in xrange(start + len(keys), end + 1):
            keys.append(db.Key.from_path('Paragraph', str(i), parent=story.key()))

        paragraphs = db.get(keys)
        return paragraphs[:paragraphs.index(None)]
