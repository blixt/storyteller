# Storyteller

Storyteller is a web app for collaboratively writing stories being developed in Python for [Google App Engine](http://appengine.google.com/). The app is available at <http://story.multifarce.com/>.

If you want to contribute, please see [the wave discussing future development of Storyteller](https://wave.google.com/wave/waveref/googlewave.com/w+soBIcBHBA). For access, contact Andreas Blixt (andreas@blixt.org).

## API

The Storyteller application does everything through a controller which communicates with the data layer. All the public methods of the controller are accessible using HTTP requests. Examples:

- Get information about a story: <http://story.multifarce.com/api/get_story?id=1>
- Suggest a paragraph for a story: <http://story.multifarce.com/api/suggest_paragraph?story_id=1001&text="Hello+World!">

Currently, no authentication is needed, but once it starts getting abused, that will be implemented in one form or another.

For more information, look in the controller code.

## License

[GNU General Public License](http://www.gnu.org/licenses/)
