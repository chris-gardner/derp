#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import math

from PySide import QtCore, QtGui

import depends_node
import depends_undo_commands
import tabMenu

"""
A collection of QT graphics widgets that displays and allows the user to 
manipulate a dependency graph.  From the entire scene, to the nodes, to the
connections between the nodes, to the nubs the connections connect to.
"""

dataTypeColors = {
    'number': [0.0, 1.0, 0.0],
    'string': [0.0, 0.0, 1.0],
    'boolean': [1.0, 0.5, 0.0],

}

###############################################################################
###############################################################################
class DrawNodeInputNub(QtGui.QGraphicsItem):
    """
    A QGraphicsItem representing the small clickable nub at the end of a DAG
    node.  New connections can be created by clicking and dragging from this.
    """

    Type = QtGui.QGraphicsItem.UserType + 3


    def __init__(self, index=0, name='', dataType='string'):
        """
        """
        QtGui.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)

        self.index = index
        self.radius = 14.0
        self.padding = 5
        self.verticalOffset = (self.index * self.radius) + (self.index * 5) + 30
        self.name = name
        self.dataType = dataType

        self.edgeList = list()
        self.setToolTip(self.name + '\n' + dataType)

        color = [0.5, 0.5, 0.5]
        if dataType in dataTypeColors:
            color = dataTypeColors[dataType]
        self.defaultBgColor = QtGui.QColor.fromRgbF(*color)
        self.currentBgColor = QtGui.QColor.fromRgbF(*color)


    def __addDrawEdge(self, edge):
        """
        Add a given draw edge to this node.
        """
        if edge.destDrawNode() == self:
            self.edgeList.append(edge)
        edge.adjust()


    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DrawNodeInputNub.Type


    def boundingRect(self):
        """
        Defines the clickable hit box.
        """
        return QtCore.QRectF(-self.padding, -self.padding, self.radius + self.padding, self.radius + self.padding)


    def paint(self, painter, option, widget):
        """
        Draw the nub.
        """
        painter.setBrush(QtGui.QBrush(self.currentBgColor))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        rect = QtCore.QRectF(0, 0, self.radius, self.radius)
        painter.drawEllipse(rect)

    def hilite(self, state):
        if state is True:
            self.currentBgColor = QtGui.QColor(QtCore.Qt.yellow)
        else:
            self.currentBgColor = self.defaultBgColor
        self.update()

    def hoverEnterEvent(self, event):
        self.hilite(True)

    def hoverLeaveEvent(self, event):
        self.hilite(False)


class DrawNodeOutputNub(DrawNodeInputNub):
    """
    A QGraphicsItem representing the small clickable nub at the end of a DAG
    node.  New connections can be created by clicking and dragging from this.
    """

    Type = QtGui.QGraphicsItem.UserType + 3


    def __init__(self, index=0, name='', dataType='string'):
        DrawNodeInputNub.__init__(self, index=index, name=name, dataType=dataType)


    def __addDrawEdge(self, edge):
        """
        Add a given draw edge to this node.
        """
        if edge.sourceDrawNode() == self:
            self.edgeList.append(edge)
        edge.adjust()


    def mousePressEvent(self, event):
        """
        Accept left-button clicks to create the new connection.
        """
        print self.name
        tempEdge = DrawEdge(self.parentItem(), None, floatingDestinationPoint=event.scenePos(), sourcePort=self.index)
        self.scene().addItem(tempEdge)
        self.ungrabMouse()
        tempEdge.dragging = True  # TODO: Probably better done with an DrawEdge function (still valid?)
        tempEdge.grabMouse()
        event.accept()
        return


