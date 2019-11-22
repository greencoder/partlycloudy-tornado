import tornado.httpclient
import tornado.ioloop
import tornado.template
import tornado.web

from tornado.escape import json_encode as json_enc
from tornado.escape import json_decode as json_dec
from tornado.options import define
from tornado.options import options

from noaa import NoaaParser

class FetchHandler(tornado.web.RequestHandler):

    async def _fetch_forecast_html(self, lat, lon):
        http_client = tornado.httpclient.AsyncHTTPClient()
        url = f'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}'
        headers = {'User-Agent': 'Mozilla 1.0'}
        response = await http_client.fetch(url, headers=headers, method='GET')
        return response.body

    @tornado.web.asynchronous
    async def get(self):
        lat = self.get_argument('lat')
        lon = self.get_argument('lon')

        noaa_parser = NoaaParser()
        html = await self._fetch_forecast_html(lat, lon)

        data = noaa_parser.parse(html)

        loader = tornado.template.Loader('templates')
        html = loader.load('MapClick.html').generate(data=data)
        self.finish(html)


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        loader = tornado.template.Loader('templates')
        html = loader.load('index.html').generate()
        self.finish(html)


def make_app(debug):
    return tornado.web.Application([
        (r'/MapClick.php', FetchHandler),
        (r'/', MainHandler),
    ], debug=debug)


if __name__ == "__main__":
    options.define('port', default=5000, help='port to listen on')
    options.define('debug', default=False)
    options.parse_command_line()

    app = make_app(debug=options.debug)
    app.listen(options.port)

    print('Server listening on port %s' % options.port)
    tornado.ioloop.IOLoop.current().start()
