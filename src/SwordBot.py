import basic
import json

class SwordBot(basic.BasicBot):
    def __init__(self, agent_host, name):
        super().__init__(agent_host, name)

    def step(self, command):
        if command[2] >= .5:
                self.agent_host.sendCommand('attack 1')
        else:
                self.agent_host.sendCommand('attack 0')
        super().step(command)