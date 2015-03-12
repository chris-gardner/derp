#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import depends_node
from depends_node import DagNodeInput, DagNodeOutput



class DagNodeInteger(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        return [depends_node.DagNodeAttribute('number', '1', dataType='int', docString='Number')]

    def _defineInputs(self):
        return []

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'number', None)]

    def executePython(self):
        myVal = int(self.attributeValue('number'))
        self.outVal = myVal



class DagNodeFloat(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        return [depends_node.DagNodeAttribute('number', '1.0', dataType='float', docString='Number')]

    def _defineInputs(self):
        return []

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'number', None)]

    def executePython(self,):
        myVal = float(self.attributeValue('number'))
        self.outVal = myVal



class DagNodeAdd(depends_node.DagNode):
    category = 'Math'

    def _defineInputs(self):
        return [DagNodeInput('input1', 'number', None)]

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'number', None)]

    def executePython(self,):
        outVal = 0
        for index, input in enumerate(self.inputs()):
            values = self.getPortValues(index)
            print 'value for port', input, index,
            for val in values:
                print val
                outVal += val



        print 'new outval', outVal

        self.outVal = outVal



class DagNodeMultiply(depends_node.DagNode):
    category = 'Math'

    def _defineInputs(self):
        return [DagNodeInput('input1', 'number', None)]

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'number', None)]

    def executePython(self,):

        # surprisingly complicated - if you start off with a base value of zero, it'll multiply everything by...
        # you guessed it... zero.

        prevVal = None
        outVal = 0
        values = self.getPortValues(0)
        print 'value for port', input, 0
        print values

        if len(values) == 0:
            outVal = 0

        elif len(values) == 1:
            outVal = values[0]

        else:
            for val in values:
                if prevVal is None:
                    prevVal = val
                else:
                    outVal = val * prevVal



        print 'new outval', outVal

        self.outVal = outVal

