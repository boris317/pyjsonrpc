'''
object_hook handles the decoding and encoding of more complex python objects. Such as classes
you may write. 

A transmittable object is encoded as a json structure. 
Example of the json structure:

{
    "__classhook__": {
        #name of the class to instatiate.
        "name": "ClassName",
        #Describing the agruments to be passed during instatiation
        "__init__": {
            #positional(optional)
            "__args__": ["positionan argument 1", "positionan argument 2"],
            #keyword arguments(optional)
            "__kwargs": {"kwarg1":"kw value 1", "kwarg2": "kw value 2"}
        }
    }
}

Thec``reconstructor`` decorator is used to describe the __init__ object. See its
doc string to learn how to describe what data gets sent via the __init__ object.

'''
from pyjsonrpc._exc import JSONRPCDecodeError

class ObjectHook(object):
    
    __hooks = {}
    
    def __init__(self, hooks={}):
        self.__hooks.update(hooks)
        
    def add_hook(self, name, handler):
        """
        Add a new transmittable class. "name" will be the value of the "name"
        attribute of the __classhook__ json object. "handler" is the actual
        transmittable class object.        
        """
        self.__hooks['name'] = handler
        
    def __call__(self, dict_obj):
        if "__classhook__" in dict_obj:
            class_hint = dict_obj['__classhook__']
            if class_hint['name'] in self.__hooks:
                klass = self.__hooks[class_hint['name']]
                arg_sig = class_hint.get('__init__', {})
                if '__args__' in arg_sig and '__kwargs__' in arg_sig:
                    return klass(*arg_sig['__args__'], **self.__strify_keys(arg_sig['__kwargs__']))
                if '__args__' in arg_sig:
                    return klass(*arg_sig['__args__'])
                if '__kwargs__' in arg_sig:
                    return klass(**self.__strify_keys(arg_sig['__kwargs__']))                
                return klass()
            raise JSONRPCDecodeError(
                'Could not decode class. Object hook for class ``%s`` not found.', class_hint['name']
            )
        return dict_obj
    
    def __strify_keys(self, dct):
        return dict([(str(k), v) for k,v in dct.iteritems()])
    
def reconstructor(*dargs, **dkw):
    '''
    Decorate the __init__ method of your ``Transmittable`` classes to describe
    how to instatiate a class after it has been sent via a json rpc call.
    
    The best way to show this is with an example:
    
    class Person(Transmittable):
        @reconstructor('__first_name', '__last_name', middle='middle')
        def __init__(self, first_name, last_name, middle=None):
            self.__first_name = first_name
            self.__last_name = last_name
            self.middle = middel
            
    new_person = Person('shawn', 'adams', middle='m')
    
    new_person as json:
    {"__classhook__": {
            "name": "Person",
            "__init__": {
                "__args__": ["shawn", "adams"],
                "__kwargs": {"middle":"m"}        
    }}}
    
        
    When this json request is recieved and decoded it will get instiated like this:
    Person('shawn', 'adams', middle='m')
    
    Passing arg or kwargs to ``reconstructor`` is completely optional. You can leave off the
    decorator entirely, causing the class to be instiated without any arguments.
    
    keyword args:
        @``skip_null_keys``(default: False) - If skip_null_keys is True an attribute whos
            value is None will not be included as a keyword argument during reinstiation
            of the class.           
    '''
    
    def decorater(func):
        def wrap(*args, **kw):
            self = args[0]            
            if not isinstance(self, Transmittable):
                raise TypeError('The ``reconstructor`` decorator should only be used on subclasses of ``Transmittable``.')
            #when the class is initialised we gather info about its signature and save it for
            #when we have to serialize it backe to json.
            self._skip_null_keys = dkw.pop('skip_null_keys', False)
            self._arg_spec['__args__'] = dargs
            self._arg_spec['__kwargs__'] = dkw
            return func(*args, **kw)            
        return wrap
    return decorater
            
class Transmittable(object):
    '''
    Base class for all objects you wish to make transmittable across the json rpc
    transport.
    '''
    #@__arg_spec - gets a value from the "reconstructor" decorator.
    _arg_spec = {}
    _skip_null_keys = False
    def to_obj(self):
        '''
        If you override this method it should return an object that represents the argumnents to be
        passed to this class's contructor. The object should follow subspec 1a
        ie:
            to_obj() returns -> {'__args__':[1,2], '__kwargs__':{'foo': True}}
            
            during decoding this class will be initialised like this:
            SomeClass(1,2, foo=True)        
        '''
        
        arg_spec = {}
        
        if '__args__' in self._arg_spec:
            arg_spec['__args__'] = [getattr(self, str(arg)) for arg in self._arg_spec['__args__']]
        if '__kwargs__' in self._arg_spec:
            arg_spec['__kwargs__'] = dict([(k, getattr(self, v)) for k,v in self._arg_spec['__kwargs__'].iteritems() \
                                           if not (self._skip_null_keys and getattr(self, v) is None)])
            
        return {'__classhook__': {'name':self.__class__.__name__, '__init__': arg_spec}}
        
    