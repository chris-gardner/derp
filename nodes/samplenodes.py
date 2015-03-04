#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import depends_node
import depends_data_packet



class DagNodeInteger(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        """
        """
        docLong = ("Number")
        return [
              depends_node.DagNodeAttribute('number', "1", docString=docLong)]

    def executePython(self, nodesBefore):
        myVal = int(self.attributeValue('number'))
        self.outVal = myVal


class DagNodeFloat(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        """
        """
        docLong = ("Number")
        return [
              depends_node.DagNodeAttribute('number', "1.0", docString=docLong)]


    def executePython(self, nodesBefore):
        myVal = float(self.attributeValue('number'))
        self.outVal = myVal


class DagNodeAdd(depends_node.DagNode):
    category = 'Math'

    def executePython(self, nodesBefore):
        outVal = 0

        print 'nodes before:'.center(60, '*')
        for x in nodesBefore:
            print x, x.outVal
            if x.outVal:
                outVal += x.outVal

        print 'new outval', outVal

        self.outVal = outVal


class DagNodeRange(depends_node.DagNode):
    category = 'Math'

    def _defineAttributes(self):
        return [
              depends_node.DagNodeAttribute('start', "1", docString="Start of range"),
              depends_node.DagNodeAttribute('end', "100", docString='End of range')
        ]

    def executePython(self, nodesBefore):
        outVal = []
        start = int(self.attributeValue('start'))
        end = int(self.attributeValue('end'))
        outVal = range(start, end + 1)
        print 'outval', outVal
        self.outVal = outVal


class DagNodeRepeat(depends_node.DagNode):
    category = 'Flow Control'

    def executePython(self, nodesBefore):
        if len(nodesBefore) >= 2:
            outVal = []

            loopNode = nodesBefore[0]
            print loopNode
            doNode = nodesBefore[1]
            print doNode

            loopList = loopNode.outVal
            if isinstance(loopList, list):
                for x in loopList:
                    outVal.append(doNode.outVal)
            else:
                print 'no list, cannot loop'


            self.outVal = outVal
        else:
            self.outVal = None