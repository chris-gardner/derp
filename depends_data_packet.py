#
# Depends
# Copyright (C) 2014 by Andrew Gardner & Jonas Unger.  All rights reserved.
# BSD license (LICENSE.txt for details).
#

import os
import re
import uuid

import depends_node
import depends_util


"""
A data packet is the absolute minimum amount of information needed to represent
a knowable-thing on disk.  Each datapacket can represent a single item or a
sequence of items.

Only file information is transferred in a DataPacket, and only file information
should ever be transferred.  Other values that should be shared between nodes
should happen through the variable substitution mechanisms.
"""


###############################################################################
## Utility
###############################################################################
def filenameDictForDataPacketType(dataPacketType):
    """
    Return a dict of fileDescriptors for a given DataPacket type.
    """
    foo = dataPacketType(None, None)
    return foo.filenames


def scenegraphLocationString(dataPacket):
    """
    Given a datapacket, return a string representing its location in the 
    scenegraph. (::UUID:OUTPUT)
    """
    return "::"+str(dataPacket.sourceNode.uuid)+":"+dataPacket.sourceOutputName


def shorthandScenegraphLocationString(dataPacket):
    """
    Given a datapacket, return a "human-readable" string representing its name
    in the scenegraph.  (::NAME:OUTPUT)
    """
    return "::"+dataPacket.sourceNode.name+":"+dataPacket.sourceOutputName


def uuidFromScenegraphLocationString(string):
    """
    Returns a UUID object for a given scenegraph location string.
    """
    if string == "":
        return None
    if not string.startswith("::"):
        return None
    uuidString = string.split(":")[2]
    return uuid.UUID(uuidString)


def nodeAndOutputFromScenegraphLocationString(string, dag):
    """
    Returns a tuple containing the node defined in a location string and its 
    corresponding Output.
    """
    try:
        outputNodeUUID = uuidFromScenegraphLocationString(string)
        outputNode = dag.node(nUUID=outputNodeUUID)
        outputNodeOutputName = string.split(":")[3]
        return (outputNode, outputNode.outputNamed(outputNodeOutputName))
    except:
        return(None, None)
    

# TODO: A function to get the type name without needing to create the class?


