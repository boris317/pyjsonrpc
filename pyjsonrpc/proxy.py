import urllib2
import random
from pyjsonrpc.json import RPCEncoder
from pyjsonrpc.service import RPCRequest
import simplejson as json

_RAND_RANGE = (1, 100000)

class JSONRPCException(Exception):
    def __init__(self, rpcError):
        Exception.__init__(self)
        self.error = rpcError
    def __str__(self):
        return self.error

class ServiceProxy(object):
    """
    Service Proxy client used to call a remote json service.
    
    Arguments
        @service_url - URL of the json service.
       
    Kw Arguments:
        @service_name - The service's namespace. A remote json service can offer many services or namepaces. 
           Setting this variable will ensure your calls get dispatched to the correct service namespace.
           The remote service can also simply offer an "un-named" namespace. In that case keeping
           "service_name" set to None will work just fine.
           
        @object_hook - ObjectHook instance with all the service's transmittable objects. If the service depends
           on alot of transimittable objects it is better to have the servie designer also create a
           custom subclassed ServiceProxy client that is already aware of said "transmittables".
    """
    def __init__(self, service_url, service_name=None, object_hook=None):
        self.__service_url = service_url
        self.__service_name = service_name
        self.encoder = RPCEncoder()
        self.class_handler = object_hook or (lambda x: x)

    def __getattr__(self, name):
        if self.__service_name != None:
            name = "%s.%s" % (self.__service_name, name)
        return ServiceProxy(self.__service_url, name)

    def __call__(self, *args, **kw):
        #add headers content-type, accept - application/json
        postdata = self.encoder.encode(self.__build_req_obj(*args, **kw))
        respdata = urllib2.urlopen(self.__service_url, postdata).read()
        resp = json.loads(respdata, object_hook=self.class_handler)

        if 'error' in resp:
            raise JSONRPCException(resp['error'])
        else:
            return resp['result']

    def __build_req_obj(self, *args, **kw):
        params = {}
        if args:
            params['__args__'] = args
        if kw:
            params['__kwargs__'] = kw
            
        return RPCRequest(
            method=self.__service_name,
            id=random.randrange(*_RAND_RANGE),
            subspec="1a",
            jsonrpc="2.0",
            params=params or None            
        )