###############################################################################
###############################################################################
class DrawNode(QtGui.QGraphicsItem):
    """
    A QGraphicsItem representing a node in a dependency graph.  These can be
    selected, moved, and connected together with DrawEdges.
    """

    Type = QtGui.QGraphicsItem.UserType + 1


    def __init__(self, dagNode):
        """
        """
        QtGui.QGraphicsItem.__init__(self)

        # The corresponding DAG node
        self.dagNode = dagNode
        # Input and output edges
        self.incomingDrawEdgeList = list()
        self.outgoingDrawEdgeList = list()

        self.inNubs = []
        for count, input in enumerate(dagNode.inputs()):
            nub = DrawNodeInputNub(index=count, name=input.name, dataType=input.dataType)
            nub.setParentItem(self)
            self.inNubs.append(nub)
        print self.inNubs

        self.outNubs = []
        for count, output in enumerate(dagNode.outputs()):
            nub = DrawNodeOutputNub(index=count, name=output.name, dataType=output.dataType)
            nub.setParentItem(self)
            self.outNubs.append(nub)
        print self.outNubs

        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        #self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)

        self.width = 150

        # calc height
        inputCount = len(dagNode.inputs())
        outputCount = len(dagNode.outputs())
        if outputCount > inputCount:
            extraHeight = outputCount * 20
        else:
            extraHeight = inputCount * 20

        self.height = 30 + extraHeight

        # For handling movement undo/redos of groups of objects
        # This is a little strange to be handled by the node itself 
        # and maybe can move elsewhere?
        self.clickSnap = None
        self.clickPosition = None

        # if type(self.dagNode) == depends_node.DagNodeDot:
        #     self.width = 15
        #     self.height = 15



    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DrawNode.Type



    def contextMenuEvent(self, contextEvent):
        menu = QtGui.QMenu()
        menu.addAction("Do stuff to this node")

        position=QtGui.QCursor.pos()
        menu.exec_(position)

       # this will tell the parent graphicsView not to use the event
        contextEvent.setAccepted(True)


    def removeDrawEdge(self, edge):
        """
        Removes the given edge from this node's list of edges.
        """
        if edge in self.incomingDrawEdgeList:
            self.incomingDrawEdgeList.remove(edge)
        elif edge in self.outgoingDrawEdgeList:
            self.outgoingDrawEdgeList.remove(edge)
        else:
            raise RuntimeError("Attempting to remove drawEdge that doesn't exist from node %s." % self.dagNode.name)


    def addDrawEdge(self, edge):
        """
        Add a given draw edge to this node.
        """
        if edge.destDrawNode() == self:
            self.incomingDrawEdgeList.append(edge)
        elif edge.sourceDrawNode() == self:
            self.outgoingDrawEdgeList.append(edge)
        edge.adjust()


    def drawEdges(self):
        """
        Return all incoming and outgoing edges in a list.
        """
        return (self.incomingDrawEdgeList + self.outgoingDrawEdgeList)


    def incomingDrawEdges(self):
        """
        Return only incoming edges in a list.
        """
        return self.incomingDrawEdgeList


    def outgoingDrawEdges(self):
        """
        Return only outgoing edges in a list.
        """
        return self.outgoingDrawEdgeList


    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        # TODO: Is this the right place to put this?  Maybe setWidth (adjust) would be fine.
        # if len(self.dagNode.name)*10 != self.width:
        # self.prepareGeometryChange()
        #   self.width = len(self.dagNode.name)*10
        #   if self.width < 9: 
        #       self.width = 9
        adjust = 2.0
        return QtCore.QRectF(0, 0, self.width + 3 + adjust, self.height + 3 + adjust)

    def shape(self):
        """
        The QT shape function.
        """
        # TODO: Find out what this is for again?
        path = QtGui.QPainterPath()
        path.addRoundedRect(self.boundingRect(), 5, 5)
        return path


    def paint(self, painter, option, widget):
        """
        Draw the node, whether it's in the highlight list, selected or 
        unselected, is currently executable, and its name.  Also draws a 
        little light denoting if it already has data present and/or if it is
        in a "stale" state.
        """
        inputsFulfilled = None

        bgColor = QtGui.QColor.fromRgbF(0.75, 0.75, 0.75)
        pen = QtGui.QPen(QtCore.Qt.black, 0)
        pen.setWidth(1)

        if option.state & QtGui.QStyle.State_Selected:
            bgColor = QtGui.QColor.fromRgbF(1, 0.6, 0.2)
            pen = QtGui.QPen(QtCore.Qt.white, 0)
            pen.setWidth(3)

        painter.setPen(pen)
        painter.setBrush(bgColor)
        fullRect = QtCore.QRectF(0, 0, self.width, self.height)
        painter.drawRoundedRect(fullRect, 2, 2)

        # No lights or text for dot nodes
        # if type(self.dagNode) == depends_node.DagNodeDot:
        #     return


        # Text (none for dot nodes)
        textRect = QtCore.QRectF(4, 4, self.boundingRect().width() - 4, 30)
        font = painter.font()
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.black)
        painter.drawText(textRect, QtCore.Qt.AlignCenter, self.dagNode.name)

        padding = 30
        spacing = 10
        halfRadius = 7
        # draw inputs
        for count, input in enumerate(self.dagNode.inputs()):
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)

            verticalOffset = (count * spacing) + (count * spacing) + padding

            textRect = QtCore.QRectF(self.boundingRect().left() + 10, verticalOffset,
                                     (self.boundingRect().width() / 2), 20)

            painter.drawText(textRect, QtCore.Qt.AlignLeft, input.name)

        for count, nub in enumerate(self.inNubs):
            verticalOffset = (count * spacing) + (count * spacing) + padding
            nub.setPos(-halfRadius, verticalOffset + 5)

        # draw outputs
        for count, output in enumerate(self.dagNode.outputs()):
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)

            verticalOffset = (count * spacing) + (count * spacing) + padding

            textRect = QtCore.QRectF(self.boundingRect().width() / 2, verticalOffset,
                                     (self.boundingRect().width() / 2) - 15, 20)
            painter.drawText(textRect, QtCore.Qt.AlignRight, output.name)

        for count, nub in enumerate(self.outNubs):
            verticalOffset = (count * spacing) + (count * spacing) + padding
            nub.setPos(self.boundingRect().width() - 10, verticalOffset + 5)



    def mousePressEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        print 'mouse event'
        if event.button() == QtCore.Qt.LeftButton:
            # Let the QT parent class handle the selection process before querying what's selected
            self.clickSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                       connectionMetaDict=self.scene().connectionMetaDict())
            self.clickPosition = self.pos()
        else:
            print 'some other button'
        QtGui.QGraphicsItem.mousePressEvent(self, event)


    def mouseReleaseEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        # Don't register undos for selections without moves
        if self.pos() != self.clickPosition:
            currentSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                    connectionMetaDict=self.scene().connectionMetaDict())
            self.scene().undoStack().push(
                depends_undo_commands.SceneOnlyUndoCommand(self.clickSnap, currentSnap, self.scene()))
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)


    def itemChange(self, change, value):
        """
        If the node has been moved, update all of its draw edges.
        """
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.drawEdges():
                edge.adjust()
        return QtGui.QGraphicsItem.itemChange(self, change, value)


