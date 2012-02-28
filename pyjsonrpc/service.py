'''
Parts of this package are based off of "python-jsonrpc" by Jan-Klaas Kollhof
http://json-rpc.org/

I am going to add onto the JSON-RPC proposed spec to support mixed positional
and keyword args in the "params" key. I am not changing the spec but instead including
an object structure that can be passed as the only positional argument in params. In this
way i support "spec" and also add more intellengence to it.



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
import inspect
import simplejson as json

from pyjsonrpc.object_hook import ObjectHook, Transmittable, reconstructor
from pyjsonrpc._exc import *

import logging
log = logging.getLogger(__name__)


def service_method(func):
    '''
    Decorate fucntions and methods to expose them as remote methods.
    '''
    func.is_service_method = True
    return func


class RPCRequest(Transmittable):
    version = "2.0"
    
    @reconstructor(method="method", jsonrpc="version", params="params", 
                   id="id", __subspec__="subspec", skip_null_keys=True)
    def __init__(self, **kw):
        Transmittable.__init__(self)
        self.subspec = kw.get('__subspec__') or kw.get('subspec')
        self.id = kw.get('id')
        self.type = 'request' if self.id else 'notification'

        try:
            self.method  = kw['method']
            self.version = kw['jsonrpc']
        except KeyError, e:
            raise JSONRPCDecodeError('Missing required parameter "%s"' % e.args[0], rpc=self)
        
        self.params = kw.get('params')
        if not isinstance(self.params, (NoneType, dict, list)):
            raise JSONRPCDecodeError(
                'Invalid type "%s" for value of "params" keyword. Must be list or dict.' % type(self.params),
                rpc=self
            )
                        
class RemoteService(object):
    __namespaces = {}
    def __init__(self, services=None, show_stack_trace=False):
        '''
        ``RemoteService`` wraps our remote service namespace. Takes a json-rpc
        string and invokes the correct call to the underlying service namespace
        
        kw_args:
           @service(None) - class or namespace/list of namespaces that exposes remote methods. If service is None
                            the namespace is assumed to be ``__main__``.
                      
           @show_stack_trace(False) - If True, when an exception occurs durring a remote method
                                       call send the stack trace to the client.
        '''
        
        if not services:
            import __main__ as services
            
        if not isinstance(services, list):
            services = [services]
            
        for service in services:
            #service namespaces can be classes, instances or modules
            if inspect.ismodule(service):
                self.__namespaces[service.__name__] = service                        
            elif inspect.isclass(service):
                self.__namespaces[service.__name__] = service()
            elif hasattr(service, '__class__'):
                self.__namespaces[service.__class__.__name__] = service
            else:
                raise ServiceException(None, 'Invalid service object')
          
        log.debug('Namespaces: %s', str(self.__namespaces))
        self.show_stack_trace = show_stack_trace
        self.object_hook = ObjectHook({'RPCRequest': RPCRequest})
     
    def add_object_hook(self, name, handler):
        self.object_hook.add_hook(name, handler)
        
    def handle(self, json_rpc_str):
        """
        Handle a service call and dispatch to the correct method.
        """
        try:
            rpc = json.loads(json_rpc_str, object_hook=self.object_hook)
        except ValueError, e:
            raise
        except JSONRPCDecodeError, e:
            return self.error(e)
        
        log.debug('Request: %s\nVersion: %s\nSubspec: %s', rpc.id, rpc.version, rpc.subspec)
        
        try:
            result = self.call_method(self.get_method(rpc), rpc)
        except ServiceException, e:
            return self.error(e)
        except Exception, e:
            e.rpc = rpc
            return self.error(e, self.show_stack_trace)
        else:            
            if not rpc.id:#notification
                return ''
            response = self.__base_response(rpc)
            response['result'] = result
            return response
                                    
    def error(self, e, stack_trace=False):
        
        if getattr(e, 'rpc', None):
            error = self.__base_response(e.rpc)
            if e.rpc.subspec:
                error['__subspec__'] = e.rpc.subspec
        else: error = {}
        
        error['error'] = e.message
        error['code'] = getattr(e, 'code', None) or -32000
                    
        if stack_trace:            
            error['data'] = traceback.format_exc()
            
        return error
        
    def get_method(self, rpc):        
        
        if '.' in rpc.method:
            try:
                namespace, method_name = rpc.method.split('.')
            except ValueError, e:
                raise ServiceMethodNotFound(rpc)
        else:
            namespace = '__main__'
            method_name = rpc.method
            
        log.debug('Getting method "%s" from namespace "%s".', method_name, namespace)
        if not namespace in self.__namespaces:
            log.debug('No such namespace: %s', namespace)
            raise ServiceMethodNotFound(rpc)
        
        _method = getattr(self.__namespaces[namespace], method_name, None)
        if not _method or not hasattr(_method, 'is_service_method'):
            log.debug('No such method "%s" in namespace "%s"', method_name, namespace)
            raise ServiceMethodNotFound(rpc)
        
        log.debug('Method found: %s', method_name)        
        return _method
    
    def call_method(self, _method, rpc):
        log.debug('Calling method: %s', rpc.method)
        
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
                    
