__author__ = 'chris.gardner'

import os, os.path
import sys

sys.path.append('//fsm.int/fsm/library/assets/pipeline/python/')

import scopeApi as scopeApi
from fsmpipe.common import pathManager
from fsmpipe.common import pathTokens
from fsmpipe.common import fileUtils


import depends_node
import depends_data_packet
from depends_node import DagNodeInput, DagNodeOutput



class DagNodeScopeGetLatestFile(depends_node.DagNode):
    category = 'Scope'

    def _defineAttributes(self):
        return [depends_node.DagNodeAttribute('projectid', "0000", docString='Scope Project Id')]

    def _defineInputs(self):
        return []

    def _defineOutputs(self):
        return [DagNodeOutput('output1', 'string', None)]

    def executePython(self):
        project_id = int(self.attributeValue('projectid'))

        ret = []

        proj = scopeApi.getObjectsById(modelName='project', idList=[project_id])
        if proj:
            print proj
            sequences = proj.getSequences()
            if sequences:
                for seq in sequences:
                    print seq
                    for shot in seq.getShots():
                        print shot
                        shotPath = shot.getAttr('path')
                        mayaDir = fileUtils.unixSlashes(os.path.join(shotPath, 'setups', 'maya', 'scenes', 'lit'))
                        if os.path.isdir(mayaDir):
                            print mayaDir
                            context = pathManager.getContextFromPath(shotPath)
                            foo = pathTokens.pathToken()
                            foo.values = context
                            baseName = foo.buildFromTokens('[seq][shot]_lit_v001xx_wip.ma')


                            pathToBaseFile = fileUtils.unixSlashes(os.path.join(mayaDir, baseName))
                            lastestFile = fileUtils.findLatestFile(pathToBaseFile)
                            if lastestFile:
                                print baseName
                                print lastestFile
                                pathTolastestFile = fileUtils.unixSlashes(os.path.join(mayaDir, lastestFile))
                                ret.append(pathTolastestFile)
        self.outVal = ret
