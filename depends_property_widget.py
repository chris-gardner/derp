#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

from PySide import QtCore, QtGui

import depends_node
import depends_data_packet
import depends_file_dialog


"""
A QT graphics widget that displays the properties (attributes, outputs, and
inputs) of a given node.  Inputs can be modified with drag'n'drop, attributes
can be modified with keyboard input, and outputs are the same.
"""


###############################################################################
###############################################################################
class GeneralEdit(QtGui.QWidget):
    """
    An edit widget that displays a text field, two fields for the file sequence
    range, and an expansion button to hide the range fields by default.  It 
    allows tooltips to be added, modifiable bits to be set, file dialog buttons
    to be added, tighter formatting, and custom file dialogs.
    """

    # Signals
    valueChanged = QtCore.Signal(str, object, type)

    def __init__(self, label="Unknown", enabled=True, toolTip=None,
                 parent=None):
        """
        """
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.enabled = enabled
        self.toolTip = toolTip
        self.draw()


    def draw(self):
        # The upper layout holds the label, the value, and the "expand" button
        upperLayout = QtGui.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)

        self.label = QtGui.QLabel(self.label, self)
        self.label.setMinimumWidth(150)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)

        self.lineEdit = QtGui.QLineEdit(self)
        self.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)

        self.setLayout(upperLayout)

        # Chain signals out with property name and value
        self.lineEdit.editingFinished.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.text(), depends_node.DagNodeAttribute))


    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.lineEdit.setText(str(value))
        self.lineEdit.editingFinished.emit()  # TODO: Is this necessary?  Might be legacy.


###############################################################################
###############################################################################
class StringAttrEdit(GeneralEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """

    def __init__(self, attribute=None, dagNode=None, dag=None, parent=None):
        """
        """
        GeneralEdit.__init__(self,
                             label=attribute.name,
                             toolTip=attribute.docString,
                             parent=parent)
        self.dag = dag
        self.dagNode = dagNode
        self.attribute = attribute


class FloatAttrEdit(StringAttrEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """

    def __init__(self, attribute=None, dagNode=None, dag=None, parent=None):
        """
        """
        GeneralEdit.__init__(self,
                             label=attribute.name,
                             toolTip=attribute.docString,
                             parent=parent)
        self.dag = dag
        self.dagNode = dagNode
        self.attribute = attribute

    def draw(self):
        upperLayout = QtGui.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)

        self.label = QtGui.QLabel(self.label, self)
        self.label.setMinimumWidth(150)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)

        self.lineEdit = QtGui.QDoubleSpinBox(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)

        self.setLayout(upperLayout)

        # Chain signals out with property name and value
        self.lineEdit.editingFinished.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.value(), depends_node.DagNodeAttribute))

    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        print value
        self.value = value
        self.lineEdit.setValue(float(value))
        self.lineEdit.editingFinished.emit()  # TODO: Is this necessary?  Might be legacy.



