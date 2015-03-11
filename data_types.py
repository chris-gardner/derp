__author__ = 'chris.gardner'

class dataTypeBase(object):
    """"""
    
    def __init__(self, typeName='', color=[1.0, 0.0, 0.0]):
        """Constructor for dataTypeBase"""
        self.typeName = typeName
        self.color = color

    def validate(self, value):
        return False

