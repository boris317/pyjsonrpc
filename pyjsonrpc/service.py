'''
Parts of this package are based off of "python-jsonrpc" by Jan-Klaas Kollhof
http://json-rpc.org/

I am going to add onto the JSON-RPC proposed spec to support mixed positional
and keyword args in the "params" key. I am not changing the spec but instead including
an object structure that can be passed as the only positional argument in params. In this
way i support "spec" and also add more intellenge to it.



As per JSON-RPC 2.0:

Procedure Call with positional parameters:
--> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
<-- {"jsonrpc": "2.0", "result": 19, "id": 1}

Procedure Call with named parameters:
--> {"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 3}
<-- {"jsonrpc": "2.0", "result": 19, "id": 3}

As per my sub spec 1a formally called(by me) JSON-RPC 2.0-1a:
Procedure Call with mixed positional and keyword parameters:
--> {"jsonrpc": "2.0", "__subspec__": "1a", "method": "divide", "params": {"__args__": [1,2], "__kwargs__": {"round": true}}, "id": 3}
<-- {"jsonrpc": "2.0", "__subspec__": "1a", "result": 0.0, "id": 3}
'''
import traceback
from types import NoneType

import simplejson as json

class ServiceException(Exception):
    code = None
    def __init__(self, rpc, message):
        self.message = message
        self.rpc = rpc
        
    def __str__(self):
        return self.message

class ServiceMethodNotFound(ServiceException):
    code = -32601
    def __init__(self, rpc):
        ServiceException.__init__(self, rpc, "Service method '%s' not found." % rpc.method)
        self.method_name = name
        
class JsonRpcDecodeError(ServiceException):
    code = -32600
    def __init__(self, rpc, message):
        ServiceException.__init__(self, rpc, message)
                        
def service_method(func):
    '''
    Decorate fucntions and methods to expose them as remote methods.
    '''
    func.is_service_method = True
    return func

class JsonAsObject(object):
    def __new__(cls, obj_dict):
        if not cls.as_object in obj_dict:
            return obj_dict
        return super(JsonAsObject, cls).__new__(cls, obj_dict)
    
class RPCRequest(JsonAsObject):
    as_object = '__rpcrequest__'
    version = "2.0"
    def __init__(self, obj_dict):
        
        self.subspec = obj_dict.get('__subspec__')
        self.id = obj_dict.get('id')
        self.type = 'request' if self.id else 'notification'

        try:
            self.method  = obj_dict['method']
            self.version = obj_dict['jsonrpc']
        except KeyError, e:
            raise JsonRpcDecodeError(self, 'Missing required parameter "%s"' % e.args[0])
        
        self.params = obj_dict.get('params')
        if not isinstance(self.params, (NoneType, dict, list)):
            raise JsonRpcDecodeError(self,
                'Invalid type "%s" for value of "params" keyword. Must be list or dict.' % type(self.params)
            )
                
class RemoteService(object):
    
    def __init__(self, service=None, show_stack_trace=False):
        '''
        RemoteService wraps our remote service namespace. Takes a json-rpc
        string and invokes the correct call to the underlying service namespace
        
        kw_args:
           @service(None) - class or namespace that exposes remote methods. If service is None
                      the namespace is assumed to be __main__.
                      
           @show_stack_trace(False) - If True, when an exception occurs durring a remote method
                                       call send the stack trace to the client.
        '''
        if not service:
            import __main__ as service
        self.service = service
        self.show_stack_trace = show_stack_trace
        
    def handle(self, json_rpc_str):
        try:
            rpc = json.loads(json_rpc_str, object_hook=RPCRequest)
        except ValueError, e:
            raise
        except JsonRpcDecodeError, e:
            return self.error(e)
        try:
            return self.call_method(self.get_method(rpc), rpc)
        except ServiceException, e:
            self.error(e)
        except Exception, e:
            e.rpc = rpc
            return self.error(e, self.show_stack_trace)            
                        
    def error(self, e, stack_trace=False):
        error = self.__base_response(e.rpc)
        error['error'] = e.message
        error['code'] = getattr(e, 'code', None) or -32000
        
        if e.rpc.subspec:
            error['__subspec__'] = e.rpc.subspec
            
        if stack_trace:            
            error['data'] = traceback.format_exc()
            
        return error
        
    def get_method(self, rpc):
        _method = getattr(self.service, rpc.method)
        if not _method or not getattr(_method, 'is_service_method', None):
            raise ServiceMethodNotFound(rpc)
        return _method
    
    def call_method(self, _method, rpc):
        if not rpc.params:
            return _method()
        if isinstance(rpc.params, list):
            return _method(*rpc.params)
        if isinstance(rpc.params, dict):
            if rpc.subspec == "1a":
                if '__args__' in rpc.params and '__kwargs__' in rpc.params:
                    return _method(*rpc.params['__args__'], **self.__strify_keys(rpc.params['__kwargs__']))
                if '__args__' in rpc.params:
                    return _method(*rpc.params['__args__'])
                if '__kwargs__' in rpc.params:
                    return _method(**self.__strify_keys(rpc.params['__kwargs__']))
            return _method(**self.__strify_keys(rpc.params))
        
    def __base_response(self, rpc):
        resp = {'jsonrpc': rpc.version}
        if rpc.id:
            resp['id'] = rpc.id
        return resp
    
    def __strify_keys(self, dct):
        return dict([(str(k), v) for k,v in dct.iteritems()])        
                    