class BoolAttrEdit(StringAttrEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """

    def __init__(self, attribute=None, dagNode=None, dag=None, parent=None):
        """
        """
        GeneralEdit.__init__(self,
                             label=attribute.name,
                             toolTip=attribute.docString,
                             parent=parent)
        self.dag = dag
        self.dagNode = dagNode
        self.attribute = attribute

    def draw(self):
        upperLayout = QtGui.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 05)
        # upperLayout.setSpacing(0)

        self.label = QtGui.QLabel(self.label, self)
        self.label.setMinimumWidth(150)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)

        self.lineEdit = QtGui.QCheckBox(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)

        self.setLayout(upperLayout)

        # Chain signals out with property name and value
        self.lineEdit.stateChanged.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.isChecked(), depends_node.DagNodeAttribute))

    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        print value
        self.value = value
        self.lineEdit.setChecked(bool(value))
        self.lineEdit.stateChanged.emit(bool(value))  # TODO: Is this necessary?  Might be legacy.

###############################################################################
###############################################################################
class PropWidget(QtGui.QWidget):
    """
    The full graphics view containing general edits for the object name and
    type, and input, attribute, and output edits for all the node's properties.
    """

    # Signals
    attrChanged = QtCore.Signal(depends_node.DagNode, str, object, type)

    def __init__(self, parent=None):
        """
        """
        QtGui.QWidget.__init__(self, parent)
        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self.scrollArea = QtGui.QScrollArea()

        self.mainLayout.addWidget(self.scrollArea)
        self.foo = QtGui.QWidget(self)
        self.scrollAreaLayout = QtGui.QVBoxLayout(self.foo)
        self.scrollAreaLayout.setContentsMargins(2, 2, 2, 2)
        self.scrollAreaLayout.setSpacing(0)

        self.scrollAreaLayout.setAlignment(QtCore.Qt.AlignTop)
        self.foo.setLayout(self.scrollAreaLayout)
        self.scrollArea.setWidget(self.foo)
        self.setLayout(self.mainLayout)
        self.scrollArea.setWidgetResizable(True)

        self.setMinimumWidth(400)
        self.setMinimumHeight(400)

        self.dagNode = None
        self.resultField = None


    def rebuild(self, dag, dagNodes):
        """
        Completely reconstruct the entire widget from a dag and a list of
        nodes.
        """
        # Clear out all existing widgets
        for child in self.foo.children():
            if type(child) is not type(QtGui.QVBoxLayout()):
                self.scrollAreaLayout.removeWidget(child)
                child.setParent(None)
                child.deleteLater()

        # We only allow one node to be selected so far
        if not dagNodes or len(dagNodes) > 1:
            return

        # Helpers
        self.dagNode = dagNodes[0]
        attrChangedLambda = lambda propName, newValue, type, func=self.attrChanged.emit: func(self.dagNode, propName,
                                                                                              newValue, type)

        # Populate the UI with name and type
        nameWidget = GeneralEdit("Name", parent=self)
        nameWidget.setValue(self.dagNode.name)
        nameWidget.valueChanged.connect(attrChangedLambda)
        self.scrollAreaLayout.addWidget(nameWidget)

        attributeGroup = QtGui.QTabWidget()
        attributeGroup.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        tabWidget = QtGui.QWidget()
        attributeTab= attributeGroup.addTab(tabWidget, self.dagNode.typeStr())
        attributeLayout = QtGui.QVBoxLayout(tabWidget)
        attributeLayout.setContentsMargins(2, 2, 2, 2)
        attributeLayout.setSpacing(2)

       # Add the attributes (don't show any attributes that begin with input/output keywords)
        if self.dagNode.attributes():

            for attribute in self.dagNode.attributes():

                if attribute.dataType in ['float', 'int']:
                    newThing = FloatAttrEdit(attribute=attribute, dagNode=self.dagNode, dag=dag, parent=attributeGroup)
                elif attribute.dataType in ['bool']:
                    newThing = BoolAttrEdit(attribute=attribute, dagNode=self.dagNode, dag=dag, parent=attributeGroup)

                else:
                    newThing = StringAttrEdit(attribute=attribute, dagNode=self.dagNode, dag=dag, parent=attributeGroup)

                newThing.setValue(self.dagNode.attributeValue(attribute.name, variableSubstitution=False))

                attributeLayout.addWidget(newThing)
                newThing.valueChanged.connect(attrChangedLambda)
        else:
            noAttrLabel = QtGui.QLabel()
            noAttrLabel.setText('No attributes')
            attributeLayout.addWidget(noAttrLabel)

       # attributeTab.setLayout(attributeLayout)
        self.scrollAreaLayout.addWidget(attributeGroup)

        self.resultField = GeneralEdit("Result",
                                       enabled=False,
                                       toolTip='Result of this nodes last run',
                                       parent=self)
        self.resultField.setValue(self.dagNode.outVal)
        self.scrollAreaLayout.addWidget(self.resultField)

        if type(self.dagNode).__name__ == 'DagNodeExecute':
            executeBtn = QtGui.QPushButton(self)
            executeBtn.setText('Execute')
            executeBtn.clicked.connect(self.executeBtnClicked)
            self.scrollAreaLayout.addWidget(executeBtn)


    def executeBtnClicked(self, *args):
        print 'executing:', self.dagNode
        mainWin = self.parent().parent()
        mainWin.dagExecuteNode(self.dagNode)
        print 'refreshing'
        self.refresh()


    def refresh(self):
        """
        Refresh the values of all the input, output, and attribute fields
        without a full reconstruction of the widget.
        """
        groupBoxes = self.findChildren(QtGui.QGroupBox)
        inputBox = None
        attributeBox = None
        outputBox = None
        for gb in groupBoxes:
            title = gb.title()
            if title == "Inputs":
                inputBox = gb
            elif title == "Attributes":
                attributeBox = gb
            elif title == "Outputs":
                outputBox = gb

        if attributeBox:
            attributeEdits = attributeBox.findChildren(StringAttrEdit)
            for attrEdit in attributeEdits:
                attrEdit.blockSignals(True)
                attributeName = attrEdit.label.text()
                attrEdit.setValue(self.dagNode.attributeValue(attributeName, variableSubstitution=False))
                attrEdit.blockSignals(False)

        if self.resultField:
            self.resultField.blockSignals(True)
            self.resultField.setValue(self.dagNode.outVal)
            self.resultField.blockSignals(False)


