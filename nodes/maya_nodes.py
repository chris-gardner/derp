
import depends_node



class DagNodeMayaLocator(depends_node.DagNode):
    category = 'Maya'

    def _defineAttributes(self):
        """
        """
        return [
              depends_node.DagNodeAttribute('name', "someLocator_1", docString="Name of locator")
        ]

    def executePython(self, nodesBefore):
        import rpyc

        locName = self.attributeValue('name')


        conn = rpyc.classic.connect("127.0.0.1", port=8003)
        cmds = conn.modules.maya.cmds
        utils = conn.modules.maya.utils

        loc = cmds.spaceLocator(name=locName)
        print loc
        self.outVal = loc


class DagNodeMayaSphere(depends_node.DagNode):
    category = 'Maya'

    def _defineAttributes(self):
        """
        """
        return [
              depends_node.DagNodeAttribute('radius', "5.0", docString="Radius"),
              depends_node.DagNodeAttribute('name', "someSphere", docString="Name of locator")
        ]

    def executePython(self, nodesBefore):
        import rpyc

        radius = float(self.attributeValue('radius'))
        sphereName = self.attributeValue('name')

        conn = rpyc.classic.connect("127.0.0.1", port=8003)
        cmds = conn.modules.maya.cmds
        utils = conn.modules.maya.utils

        def doSphere(radius, sphereName):
            return cmds.polySphere(radius=radius, name=sphereName, constructionHistory=False)

        ret = utils.executeInMainThreadWithResult(doSphere, radius, sphereName)

        print ret
        self.outVal = ret





class DagNodeTestNode(depends_node.DagNode):
    category = 'Maya'

    def _defineAttributes(self):
        """
        """
        return [
        ]

    def executePython(self, nodesBefore):
        import rpyc

        conn = rpyc.classic.connect("127.0.0.1", port=8003)
        cmds = conn.modules.maya.cmds
        core = conn.modules.fsmpipe.maya.renderLayers.core
        utils = conn.modules.maya.utils

        def doStuff():
            core.setup()
            core.createLayer("baseLayer")
            core.createOverride("sgOverride", "baseLayer", "|hdri", override="None", overrideValue="_NoneSG", memberRules="")
            core.createOverride("sgOverride", "baseLayer", "|dome", override="None", overrideValue="surfaceShader1SG", memberRules="")
            core.createLayer("matte_A")
            core.createOverride("sgOverride", "matte_A", "", override="None", overrideValue="GreenSG", memberRules="[+tag=tree_A][+tag=tree_B][+tag=leaves_A][+tag=leaves_B][+tag=leaves_C][+tag=trunks]")
            core.createOverride("sgOverride", "matte_A", "", override="None", overrideValue="surfaceShader2SG", memberRules="[+tag=ELN]")
            core.createOverride("sgOverride", "matte_A", "", override="None", overrideValue="BlackSG", memberRules="[+tag=ENV][-tag=road][-tag=tree_A][-tag=tree_B][-tag=leaves][-tag=leavesA][-tag=leavesB][-tag=leavesC][+tag=elantra]")
            core.createOverride("sgOverride", "matte_A", "", override="None", overrideValue="BlueSG", memberRules="[+tag=road]")
            core.createOverride("valueOverride", "matte_A", "", override="visibility", overrideValue=False, memberRules="[+tag=dome]")

        ret = utils.executeInMainThreadWithResult(doStuff)

        print ret
        self.outVal = ret

