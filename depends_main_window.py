#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import os
import sys
import json
import tempfile
import itertools

from PySide import QtCore, QtGui

import depends_dag
import depends_node
import depends_util
import depends_variables
import depends_data_packet
import depends_undo_commands
import depends_property_widget
import depends_variable_widget
import depends_graphics_widgets


"""
The main window which contains the dependency graph view widget and a dock for 
additional windows.  Executing the program from the commandline interface 
creates one of these windows (and therefore all startup routines execute), but 
does not display it.
"""


###############################################################################
###############################################################################
class MainWindow(QtGui.QMainWindow):
    """
    This class constructs the UI, consisting of the many windows, menu items,
    undo managers, plugin systems, workflow variables, etc.  It also holds 
    functions to manage what happens when dag nodes change (see "DAG management"
    section), loading and saving of DAG snapshots, and much 
    """

    def __init__(self, startFile="", parent=None):
        """
        """
        QtGui.QMainWindow.__init__(self, parent)

        # Add the DAG widget
        self.graphicsViewWidget = depends_graphics_widgets.GraphicsViewWidget(self)
        self.graphicsScene = self.graphicsViewWidget.scene()
        self.setCentralWidget(self.graphicsViewWidget)

        # Create the docking widget for the properties dialog
        self.propDock = QtGui.QDockWidget()
        self.propDock.setObjectName('propDock')
        self.propDock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        self.propDock.setWindowTitle("Properties")
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.propDock)

        # Create and add the properties dialog to the dock widget
        self.propWidget = depends_property_widget.PropWidget(self)
        self.propDock.setWidget(self.propWidget)


        # Create the docking widget for the variable dialog
        self.variableDock = QtGui.QDockWidget()
        self.variableDock.setObjectName('variableDock')
        self.variableDock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        self.variableDock.setWindowTitle("Variables")
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.variableDock)

        # Create and add the variable dialog to the dock widget
        self.variableWidget = depends_variable_widget.VariableWidget(self)
        self.variableDock.setWidget(self.variableWidget)
        self.variableWidget.rebuild(depends_variables.variableSubstitutions)
        # self.variableDock.hide()

        # Set some locals
        self.dag = None
        self.undoStack = QtGui.QUndoStack(self)

        # Undo and Redo have built-in ways to create their menus
        undoAction = self.undoStack.createUndoAction(self, "&Undo")
        undoAction.setShortcuts(QtGui.QKeySequence.Undo)
        redoAction = self.undoStack.createRedoAction(self, "&Redo")
        redoAction.setShortcuts(QtGui.QKeySequence.Redo)

        # Create the menu bar
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(QtGui.QAction("&Open DAG...", self, shortcut="Ctrl+O", triggered=self.openDialog))
        fileMenu.addAction(QtGui.QAction("&Save DAG", self, shortcut="Ctrl+S", triggered=lambda: self.save(self.workingFilename)))
        fileMenu.addAction(QtGui.QAction("Save DAG &Version Up", self, shortcut="Ctrl+Space", triggered=self.saveVersionUp))
        fileMenu.addAction(QtGui.QAction("Save DAG &As...", self, shortcut="Ctrl+Shift+S", triggered=self.saveAs))
        fileMenu.addAction(QtGui.QAction("&Quit...", self, shortcut="Ctrl+Q", triggered=self.close))
        editMenu = self.menuBar().addMenu("&Edit")
        editMenu.addAction(undoAction)
        editMenu.addAction(redoAction)
        editMenu.addSeparator()


        createMenu = self.menuBar().addMenu("&Nodes")
        editMenu.addAction(QtGui.QAction("&Delete Node(s)", self, shortcut="Delete", triggered=self.deleteSelectedNodes))
        editMenu.addAction(QtGui.QAction("&Shake Node(s)", self, shortcut="Backspace", triggered=self.shakeSelectedNodes))
        editMenu.addAction(QtGui.QAction("D&uplicate Node", self, shortcut="Ctrl+D", triggered=self.duplicateSelectedNodes))
        editMenu.addSeparator()
        editMenu.addAction(QtGui.QAction("&Group Nodes", self, shortcut="Ctrl+G", triggered=self.groupSelectedNodes))
        editMenu.addAction(QtGui.QAction("&Ungroup Nodes", self, shortcut="Ctrl+Shift+G", triggered=self.ungroupSelectedNodes))
        executeMenu = self.menuBar().addMenu("E&xecute")
        executeMenu.addAction(QtGui.QAction("Execute &Selected Node", self, shortcut= "Ctrl+Shift+E", triggered=lambda: self.executeSelected(executeImmediately=True)))
        recipeMenu = executeMenu.addMenu("&Output Recipe")
        executeMenu.addSeparator()
        executeMenu.addAction(QtGui.QAction("Version &Up outputs", self, shortcut= "Ctrl+U", triggered=self.versionUpSelectedOutputFilenames))
        #executeMenu.addAction(QtGui.QAction("&Test Menu Item", self, shortcut= "Ctrl+T", triggered=self.testMenuItem))
        executeMenu.addSeparator()
        executeMenu.addAction(QtGui.QAction("&Reload plugins", self, shortcut= "Ctrl+0", triggered=self.reloadPlugins))
        windowMenu = self.menuBar().addMenu("&Window")
        windowMenu.addAction(self.propDock.toggleViewAction())
        windowMenu.addAction(self.variableDock.toggleViewAction())

        # Application settings
        self.settings = QtCore.QSettings('vcl', 'depends', self)
        self.restoreSettings()

        # Setup the variables, load the plugins, and auto-generate the read dag nodes
        self.setupStartupVariables()
        depends_node.loadChildNodesFromPaths(depends_variables.value('NODE_PATH').split(':'))

        # Generate the Create menu.  Must be done after plugins are loaded.
        menuActions = self.createCreateMenuActions()
        for action in menuActions:
            cat = None
            for eAct in createMenu.actions():
                if eAct.menu():
                    if eAct.text() == action.category:
                        cat = eAct.menu()
                        break

            if not cat:
                cat = QtGui.QMenu(createMenu)
                cat.setTitle(action.category)
                createMenu.addMenu(cat)

            cat.addAction(action)


        # Load the starting filename or create a new DAG
        self.workingFilename = startFile
        self.dag = depends_dag.DAG()
        self.graphicsScene.setDag(self.dag)
        if not self.open(self.workingFilename):
            self.setWindowTitle("Depends")
        self.undoStack.setClean()

        # This is a small workaround to insure the properties dialog doesn't 
        # try to redraw twice when two nodes are rapidly selected 
        # (within a frame of eachother).  There's a good chance the way I
        # construct a property dialog is strange, but a twice-at-once redraw
        # was making the entire UI destroy itself and spawn a temporary child
        # window that had the same name as the program 'binary'.
        self.selectionTimer = QtCore.QTimer(self)
        self.selectionTimer.setInterval(0)
        self.selectionTimer.timeout.connect(self.selectionRefresh)

        # Hook up some signals
        self.graphicsViewWidget.createNode.connect(self.createNode)
        self.graphicsScene.selectionChanged.connect(self.selectionChanged)
        self.graphicsScene.nodesDisconnected.connect(self.nodesDisconnected)
        self.graphicsScene.nodesConnected.connect(self.nodesConnected)
        self.propWidget.attrChanged.connect(self.propertyEdited)
        self.propWidget.mouseover.connect(self.highlightDagNodes)
        self.variableWidget.addVariable.connect(depends_variables.add)
        self.variableWidget.setVariable.connect(depends_variables.setx)
        self.variableWidget.removeVariable.connect(depends_variables.remove)
        self.undoStack.cleanChanged.connect(self.setWindowTitleClean)


    ###########################################################################
    ## Event overrides
    ###########################################################################
    def closeEvent(self, event):
        """
        Save program settings and ask "are you sure" if there are unsaved changes.
        """
        if not self.undoStack.isClean():
            if self.yesNoDialog("Current workflow is not saved.  Save it before quitting?"):
                if self.workingFilename:
                    self.save(self.workingFilename)
                else:
                    self.saveAs()
        self.saveSettings()
        QtGui.QMainWindow.closeEvent(self, event)


    ###########################################################################
    ## Internal functionality
    ###########################################################################

    def selectedDagNodes(self):
        """
        Return a list of all selected DagNodes in the scene.
        """
        selectedDrawNodes = self.graphicsScene.selectedItems()
        return [sdn.dagNode for sdn in selectedDrawNodes]


    def clearSelection(self):
        selectedDrawNodes = self.graphicsScene.selectedItems()
        for dagNode in selectedDrawNodes:
            dagNode.setSelected(False)
        self.selectionChanged()


    def setupStartupVariables(self):
        """
        Each program starts with a set of workflow variables that are defined
        by where the program is executed from and potentially a set of
        environment variables.
        """
        # The current session gets a "binary directory" variable
        depends_variables.add('DEPENDS_DIR')
        depends_variables.setx('DEPENDS_DIR', os.path.dirname(os.path.realpath(__file__)), readOnly=True)

        # ...And a path that points to where the nodes are loaded from
        depends_variables.add('NODE_PATH')
        if not os.environ.get('DEPENDS_NODE_PATH'):
            depends_variables.setx('NODE_PATH', os.path.join(depends_variables.value('DEPENDS_DIR'), 'nodes'), readOnly=True)
        else:
            depends_variables.setx('NODE_PATH', os.environ.get('DEPENDS_NODE_PATH'), readOnly=True)

        
    def clearVariableDictionary(self):
        """
        Clear all variables from the 'global' variable dictionary that aren't 
        "built-in" to the current session.
        """
        for key in depends_variables.names():
            if key == 'DEPENDS_DIR':
                continue
            if key == 'NODE_PATH':
                continue
        

    def saveSettings(self):
        """
        Register the software's general settings with the QSettings object 
        and force a save with sync().
        """
        self.settings.setValue("mainWindowGeometry", self.saveGeometry())
        self.settings.setValue("mainWindowState", self.saveState())
        self.settings.sync()
        
        
    def restoreSettings(self):
        """
        Restore the software's general settings by pulling data out of the 
        current settings object.
        """
        self.restoreGeometry(self.settings.value('mainWindowGeometry'))
        self.restoreState(self.settings.value('mainWindowState'))
        

    ###########################################################################
    ## Complex message handling
    ###########################################################################
    def createNode(self, nodeType, nodeLocation):
        """
        Create a new dag node with a safe name, add it to the dag, and register it with the QGraphicsScene.
        """
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        newDagNode = nodeType()
        nodeName = depends_node.cleanNodeName(newDagNode.typeStr())
        nodeName = self.dag.safeNodeName(nodeName)
        newDagNode.setName(nodeName)
        self.dag.addNode(newDagNode)
        self.graphicsScene.addExistingDagNode(newDagNode, nodeLocation)

        currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene))

        self.clearSelection()
        drawNode = self.graphicsScene.drawNode(newDagNode)
        self.selectNode(drawNode)


    def deleteNodes(self, dagNodesToDelete):
        """
        Delete an existing dag node and its edges, and make sure the QGraphicsScene cleans up as well.
        """
        nodesAffected = list()
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        # Clean up the graphics scene
        # TODO: Should be a signal that tells the scene what to do
        for dagNode in dagNodesToDelete:
            drawNode = self.graphicsScene.drawNode(dagNode)
            drawEdges = drawNode.drawEdges()
            for edge in drawEdges:
                edge.sourceDrawNode().removeDrawEdge(edge)
                edge.destDrawNode().removeDrawEdge(edge)
                self.graphicsScene.removeItem(edge)
            self.graphicsScene.removeItem(drawNode)

        # Remove the nodes from the dag
        for delNode in dagNodesToDelete:
            nodesAffected = nodesAffected + self.dagNodeDisconnected(delNode)
            nodesAffected.remove(delNode)
            self.dag.removeNode(delNode)

        currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene))
        
        # Updates the drawNodes for each of the affected dagNodes
        self.graphicsScene.refreshDrawNodes(nodesAffected)
    
    
    def shakeNodes(self, dagNodesToShake):
        """
        Pull a node out of the dependency chain without deleting it and without 
        losing downstream information.
        """
        nodesAffected = list()
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        for dagNode in dagNodesToShake:
            inNodes = self.dag.nodeConnectionsIn(dagNode)
            outNodes = self.dag.nodeConnectionsOut(dagNode)
            drawNode = self.graphicsScene.drawNode(dagNode)
            
            # Connect all previous dag nodes to all next nodes & add the draw edges
            for inputDagNode in inNodes:
                inputDrawNode = self.graphicsScene.drawNode(inputDagNode)
                for outputDagNode in outNodes:
                    outputDrawNode = self.graphicsScene.drawNode(outputDagNode)
                    self.dag.connectNodes(inputDagNode, outputDagNode)
                    newDrawEdge = self.graphicsScene.addExistingConnection(inputDagNode, outputDagNode)
                    newDrawEdge.horizontalConnectionOffset = self.graphicsScene.drawEdge(drawNode, outputDrawNode).horizontalConnectionOffset
                    newDrawEdge.adjust()
            
            # Disconnect this dag node from everything
            for inputDagNode in inNodes:
                self.dag.disconnectNodes(inputDagNode, dagNode)
            for outputDagNode in outNodes:
                nodesAffected = nodesAffected + self.dagNodeDisconnected(dagNode)
                self.dag.disconnectNodes(dagNode, outputDagNode)

            # Remove all draw edges
            for edge in drawNode.drawEdges():
                edge.sourceDrawNode().removeDrawEdge(edge)
                edge.destDrawNode().removeDrawEdge(edge)
                self.graphicsScene.removeItem(edge)
                
            # Nullify all our inputs
            for input in dagNode.inputs():
                dagNode.setInputValue(input.name, "")

        currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene))

        # A few refreshes
        self.propWidget.refresh()
        self.graphicsScene.refreshDrawNodes(nodesAffected)


    def duplicateNodes(self, dagNodesToDupe):
        """
        Create identical copies of the given dag nodes, but drop their 
        incoming and outgoing connections.
        """
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        
        for dagNode in dagNodesToDupe:
            dupedNode = dagNode.duplicate("_Dupe")
            newLocation = self.graphicsScene.drawNode(dagNode).pos() + QtCore.QPointF(20, 20)
            self.dag.addNode(dupedNode)
            self.graphicsScene.addExistingDagNode(dupedNode, newLocation)
        
        currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene))


    def versionUpOutputFilenames(self, dagNodesToVersionUp):
        """
        Increment the filename version of all output filenames in a given
        list of dag nodes.
        """
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        nodesAffected = list()
        for dagNode in self.selectedDagNodes():
            for output in dagNode.outputs():
                for soName in output.subOutputNames():
                    if not output.value[soName]:
                        continue
                    currentValue = output.value[soName]
                    updatedValue = depends_util.nextFilenameVersion(currentValue)
                    dagNode.setOutputValue(output.name, soName, updatedValue)
                    self.dag.setNodeStale(dagNode, False)
                    nodesAffected = nodesAffected + self.dagNodeOutputChanged(dagNode, dagNode.outputNamed(output.name))

        currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
        self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene))

        # Updates the drawNodes for each of the affected dagNodes
        self.propWidget.refresh()
        self.graphicsScene.refreshDrawNodes(nodesAffected)


    def nodesDisconnected(self, fromDagNode, toDagNode):
        """
        When the user interface disconnects two nodes, tell the in-flight
        dag about it.
        """
        print 'disconnect', fromDagNode, toDagNode
        nodesAffected = list()
        nodesAffected = nodesAffected + self.dagNodeDisconnected(fromDagNode)
        self.dag.disconnectNodes(fromDagNode, toDagNode)

        # A few refreshes
        self.propWidget.refresh()
        self.graphicsScene.refreshDrawNodes(nodesAffected)

    
    def nodesConnected(self, fromDagNode, toDagNode, sourcePort, destPort):
        """
        When the user interface connects two nodes, tell the in-flight dag
        about it.
        """
        print 'connecting nodes', fromDagNode, toDagNode
        print 'ports', sourcePort, destPort
        self.dag.connectNodes(fromDagNode, toDagNode, sourcePort=sourcePort, destPort=destPort )


    def propertyEdited(self, dagNode, propName, newValue, propertyType=None):
        """
        When the user interface edits a property of a node (meaning an attribute,
        input, or output), communicate this information to the in-flight dag
        and nodes, and handle the repercussions.
        """
        somethingChanged = False
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        nodesAffected = list()
        if propName == "Name" and propertyType is depends_node.DagNodeAttribute:
            if newValue != dagNode.name:
                dagNode.setName(newValue)
                nodesAffected = nodesAffected + [dagNode]
                somethingChanged = True
        else:
            if propertyType is depends_node.DagNodeInput:
                if newValue != dagNode.inputValue(propName):
                    dagNode.setInputValue(propName, newValue)
                    nodesAffected = nodesAffected + self.dagNodeInputChanged(dagNode, dagNode.inputNamed(propName))
                    somethingChanged = True
                    self.propWidget.refresh()

            elif propertyType is depends_node.DagNodeOutput:
                bothNames = propName.split('.')
                if newValue != dagNode.outputValue(bothNames[0], bothNames[1]):
                    dagNode.setOutputValue(bothNames[0], bothNames[1], newValue)
                    self.dag.setNodeStale(dagNode, False)
                    nodesAffected = nodesAffected + self.dagNodeOutputChanged(dagNode, dagNode.outputNamed(bothNames[0]))
                    somethingChanged = True
                
            elif propertyType is depends_node.DagNodeAttribute:
                if newValue != dagNode.attributeValue(propName):
                    dagNode.setAttributeValue(propName, newValue)
                    nodesAffected = nodesAffected + [dagNode]
                    somethingChanged = True
                

        # Undos aren't registered when the value doesn't actually change
        if somethingChanged:
            currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
            self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene, self.propWidget))

        # Updates the drawNodes for each of the affected dagNodes
        self.graphicsScene.refreshDrawNodes(nodesAffected)


    def propertyRangeEdited(self, dagNode, propName, newRange, propertyType):
        """
        When the user interface edits the range of a property (attribute, input,
        or output), modify the in-flight dag and nodes and insure everything
        needed changes accordingly.
        """
        registerUndo = False
        preSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())

        # None is a legit value for a range value.  Make sure blanks are Nones.
        if newRange[0] == "":
            newRange = (None, newRange[1])
        if newRange[1] == "":
            newRange = (newRange[0], None)
        
        nodesAffected = list()
        if propertyType is depends_node.DagNodeInput:
            if newRange != dagNode.inputRange(propName, variableSubstitution=False):
                dagNode.setInputRange(propName, newRange)
                nodesAffected = nodesAffected + [dagNode]
                registerUndo = True
                
        elif propertyType is depends_node.DagNodeOutput:
            if newRange != dagNode.outputRange(propName, variableSubstitution=False):
                dagNode.setOutputRange(propName, newRange)
                # Note: Changing the output range does not affect the staleness of the node
                nodesAffected = nodesAffected + [dagNode]
                registerUndo = True
                
        elif propertyType is depends_node.DagNodeAttribute:
            if newRange != dagNode.attributeRange(propName, variableSubstitution=False):
                dagNode.setAttributeRange(propName, newRange)
                nodesAffected = nodesAffected + [dagNode]

        # Undos aren't registered when the value doesn't actually change, 
        if registerUndo:
            currentSnap = self.dag.snapshot(nodeMetaDict=self.graphicsScene.nodeMetaDict(), connectionMetaDict=self.graphicsScene.connectionMetaDict())
            self.undoStack.push(depends_undo_commands.DagAndSceneUndoCommand(preSnap, currentSnap, self.dag, self.graphicsScene, self.propWidget))

        # Updates the drawNodes for each of the affected dagNodes
        self.graphicsScene.refreshDrawNodes(nodesAffected)


    def communicationReceived(self, message):
        """
        This function acts as a switchboard for incoming messages from the
        program's communication module.  It is very rough, but it has served
        its purpose.  More work is needed to make it nice and general.
        """
        print "Dependency graph received: %s" % message
        tokenizedCommand = message.strip().split('<-->')
        if tokenizedCommand[0].strip() == "MODIFY":
            attribute = tokenizedCommand[1].strip()
            nodeName = tokenizedCommand[2].strip()
            filename = tokenizedCommand[3].strip()

            dagNode = self.dag.node(name=nodeName)
            # TODO: Bring back and formalize
            #for key in nodeDOTattributes:
            #   if not key.startswith(attribute):
            #       continue
            #   dagNode.setAttribute(key, list(filename))
            #   print "SUCCESS"
            #   break


    def selectNode(self, dagNode):
        """
        Select a node
        """
        dagNode.setSelected(True)
        self.selectionChanged()
        return dagNode


    def selectionRefresh(self):
        """
        A small workaround for a property dialog refresh issue.  See comments 
        in constructor ("This is a small workaround...") for more details.
        """
        selectedDagNodes = self.selectedDagNodes()
        self.propWidget.rebuild(self.dag, selectedDagNodes)
        self.selectionTimer.stop()


    def selectionChanged(self):
        """
        Fires off an instantaneous timer that rebuilds the scenegraph and 
        property widget based on a change of selection in the SceneWidget.
        Works in conjunction with self.selectionRefresh().
        """
        if self.selectionTimer.isActive():
            return
        self.selectionTimer.start(0)


    def highlightDagNodes(self, dagNodeList):
        """
        Given a list of DagNodes to highlight, derive their drawNodes, and 
        alert the graphics widgets that a highlight might be apropos.
        """
        drawNodes = list()
        if dagNodeList:
            for dagNode in dagNodeList:
                drawNodes.append(self.graphicsScene.drawNode(dagNode))
        self.graphicsScene.setHighlightNodes(drawNodes)
    

    def setWindowTitleClean(self, isClean):
        """
        Adjust the window title's clean state based on an incoming parameter.
        """
        if isClean:
            self.setWindowTitle("%s" % self.windowTitle()[:-1])
        else:
            self.setWindowTitle("%s*" % self.windowTitle())
    

    ###########################################################################
    ## DAG management
    ###########################################################################
    def dagNodeDisconnected(self, fromDagNode):
        """
        When a node is disconnected, all nodes after it lose their inputs to
        nodes that come before it. This function is to be called before the DAG 
        removes any connections or deletes any nodes from its collection.
        """
        nodesAffected = [fromDagNode]

        allNodesAfter = self.dag.allNodesAfter(fromDagNode)
        allNodesBefore = self.dag.allNodesBefore(fromDagNode) + [fromDagNode]
        for afterNode in allNodesAfter:
            for input in afterNode.inputs():
                inputNode = self.dag.nodeInputComesFromNode(afterNode, input)[0]
                if inputNode in allNodesBefore:
                    afterNode.setInputValue(input.name, "")
                    afterNode.setInputRange(input.name, None)
                    nodesAffected.append(afterNode)
                    nodesAffected = nodesAffected + self.dagNodeInputChanged(afterNode, input)

        return nodesAffected


    def dagNodeInputChanged(self, dagNode, input):
        """
        When a node's input is changed, its range should be set to the same as
        the output connected to it.  Also, if there is an output that is affected
        by this input, its range should be changed as well.
        """
        nodesAffected = list()
        
        # Gather the output that corresponds to the changed input
        affectedOutput = dagNode.outputAffectedByInput(input)

        # Notify the system that there has been a changed output - this covers the case of the output range
        # change (loop just above this one) and the input type being changed, and thus cascading down.
        if affectedOutput:
            nodesAffected = nodesAffected + self.dagNodeOutputChanged(dagNode, affectedOutput)
            
        return nodesAffected
    
    
    def dagNodeOutputChanged(self, dagNode, output):
        """
        When a node output's type or range is changed, inputs that connect to it 
        may need to be adjusted.  Incompatible types must be disconnected and 
        ranges should be clamped.
        """
        nodesAffected = list()

        # Input types downstream may no longer be able to connect to this node.  Handle recursively.
        allAffectedNodes = self.dag.allNodesDependingOnNode(dagNode, recursion=False)
        for affectedNode in allAffectedNodes:
            for input in affectedNode.inputs():
                nodeComingInOutputType = self.dag.nodeOutputType(*self.dag.nodeInputComesFromNode(affectedNode, input))
                nodesAffected = nodesAffected + self.dagNodeInputChanged(affectedNode, input)
                if nodeComingInOutputType not in input.allPossibleInputTypes():
                    affectedNode.setInputValue(input.name, "")
                    affectedNode.setInputRange(input.name, None)
                    nodesAffected.append(affectedNode)
        
        # The range of directly-connected inputs may need to be adjusted
        directlyAffectedNodes = self.dag.allNodesDependingOnNode(dagNode, recursion=False)
        for affectedNode in directlyAffectedNodes:
            for input in affectedNode.inputs():
                (incomingNode, incomingOutput) = self.dag.nodeInputComesFromNode(affectedNode, input)
                if input.seqRange != incomingOutput.getSeqRange():
                    input.seqRange = incomingOutput.getSeqRange()
                    nodesAffected.append(affectedNode)
                    
        # Data that used to exist may no longer exist.  Therefore all directly affected nodes should refresh.
        nodesAffected = nodesAffected + [dagNode] + directlyAffectedNodes
                
        return nodesAffected


    def dagNodeVariablesUsed(self, dagNode):
        """
        Returns a tuple containing a list of all the single-dollar and a list 
        of all the double-dollar variables used in the current DAG.
        """
        singleDollarList = list()
        doubleDollarList = list()
        for attribute in dagNode.attributes():
            vps = depends_variables.present(dagNode.attributeValue(attribute.name, variableSubstitution=False))
            vss = (list(), list())
            vss2 = (list(), list())
            if dagNode.attributeRange(attribute.name, variableSubstitution=False):
                vss = depends_variables.present(dagNode.attributeRange(attribute.name, variableSubstitution=False)[0])
                vss2 = depends_variables.present(dagNode.attributeRange(attribute.name, variableSubstitution=False)[1])
            singleDollarList += vps[0] + vss[0] + vss2[0]
            doubleDollarList += vps[1] + vss[1] + vss2[1]
        return (list(set(singleDollarList)), list(set(doubleDollarList)))


        

    def dagNodesSanityCheck(self, dagNodes):
        """
        Runs a series of sanity tests on the given dag nodes to make sure they
        are fit to be executed in their current state.
        """
        #
        # Full DAG validation
        #
        # Insure all $ variables that are used, exist
        for dagNode in dagNodes:
            (singleDollarVariables, doubleDollarVariables) = self.dagNodeVariablesUsed(dagNode)
            for sdVariable in singleDollarVariables:
                if sdVariable not in depends_variables.names():
                    raise RuntimeError("Depends variable $%s used in node '%s' does not exist in current environment." % (sdVariable, dagNode.name))

        # Insure all $$ variables that are used, are present in the current environment
        for dagNode in dagNodes:
            (singleDollarVariables, doubleDollarVariables) = self.dagNodeVariablesUsed(dagNode)
            for ddVariable in doubleDollarVariables:
                if ddVariable not in os.environ:
                    raise RuntimeError("Environment variable $%s used in node '%s' does not exist in current environment." % (ddVariable, dagNode.name))
        
        #
        # Individual node validation
        #
        for dagNode in dagNodes:
            # Insure all the inputs are connected
            if not self.dag.nodeAllInputsConnected(dagNode):
                raise RuntimeError("Node '%s' is missing a required input." % (dagNode.name))


            # Insure the validation function passes for each node.
            try:
                dagNode.validate()
            except Exception, err:
                raise RuntimeError("Dag node '%s' did not pass its validation test with the error:\n%s" % (dagNode.name, err))
        


        # Insure no node is in two groups at once
        for dagNode in dagNodes:
            if self.dag.nodeGroupCount(dagNode) > 1:
                raise RuntimeError("Node '%s' is present in multiple groups." % (dagNode.name))


    def dagExecuteNode(self, dagNode, destFileOrDir, executeImmediately=False):
        """
        Generate an execution script using a output recipe for the given node.
        Takes a path for where to write the execution script, and offers the 
        ability to evaluate the script immediately.
        """

        print 'executing dag nodes'.center(120, '#')

        # get the list of nodes to execute
        orderedDependencies = self.dag.buildExecutionList(dagNode)

        # include ourselves at the end
        orderedDependencies.append(dagNode)
        print orderedDependencies


        # try:
        #     self.dagNodesSanityCheck(orderedDependencies)
        # except Exception, err:
        #     print err
        #     print "Aborting Dag execution."
        #     return
        
        executionList = list()
        for dagNode in orderedDependencies:
            print 'executing ', dagNode


            # Command execution

            nodesBefore = self.dag.nodeConnectionsByPort(dagNode)
            dagNode.setPortValues(nodesBefore)
            commandList = dagNode.executePython()
            executionList.append((dagNode.name, dagNode.outVal))

        print 'this is what i executed:'
        print executionList


    ###########################################################################
    ## Menu operations
    ###########################################################################
    def open(self, filename):
        """
        Loads a snapshot, in the form of a json, file off disk and applies the
        values it pulls to the currently active dependency graph.  Cleans up
        the UI accordingly.
        """
        if not os.path.exists(filename):
            return False
        
        # Load the snapshot off disk
        with open(filename, 'rb') as fp:
            snapshot = json.loads(fp.read())
            
        # Apply the data to the in-flight Dag
        self.dag.restoreSnapshot(snapshot["DAG"])

        # Initialize the objects inside the graphWidget & restore the scene
        self.graphicsScene.restoreSnapshot(snapshot["DAG"])


        # Variable substitutions
        self.clearVariableDictionary()
        for v in snapshot["DAG"]["VARIABLE_SUBSTITIONS"]:
            depends_variables.variableSubstitutions[v["NAME"]] = (v["VALUE"], False)

        # The current session gets a variable representing the location of the current workflow
        if 'WORKFLOW_DIR' not in depends_variables.names():
            depends_variables.add('WORKFLOW_DIR')
        depends_variables.setx('WORKFLOW_DIR', os.path.dirname(filename), readOnly=True)

        # Additional meta-data loading
        if "RELOAD_PLUGINS_FILENAME_TEMP" in snapshot:
            filename = snapshot["RELOAD_PLUGINS_FILENAME_TEMP"]

        # UI tidies
        self.undoStack.clear()
        self.undoStack.setClean()
        self.workingFilename = filename
        self.setWindowTitle("Depends (%s)" % self.workingFilename)
        self.variableWidget.rebuild(depends_variables.variableSubstitutions)
        return True

        
    def openDialog(self):
        """
        Pops open a file dialog, recovers a filename from it, and calls self.open()
        on the results.
        """
        # TODO: This code is used twice almost identically.  Can it go into yesNoDialog?
        if not self.undoStack.isClean():
            if self.yesNoDialog("Current workflow is not saved.  Save it before opening?"):
                if self.workingFilename:
                    self.save(self.workingFilename)
                else:
                    self.saveAs()
        filename, throwaway = QtGui.QFileDialog.getOpenFileName(self, caption='Open Workflow', filter="Workflow files (*.json)")
        if not filename:
            return
        self.open(filename)
        
    
    def save(self, filename, additionalFileDictionary=None):
        """
        Functionality for writing snapshots of the software's running state
        to a json file.  Modifies the UI accordingly.
        """
        if not filename:
            return

        # Create a nested meta dict for saving node locations
        nodeMetaDict = self.graphicsScene.nodeMetaDict()

        # Create a nested meta dict for saving connection offsets
        connectionMetaDict = self.graphicsScene.connectionMetaDict()

        # Store all but read-only variables to the state
        varDicts = depends_variables.changeableList()

        # TODO: A generic way to pass additional dicts into the snapshot function might be good.
        #       The parameter list is getting long and specific!  (also, variableList->variableDict)
        #       Or maybe we should just merge it all right here?
        # Concoct a full snapshot from the current DAG and additional information fed into the function
        snapshot = self.dag.snapshot(nodeMetaDict=nodeMetaDict, connectionMetaDict=connectionMetaDict, variableMetaList=varDicts)
        fullSnap = {"DAG":snapshot}
        if additionalFileDictionary:
            fullSnap = dict({"DAG":snapshot}.items() + additionalFileDictionary.items())

        # Serialize to disk
        fp = open(filename, 'wb')
        fp.write(json.dumps(fullSnap, sort_keys=True, indent=4))
        fp.close()
        
        # UI tidies
        self.undoStack.setClean()
        self.workingFilename = filename
        self.setWindowTitle("Depends (%s)" % self.workingFilename)
        
        
    def saveAs(self):
        """
        Save the DAG to a filename pulled out of a file dialog.
        """
        currentDir = os.path.dirname(self.workingFilename)
        filename, throwaway = QtGui.QFileDialog.getSaveFileName(self, caption='Save Workflow As', filter="Workflow files (*.json)", dir=currentDir)
        if not filename:
            return
        self.save(filename)


    def saveVersionUp(self):
        """
        Save the next version of the current file.
        """
        nextVersionFilename = depends_util.nextFilenameVersion(self.workingFilename)
        self.save(nextVersionFilename)
        

    def yesNoDialog(self, text):
        """
        A simple yes/no dialog box.
        """
        reply = QtGui.QMessageBox.question(self, "Notice", text, QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if (reply == QtGui.QMessageBox.Yes):
            return True
        return False


    def reloadPlugins(self):
        """
        This menu item reloads all the plugin files off disk by restarting 
        depends in-place.  If the current workflow has been modified, save 
        a temporary copy and reload it on startup.
        """
        self.saveSettings()
        args = QtGui.qApp.arguments()
        if not self.undoStack.isClean():
            (osJunk, filename) = tempfile.mkstemp(prefix="dependsreload_", suffix=".json")
    
            metaDict = {"RELOAD_PLUGINS_FILENAME_TEMP":self.workingFilename}
            self.save(filename, metaDict)
    
            filenameIndexMinusOne = args.index('-workflow')
            args[filenameIndexMinusOne+1] = filename
        depends_util.restartProgram(args)
        
    
    def executeSelected(self, executeImmediately=False):
        """
        Execute the selected node using self.dagExecuteNode().
        """
        selectedDagNodes = self.selectedDagNodes()
        if len(selectedDagNodes) > 1 or not selectedDagNodes:
            # TODO: Status bar
            return
        self.dagExecuteNode(selectedDagNodes[0], '/tmp', executeImmediately)


    def deleteSelectedNodes(self):
        """
        Delete selected nodes using self.deleteNodes().
        """
        dagNodesToDelete = self.selectedDagNodes()
        if not dagNodesToDelete:
            return
        self.deleteNodes(dagNodesToDelete)


    def shakeSelectedNodes(self):
        """
        "Shake" selected nodes from the dag using self.shakeNodes().
        """
        dagNodesToShake = self.selectedDagNodes()
        if not dagNodesToShake:
            return
        self.shakeNodes(dagNodesToShake)


    def duplicateSelectedNodes(self):
        """
        Duplicate selected nodes using self.duplicateNodes().
        """
        dagNodesToDupe = self.selectedDagNodes()
        if not dagNodesToDupe:
            return
        self.duplicateNodes(dagNodesToDupe)


    def groupSelectedNodes(self):
        """
        Group selected nodes into an execution collection.
        """
        selDagNodes = self.selectedDagNodes()
        for dagNode in selDagNodes:
            if self.dag.nodeGroupCount(dagNode) > 0:
                raise RuntimeError("Nodes cannot currently be in more than one group.")
        groupName = depends_util.generateUniqueNameSimiarToExisting('group', self.dag.nodeGroupDict.keys())
        self.dag.addNodeGroup(groupName, selDagNodes)
        self.graphicsScene.addExistingGroupBox(groupName, selDagNodes)


    def ungroupSelectedNodes(self):
        """
        If all selected nodes are in a group together, remove their node group
        from the in-flight dependency graph.
        """
        selDagNodes = self.selectedDagNodes()
        groupNameInDag = self.dag.nodeGroupName(selDagNodes)
        if not groupNameInDag:
            return
        self.graphicsScene.removeExistingGroupBox(groupNameInDag)
        self.dag.removeNodeGroup(nodeListToRemove=selDagNodes)
        

    def versionUpSelectedOutputFilenames(self):
        """
        Version up the output filenames for each of the selected nodes using
        self.versionUpOutputFilenames().
        """
        dagNodesToVersionUp = self.selectedDagNodes()
        if not dagNodesToVersionUp:
            return
        self.versionUpOutputFilenames(dagNodesToVersionUp)


    def createNodeFromMenuStub(self):
        """
        Create a new node from scratch.  The stub funciton is theoretically 
        temporary until I can figure out how to make a deep copy of a type.
        """
        nodeType = self.sender().data()[0]
        # No nodelocation is supplied for actions that come from the menu, so compute now and apply.
        nodeLocation = self.sender().data()[1]
        if nodeLocation is None:
            nodeLocation = self.graphicsViewWidget.centerCoordinates()
        self.createNode(nodeType, nodeLocation)


    def createCreateMenuActions(self):
        """
        Creates all the menu commands that create nodes from all the dag node
        types present in the current session.
        """
        actionList = list()
        for tipe in depends_node.dagNodeTypes():
            menuAction = QtGui.QAction(tipe().typeStr(), self, triggered=self.createNodeFromMenuStub)
            menuAction.setData((tipe, None))
            menuAction.category = tipe.category
            actionList.append(menuAction)
        return actionList
    


