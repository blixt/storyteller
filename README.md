# Storyteller

Storyteller is a web app for collaboratively writing stories being developed in Python for [Google App Engine](http://appengine.google.com/). The app is available at <http://story.multifarce.com/>.

If you want to contribute, please see [the wave discussing future development of Storyteller](https://wave.google.com/wave/waveref/googlewave.com/w+soBIcBHBA). For access, contact Andreas Blixt (andreas@blixt.org).

## Getting started

How to get a newly cloned version up and running in a local development environment.

### Prerequisites

1. [Python 2.5](http://www.python.org/download/releases/2.5/)
2. [Google App Engine SDK for Python](http://code.google.com/appengine/downloads.html)
3. [Django 1.1](http://www.djangoproject.com/download/)

### Configuration

1. Copy `src/app.yaml.template` to `src/app.yaml` and change the application identifier (`example` by default)
2. Copy `src/storyteller/settings.py.template` to `src/storyteller/settings.py` and change the configuration as desired
3. Run the application on the development server

## API

The Storyteller application does everything through a controller which communicates with the data layer. All the public methods of the controller are accessible using HTTP requests. Examples:

- Get information about a story: <http://story.multifarce.com/api/get_story?id=1>
- Add a paragraph to a story (branching it if needed): <http://story.multifarce.com/api/add_paragraph?story_id=1001&paragraph_number=5&text=%22Hello+World!%22>

Currently, no authentication is needed, but once it starts getting abused, that will be implemented in one form or another.

For more information, look in the controller code.

## License

[GNU General Public License](http://www.gnu.org/licenses/)
