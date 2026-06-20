import inspect

class AdapterPluginRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, name, cls):
        self._registry[name] = cls

    def get(self, name):
        return self._registry.get(name)

    def auto_discover(self, module):
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                self.register(name, obj)