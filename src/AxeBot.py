import basic
import time
import Constants

class AxeBot(basic.BasicBot):
    def __init__(self, agent_host, name):
        super().__init__(agent_host, name)

    def step(self, command):
        if command[3] >= .5:
            self.agent_host.sendCommand('attack 1')
            self.attacks += 1
        else:
            self.agent_host.sendCommand('attack 0')
        if command[4] >= .5:
            self.agent_host.sendCommand('use 1')
        else:
            self.agent_host.sendCommand('use 0')
        return super().step(command)