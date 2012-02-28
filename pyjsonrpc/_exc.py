
class ServiceException(Exception):
    code = None
    def __init__(self, message, rpc=None):
        self.message = message
        self.rpc = rpc
        
    def __str__(self):
        return self.message

class ServiceMethodNotFound(ServiceException):
    code = -32601
    def __init__(self, rpc):
        ServiceException.__init__(self, "Service method '%s' not found." % rpc.method, rpc)
        self.method_name = rpc.method
        
class JSONRPCDecodeError(ServiceException):
    code = -32600
    def __init__(self, message, rpc=None):
        ServiceException.__init__(self, message, rpc)