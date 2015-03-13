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

