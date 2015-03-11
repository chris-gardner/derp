#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import depends_node
import depends_data_packet
from depends_node import DagNodeInput, DagNodeOutput



class DagNodeInteger(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        return [depends_node.DagNodeAttribute('number', "1", docString='Number')]

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
        return [depends_node.DagNodeAttribute('number', "1.0", docString='Number')]

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




