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

class Error(Exception):
    """Generic error for the Storyteller application."""

class NotFoundError(Error):
    """Error for when a resource cannot be found."""

class ParagraphNotFoundError(NotFoundError):
    """Raised when a paragraph could not be found."""

class StoryNotFoundError(NotFoundError):
    """Raised when a story could not be found."""

class StoryLockedError(Error):
    """Raised when attempting to act on a story that has been locked."""

class StoryPendingError(Error):
    """Raised when attempting to lock or modify a story that has a pending
    paragraph.
    
    """

class VotesNotPossibleError(Error):
    """Raised when voting is attempted on a story, but the story is not in a
    state that allows voting.

    """