###############################################################################
###############################################################################
class DrawEdge(QtGui.QGraphicsItem):
    """
    A QGraphicsItem representing a connection between two DAG nodes.  These can
    be clicked and dragged to change, add, or remove connections between nodes.
    """

    TwoPi = 2.0 * math.pi
    Type = QtGui.QGraphicsItem.UserType + 2


    def __init__(self, sourceDrawNode, destDrawNode, floatingDestinationPoint=0.0, sourcePort=0, destPort=0):
        """
        """
        QtGui.QGraphicsItem.__init__(self)

        self.arrowSize = 10.0
        self.sourcePoint = QtCore.QPointF()
        self.destPoint = QtCore.QPointF()
        self.horizontalConnectionOffset = 0.0
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

        self.setZValue(-2)

        self.sourcePort = sourcePort
        self.destPort = destPort

        self.source = sourceDrawNode
        self.dest = destDrawNode
        if self.dest:
            self.dest.addDrawEdge(self)
        else:
            self.floatingDestinationPoint = floatingDestinationPoint

        if self.source:
            self.source.addDrawEdge(self)
        else:
            self.floatingSourcePoint = floatingDestinationPoint

        self.adjust()

        # MouseMoved is a little hack to get around a bug where clicking the mouse and not dragging caused an error
        self.mouseMoved = False
        self.dragging = False


    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DrawEdge.Type


    def sourceDrawNode(self):
        """
        Simple accessor.
        """
        return self.source


    def setSourceDrawNode(self, drawNode):
        """
        Set the edge's source draw node and adjust the edge's representation.
        """
        self.source = drawNode
        self.adjust()


    def destDrawNode(self):
        """
        Simple accessor.
        """
        return self.dest


    def setDestDrawNode(self, drawNode):
        """
        Set the edge's destination draw node and adjust the edge's representation.
        """
        self.dest = drawNode
        self.adjust()


    def adjust(self):
        """
        Recompute where the line is pointing.
        """
        if not self.source:
            return

        if self.dest:
            line = QtCore.QLineF(self.mapFromItem(self.source, self.source.width, 0), self.mapFromItem(self.dest, 0, 0))
        else:
            line = QtCore.QLineF(self.mapFromItem(self.source, self.source.width, 0), self.floatingDestinationPoint)
        length = line.length()

        if length == 0.0:
            return

        radius = 5

        sourceOffset = (self.sourcePort * 10) + (self.sourcePort * 10) + 35 + radius
        destOffset = (self.destPort * 10) + (self.destPort * 10) + 35 + radius

        self.prepareGeometryChange()
        self.sourcePoint = line.p1() + QtCore.QPointF(radius, sourceOffset)
        if self.dest:
            self.destPoint = line.p2() + QtCore.QPointF(-radius, destOffset)
        else:
            self.destPoint = line.p2()


    def boundingRect(self):
        """
        Hit box assistance.  Only let the user click on the tip of the line.
        """
        if not self.source:  # or not self.dest:
            return QtCore.QRectF()
        penWidth = 1
        extra = (penWidth + self.arrowSize) / 2.0
        return QtCore.QRectF(self.sourcePoint,
                             QtCore.QSizeF(self.destPoint.x() - self.sourcePoint.x(),
                                           self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra,
                                                                                                             -extra,
                                                                                                             extra,
                                                                                                             extra)


    def shape(self):
        """
        The QT shape function.
        """
        # Setup and stroke the line
        path = QtGui.QPainterPath(self.sourcePoint)
        path.lineTo(self.destPoint)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(4)
        stroked = stroker.createStroke(path)
        # Add a square at the tip
        stroked.addRect(self.destPoint.x() - 10, self.destPoint.y() - 10, 20, 20)
        return stroked


    def paint(self, painter, option, widget):
        """
        Draw a line with an arrow at the end.
        """
        if not self.source:  # or not self.dest:
            return

        # Draw the line
        line = QtCore.QLineF(self.sourcePoint, self.destPoint)
        if line.length() == 0.0:
            return
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(line)

        # Draw the arrows if there's enough room.
        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = DrawEdge.TwoPi - angle
        destArrowP1 = self.destPoint + QtCore.QPointF(math.sin(angle - math.pi / 3) * self.arrowSize,
                                                      math.cos(angle - math.pi / 3) * self.arrowSize)
        destArrowP2 = self.destPoint + QtCore.QPointF(math.sin(angle - math.pi + math.pi / 3) * self.arrowSize,
                                                      math.cos(angle - math.pi + math.pi / 3) * self.arrowSize)
        painter.setBrush(QtCore.Qt.white)
        painter.drawPolygon(QtGui.QPolygonF([line.p2(), destArrowP1, destArrowP2]))


    def mousePressEvent(self, event):
        """
        Accept left-button clicks to drag the arrow.
        """
        event.accept()
        self.dragging = True
        # QtGui.QGraphicsItem.mousePressEvent(self, event)


    def mouseMoveEvent(self, event):
        """
        Node head dragging.
        """
        if self.dragging:
            self.mouseMoved = True
            self.floatingDestinationPoint = event.scenePos()
            if self.destDrawNode():
                # Disconnect an edge from a node
                preSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                    connectionMetaDict=self.scene().connectionMetaDict())

                self.destDrawNode().removeDrawEdge(self)
                self.scene().nodesDisconnected.emit(self.sourceDrawNode().dagNode, self.destDrawNode().dagNode)
                self.setDestDrawNode(None)

                currentSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                        connectionMetaDict=self.scene().connectionMetaDict())
                self.scene().undoStack().push(
                    depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.scene().dag, self.scene()))
            # nodes = [n for n in self.scene().items(self.floatingDestinationPoint) if type(n) in [DrawNodeInputNub, DrawNodeOutputNub]]
            # if nodes:
            # print nodes
            self.adjust()
            # TODO: Hoover-color nodes as potential targets
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)


    def mouseReleaseEvent(self, event):
        """
        Dropping the connection onto a node connects it to the node and emits 
        an appropriate signal.  Dropping the connection into space deletes the
        connection.
        """
        if self.dragging and self.mouseMoved:
            self.dragging = False

            # A little weird - seems to be necessary when passing mouse control from the nub to here
            self.ungrabMouse()

            # Hits?
            nodes = [n for n in self.scene().items(self.floatingDestinationPoint) if
                     type(n) in [DrawNodeInputNub, DrawNodeOutputNub]]
            if nodes:
                topHitNode = nodes[0]

                self.destPort = topHitNode.index

                duplicatingConnection = self.sourceDrawNode().dagNode in self.scene().dag.nodeConnectionsIn(
                    topHitNode.parentItem().dagNode)
                if topHitNode is not self.sourceDrawNode() and not duplicatingConnection:
                    # Connect an edge to a node
                    preSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                        connectionMetaDict=self.scene().connectionMetaDict())

                    self.setDestDrawNode(topHitNode.parentItem())

                    print 'connecting:', self.sourceDrawNode().dagNode, 'port:', self.sourcePort
                    print 'to:', self.destDrawNode().dagNode, 'port:', self.destPort

                    sourcePortType = self.sourceDrawNode().dagNode.outputs()[self.sourcePort].dataType
                    destNodeType = self.destDrawNode().dagNode.inputs()[self.destPort].dataType

                    print sourcePortType, destNodeType

                    if sourcePortType != destNodeType:
                        print 'types dont match - bailing'
                        self.sourceDrawNode().removeDrawEdge(self)
                        self.scene().removeItem(self)
                        self.mouseMoved = False
                        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
                        return

                    self.dest.addDrawEdge(self)
                    self.horizontalConnectionOffset = 0.0
                    self.scene().nodesConnected.emit(self.sourceDrawNode().dagNode, self.destDrawNode().dagNode,
                                                     self.sourcePort, self.destPort)
                    self.adjust()

                    currentSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(),
                                                            connectionMetaDict=self.scene().connectionMetaDict())
                    self.scene().undoStack().push(
                        depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.scene().dag,
                                                                     self.scene()))
                    return QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

            # No hits?  Delete yourself (You have no chance to win!)
            self.sourceDrawNode().removeDrawEdge(self)
            self.scene().removeItem(self)

        self.mouseMoved = False
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)


