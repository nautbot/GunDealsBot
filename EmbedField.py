"""
This class represents a single field that can be added to type Discord.Embed
"""


class EmbedField:
    def __init__(self, value, name="", inline=True):
        self._name = name
        self._value = value
        self._inline = inline

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, value):
            self._name = value

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

        @property
        def inline(self):
            return self._inline

        @value.setter
        def inline(self, value):
            self._inline = value

    def __str__(self):
        return str("name:{}, value:{}, inline:{}".format(self._name, self._value, self._inline))
