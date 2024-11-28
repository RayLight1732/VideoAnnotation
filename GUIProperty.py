from typing import Callable


class GUIProperty:
    def __init__(self, default_value: any):
        self._value = default_value
        self.listeners: dict[any, Callable[[any], None]] = {}
        self.converter = None

    def setValue(self, source, value):
        if self.converter:
            value = self.converter(value)
        self._value = value
        for listener in self.listeners.values():
            listener(source, value)

    def getValue(self):
        return self._value

    def addListener(self, key: any, listener: Callable[[any, any], None]):
        self.listeners[key] = listener

    def removeListener(self, key: any):
        del self.listeners[key]

    def setValueConverter(self, converter: Callable[[any], any]):
        self.converter = converter