###############################################################################
###############################################################################
class DrawGroupBox(QtGui.QGraphicsItem):
    """
    A simple box that draws around groups of DrawNodes.  Denotes which nodes
    are grouped together.
    """

    Type = QtGui.QGraphicsItem.UserType + 4


    def __init__(self, initialBounds=QtCore.QRectF(), name=""):
        """
        """
        QtGui.QGraphicsItem.__init__(self)
        self.name = name
        self.bounds = initialBounds
        self.setZValue(-3)


    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DrawGroupBox.Type


    def boundingRect(self):
        """
        Hit box assistance.
        """
        return self.bounds


    def paint(self, painter, option, widget):
        """
        Simply draw a grey box behind the nodes it encompasses.
        """
        # TODO: This box is currently not dynamically-sizable.  Fix!
        painter.setBrush(QtGui.QColor(62, 62, 62))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.bounds)


###############################################################################
###############################################################################
class SceneWidget(QtGui.QGraphicsScene):
    """
    The QGraphicsScene that contains the contents of a given dependency graph.
    """

    # Signals
    nodesDisconnected = QtCore.Signal(depends_node.DagNode, depends_node.DagNode)
    nodesConnected = QtCore.Signal(depends_node.DagNode, depends_node.DagNode, int, int)

    def __init__(self, parent=None):
        """
        """
        QtGui.QGraphicsScene.__init__(self, parent)

        # Call setDag() when setting the dag to make sure everything is cleaned up properly
        self.dag = None

        # The lists of highlight nodes and their matching intensities.
        self.highlightNodes = list()
        self.highlightIntensities = list()


    def undoStack(self):
        """
        An accessor to the application's global undo stack, guaranteed to be created
        by the time it's needed.
        """
        return self.parent().parent().undoStack


    def drawNodes(self):
        """
        Returns a list of all drawNodes present in the scene.
        """
        nodes = list()
        for item in self.items():
            if type(item).__name__ == 'DrawNode':
                nodes.append(item)
        return nodes


    def drawNode(self, dagNode):
        """
        Returns the given dag node's draw node (or None if it doesn't exist in
        the scene).
        """
        for item in self.items():
            if type(item).__name__ != 'DrawNode':
                continue
            if item.dagNode == dagNode:
                return item
        return None


    def drawEdges(self):
        """
        Return a list of all draw edges in the scene.
        """
        edges = list()
        for item in self.items():
            if type(item).__name__ == 'DrawEdge':
                edges.append(item)
        return edges


    def drawEdge(self, fromDrawNode, toDrawNode):
        """
        Returns a drawEdge that links a given draw node to another given draw
        node.
        """
        for item in self.items():
            if type(item).__name__ != 'DrawEdge':
                continue
            if item.source == fromDrawNode and item.dest == toDrawNode:
                return item
        return None


    def setDag(self, dag):
        """
        Sets the current dependency graph and refreshes the scene.
        """
        self.clear()
        self.dag = dag


    def addExistingDagNode(self, dagNode, position):
        """
        Adds a new draw node for a given dag node at a given position.
        """
        newNode = DrawNode(dagNode)
        self.addItem(newNode)
        newNode.setPos(position)
        return newNode


    def addExistingConnection(self, fromDagNode, toDagNode, sourcePort=0, destPort=0):
        """
        Adds a new draw edge for given from and to dag nodes.
        """
        fromDrawNode = self.drawNode(fromDagNode)
        toDrawNode = self.drawNode(toDagNode)
        if not fromDrawNode:
            raise RuntimeError(
                "Attempting to connect node %s which is not yet registered to QGraphicsScene." % fromDagNode.name)
        if not toDrawNode:
            raise RuntimeError(
                "Attempting to connect node %s which is not yet registered to QGraphicsScene." % toDagNode.name)
        newDrawEdge = DrawEdge(fromDrawNode, toDrawNode, sourcePort=sourcePort, destPort=destPort)
        self.addItem(newDrawEdge)
        return newDrawEdge


    def addExistingGroupBox(self, name, groupDagNodeList):
        """
        Add a group box from a given list of dag nodes & names it with a string.
        """
        drawNodes = [self.drawNode(dn) for dn in groupDagNodeList]
        bounds = QtCore.QRectF()
        for drawNode in drawNodes:
            bounds = bounds.united(drawNode.sceneBoundingRect())
        adjust = bounds.width() if bounds.width() > bounds.height() else bounds.height()
        adjust *= 0.05
        bounds.adjust(-adjust, -adjust, adjust, adjust)
        newGroupBox = DrawGroupBox(bounds, name)
        self.addItem(newGroupBox)


    def removeExistingGroupBox(self, name):
        """
        Removes a group box with a given name.
        """
        boxes = [n for n in self.items() if type(n) == DrawGroupBox]
        for box in boxes:
            if box.name == name:
                self.removeItem(box)
                return
        raise RuntimeError("Group box named %s does not appear to exist in the QGraphicsScene." % name)


    def refreshDrawNodes(self, dagNodes):
        """
        Refresh the draw nodes representing a given list of dag nodes.
        """
        for drawNode in [self.drawNode(n) for n in dagNodes]:
            drawNode.update()





    def mousePressEvent(self, event):
        """
        Stifles a rubber-band box when clicking on a node and moving it.
        """
        # This allows an event to propagate without actually doing what it wanted to do 
        # in the first place (draw a rubber band box for all click-drags - including middle mouse)
        # (http://www.qtcentre.org/threads/36953-QGraphicsItem-deselected-on-contextMenuEvent)
        if event.button() != QtCore.Qt.LeftButton:
            event.accept()
            return
        QtGui.QGraphicsScene.mousePressEvent(self, event)


    def nodeMetaDict(self):
        """
        Returns a dictionary containing meta information for each of the draw 
        nodes in the scene.
        """
        nodeMetaDict = dict()
        nodes = [n for n in self.items() if type(n) == DrawNode]
        for n in nodes:
            nodeMetaDict[str(n.dagNode.uuid)] = dict()
            nodeMetaDict[str(n.dagNode.uuid)]['locationX'] = str(n.pos().x())
            nodeMetaDict[str(n.dagNode.uuid)]['locationY'] = str(n.pos().y())
        return nodeMetaDict


    def connectionMetaDict(self):
        """
        Returns a dictionary containing meta information for each of the draw
        edges in the scene.
        """
        connectionMetaDict = dict()
        connections = [n for n in self.items() if type(n) == DrawEdge]
        for c in connections:
            if not c.sourceDrawNode() or not c.destDrawNode():
                continue
            connectionString = "%s|%s" % (str(c.sourceDrawNode().dagNode.uuid), str(c.destDrawNode().dagNode.uuid))
            connectionMetaDict[connectionString] = dict()
            connectionMetaDict[connectionString]['sourcePort'] = c.sourcePort
            connectionMetaDict[connectionString]['destPort'] = c.destPort
        return connectionMetaDict


    def restoreSnapshot(self, snapshotDict):
        """
        Given a dictionary that contains dag information and meta information 
        for the dag, construct all draw objects and register them with the 
        current scene.
        """
        # Clear out the drawnodes and connections, then add 'em all back in.
        selectedItems = self.selectedItems()
        self.blockSignals(True)
        for dn in self.drawNodes():
            self.removeItem(dn)
        for de in self.drawEdges():
            self.removeItem(de)
        for dagNode in self.dag.nodes():
            newNode = self.addExistingDagNode(dagNode, QtCore.QPointF(0, 0))
            if selectedItems and dagNode in [x.dagNode for x in selectedItems]:
                newNode.setSelected(True)
        for connection in self.dag.connections():
            newDrawEdge = self.addExistingConnection(connection[0], connection[1])
        self.blockSignals(False)

        # DrawNodes get their locations set from this meta entry
        expectedNodeMeta = snapshotDict["NODE_META"]
        if expectedNodeMeta:
            for dagNode in self.dag.nodes():
                drawNode = self.drawNode(dagNode)
                nodeMeta = expectedNodeMeta[str(dagNode.uuid)]
                if 'locationX' in nodeMeta:
                    locationX = float(nodeMeta['locationX'])
                if 'locationY' in nodeMeta:
                    locationY = float(nodeMeta['locationY'])
                drawNode.setPos(QtCore.QPointF(locationX, locationY))

        # DrawEdges get their insertion points set here
        expectedConnectionMeta = snapshotDict["CONNECTION_META"]
        if expectedConnectionMeta:
            for connection in self.dag.connections():
                connectionIdString = "%s|%s" % (str(connection[0].uuid), str(connection[1].uuid))
                connectionMeta = expectedConnectionMeta[connectionIdString]
                drawEdge = self.drawEdge(self.drawNode(self.dag.node(nUUID=connection[0].uuid)),
                                         self.drawNode(self.dag.node(nUUID=connection[1].uuid))
                )
                if drawEdge:
                    drawEdge.sourcePort = connectionMeta['sourcePort']
                    drawEdge.destPort = connectionMeta['destPort']
                    drawEdge.adjust()


