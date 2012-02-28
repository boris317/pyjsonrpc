from pyjsonrpc import ServiceProxy

test_service = ServiceProxy('http://127.0.0.1:9288', 'TestService')

print test_service.divide(1.0, 2.0)