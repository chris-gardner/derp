#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import depends_node
from depends_node import DagNodeInput, DagNodeOutput



class DagNodeExecute(depends_node.DagNode):
    category = 'Base'

    def _defineAttributes(self):
        return []

    def _defineInputs(self):
        return [DagNodeInput('input1', 'any', None)]

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'any', None)]

    def executePython(self):
        print 'execute node'
        outVal = []
        values = self.getPortValues(0)
        if values:
            outVal = values

        print 'new outval', outVal

        self.outVal = outVal



class DagNodeAttrTest(depends_node.DagNode):
    category = 'Base'

    def _defineAttributes(self):
        return [
            depends_node.DagNodeAttribute('numberAttr', '1', dataType='int'),
            depends_node.DagNodeAttribute('booleanAttr', True, dataType='bool'),
            depends_node.DagNodeAttribute('stringAttr', 'asdf', dataType='string'),
            depends_node.DagNodeAttribute('boolenAttr', True, dataType='bool'),

        ]

    def _defineInputs(self):
        return [DagNodeInput('input1', 'bool', None)]

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'bool', None)]

    def executePython(self):
        myVal = float(self.attributeValue('booleanAttr'))
        self.outVal = myVal

