"""
This class is represents a single field that can be added to type Discord.Embed
"""

class EmbedField:
    def __init__(self):
        self._name = ''
		self._value = ''
		self.inline = False
		
    @property
    def name(self): # implements the get - this name is *the* name
        return self._name
    
    @name.setter
    def name(self, name): # name must be the same
        self._name = name
	
	
	@property
    def value(self): # implements the get - this name is *the* name
        return self._value
    
    @value.setter
    def value(self, value): # name must be the same
        self._value = value
		
		
	@property
    def inline(self): # implements the get - this name is *the* name
        return self._inline
    
    @value.setter
    def inline(self, inline): # name must be the same
        self._inline = inline
    
