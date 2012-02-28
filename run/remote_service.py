from pyjsonrpc import service_method

class TestService(object):
    @service_method
    def divide(self, a, b):
        return a/b

if __name__ == "__main__":
    from pyjsonrpc.handlers import SimpleServer
    import sys
    
    import logging
    log = logging.getLogger('pyjsonrpc')
    h = logging.StreamHandler(sys.stdout)
    log.addHandler(h)
    log.setLevel(logging.DEBUG)
    
    service = SimpleServer('127.0.0.1', 9288, TestService)
    service.serve()