###############################################################################
###############################################################################
class GraphicsViewWidget(QtGui.QGraphicsView):
    """
    The QGraphicsView into a QGraphicsScene it owns.  This object handles the
    mouse and board behavior of the dependency graph inside the view.
    """

    # Signals
    createNode = QtCore.Signal(type, QtCore.QPointF)

    def __init__(self, parent=None):
        """
        """
        QtGui.QGraphicsView.__init__(self, parent)

        # Setup our own Scene Widget and assign it to the View.
        scene = SceneWidget(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        scene.setSceneRect(-20000, -20000, 40000, 40000)
        self.setScene(scene)

        # Mouse Interaction
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)

        # Hide the scroll bars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Window properties
        self.setWindowTitle(self.tr("Depends"))
        self.setMinimumSize(200, 200)
        self.scale(1.0, 1.0)
        # self.setFocusPolicy(QtCore.Qt.StrongFocus)


        self.boxing = False
        self.modifierBoxOrigin = None
        self.modifierBox = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)

    def centerCoordinates(self):
        """
        Returns a QPoint containing the scene location the center of this view 
        is pointing at.
        """
        topLeft = QtCore.QPointF(self.horizontalScrollBar().value(), self.verticalScrollBar().value())
        topLeft += self.geometry().center()
        return topLeft


    def frameBounds(self, bounds):
        """
        Frames a given bounding rectangle within the viewport.
        """
        if bounds.isEmpty():
            return
        widthAdjust = bounds.width() * 0.2
        heightAdjust = bounds.height() * 0.2
        bounds.adjust(-widthAdjust, -heightAdjust, widthAdjust, heightAdjust)
        self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)


    def contextMenuEvent(self, contextEvent):

        QtGui.QGraphicsView.contextMenuEvent(self, contextEvent)
        # check that the event hasn't been accepted by a child (eg, a DagNode)
        if not contextEvent.isAccepted():
            position = contextEvent.pos()
            contextMenu = QtGui.QMenu()
            menuActions = self.parent().createCreateMenuActions()
            for action in menuActions:
                cat = None
                for eAct in contextMenu.actions():
                    if eAct.menu():
                        if eAct.text() == action.category:
                            cat = eAct.menu()
                            break

                if not cat:
                    cat = QtGui.QMenu(contextMenu)
                    cat.setTitle(action.category)
                    contextMenu.addMenu(cat)

                action.setData((action.data()[0], self.mapToScene(position)))
                cat.addAction(action)
            contextMenu.exec_(self.mapToGlobal(position))


    def event(self, event):
        # have to trap the tab key in the general 'event' handler
        # because tab doesn't get passed to keyPressEvent
        if (event.type() == QtCore.QEvent.KeyPress) and (event.key() == QtCore.Qt.Key_Tab):
            #cursor = QtGui.QCursor()
            #self.contextMenuEvent(self.mapFromGlobal(cursor.pos()))
            #t = tabMenu.TabTabTabWidget(winflags=QtCore.Qt.FramelessWindowHint)
            #t.under_cursor()

            # Show, and make front-most window (mostly for OS X)
            #t.show()
            #t.raise_()
            return True

        return QtGui.QGraphicsView.event(self, event)

    def keyPressEvent(self, event):
        """
        Stifles autorepeat and handles a few shortcut keys that aren't 
        registered as functions in the main window.
        """
        # This widget will never process auto-repeating keypresses so ignore 'em all
        if event.isAutoRepeat():
            return
        # Frame selected/all items
        if event.key() == QtCore.Qt.Key_F:
            itemList = list()
            if self.scene().selectedItems():
                itemList = self.scene().selectedItems()
            else:
                itemList = self.scene().items()
            bounds = QtCore.QRectF()
            for item in itemList:
                bounds |= item.sceneBoundingRect()
            self.frameBounds(bounds)


    def keyReleaseEvent(self, event):
        """
        Stifle auto-repeats and handle letting go of the space bar.
        """
        # Ignore auto-repeats
        if event.isAutoRepeat():
            return

        # Clear the highlight list if you just released the space bar
        if event.key() == QtCore.Qt.Key_Space:
            self.scene().setHighlightNodes([], intensities=None)


    def mousePressEvent(self, event):
        """
        Special handling is needed for a drag-box that toggles selected 
        elements with the CTRL button.
        """
        # Handle CTRL+MouseClick box behavior
        if event.modifiers() & QtCore.Qt.ControlModifier:
            itemUnderMouse = self.itemAt(event.pos().x(), event.pos().y())
            if not itemUnderMouse:
                self.modifierBoxOrigin = event.pos()
                self.boxing = True
                event.accept()
                return
        QtGui.QGraphicsView.mousePressEvent(self, event)


    def mouseMoveEvent(self, event):
        """
        Panning the viewport around and CTRL+mouse drag behavior.
        """
        # Panning
        if event.buttons() & QtCore.Qt.MiddleButton:
            delta = event.pos() - self.lastMousePos
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.lastMousePos = event.pos()
        else:
            self.lastMousePos = event.pos()

        # Handle Modifier+MouseClick box behavior
        if event.buttons() & QtCore.Qt.LeftButton and event.modifiers() & QtCore.Qt.ControlModifier:
            if self.boxing:
                self.modifierBox.setGeometry(QtCore.QRect(self.modifierBoxOrigin, event.pos()).normalized())
                self.modifierBox.show()
                event.accept()
                return

        QtGui.QGraphicsView.mouseMoveEvent(self, event)


    def mouseReleaseEvent(self, event):
        """
        The final piece of the CTRL+drag box puzzle.
        """
        # Handle Modifier+MouseClick box behavior
        if self.boxing:
            # Blocking the scene's signals insures only a single selectionChanged
            # gets emitted at the very end.  This was necessary since the way I
            # have written the property widget appears to freak out when refreshing
            # twice instantaneously (see MainWindow's constructor for additional details).
            nodesInHitBox = [x for x in self.items(QtCore.QRect(self.modifierBoxOrigin, event.pos()).normalized()) if
                             type(x) is DrawNode]
            self.scene().blockSignals(True)
            for drawNode in nodesInHitBox:
                drawNode.setSelected(not drawNode.isSelected())
            self.scene().blockSignals(False)
            self.scene().selectionChanged.emit()
            self.modifierBox.hide()
            self.boxing = False
        QtGui.QGraphicsView.mouseReleaseEvent(self, event)


    def wheelEvent(self, event):
        """
        Zooming.
        """
        self.scaleView(math.pow(2.0, event.delta() / 240.0))


    def drawBackground(self, painter, rect):
        """
        Filling.
        """
        sceneRect = self.sceneRect()
        painter.fillRect(rect.intersect(sceneRect), QtGui.QBrush(QtCore.Qt.darkGray, QtCore.Qt.SolidPattern))
        painter.drawRect(sceneRect)


    def scaleView(self, scaleFactor):
        """
        Zoom helper function.
        """
        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
        if factor < 0.07 or factor > 100:
            return
        self.scale(scaleFactor, scaleFactor)
