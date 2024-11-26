from typing import Callable


class GUIProperty:
    def __init__(self, default_value: any):
        self._value = default_value
        self.listeners: dict[any, Callable[[any], None]] = {}

    def setValue(self, value):
        self._value = value
        for listener in self.listeners.values():
            listener(value)

    def getValue(self):
        return self._value

    def addListener(self, key: any, listener: Callable[[any], None]):
        self.listeners[key] = listener

    def removeListener(self, key: any):
        del self.listeners[key]
