import basic
import Constants

class CrossbowBot(basic.BasicBot):
    def __init__(self, agent_host, name):
        super().__init__(agent_host, name)

    def reset(self):
        self.obs = super().reset()
        self.agent_host.sendCommand('chat /enchant ' + self.name + ' infinity 1')
        return self.obs