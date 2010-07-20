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

from google.appengine.ext import webapp

from storyteller import settings

register = webapp.template.create_template_register()

@register.filter
def static(path):
    """Modifies a path by prepending the absolute path to where static files
    reside and adding a version-specific hash to the end of the path to make
    the path unique for the currently deployed version.

    The path should always be relative to the static path.

    """
    return '/s/%(version)s/%(path)s' % {
        'path': path,
        'version': settings.VERSION_HASH}
