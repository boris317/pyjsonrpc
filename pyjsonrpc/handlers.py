from wsgiref.simple_server import make_server
from wsgiref import handlers

import simplejson as json
from pyjsonrpc.service import RemoteService

from webob import Request, Response

class WSGIHandler(RemoteService):
    def __call__(self, environ, start_response):
        request = Request(environ)
        response = Response()
        response.content_type = "application/json"
        
        def flush(output):
            response.body = json.dumps(output)
            return response(environ, start_response)
        
        return flush(self.handle(request.body))
    
class SimpleServer(WSGIHandler):
    def __init__(self, host, port, service=None):
        WSGIHandler.__init__(self, service)
        self.host = host
        self.port = port
        self.httpd = make_server(host, port, self)
        
    def serve(self):
        print "Serving remote service: %s:%s" % (self.host, self.port)
        self.httpd.serve_forever()
        
class CGIHandler(WSGIHandler):
    def serve(self):
        handlers.CGIHandler.run(self)

    