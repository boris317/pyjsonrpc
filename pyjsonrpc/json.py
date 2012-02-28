from simplejson import JSONEncoder
from pyjsonrpc.object_hook import Transmittable

class RPCEncoder(JSONEncoder):
    """
    Custom json enconder, used instead of json.dumps. This class knows
    how to get an object suitable for json encoding from a Transmittable object.
    """
    def default(self, obj):
        if isinstance(obj, Transmittable):
            return obj.to_obj()
        return JSONEncoder.default(self, obj)
            
        