import basic
import json
import time


class BowBot(basic.BasicBot):
    def __init__(self, agent_host, name):
        super().__init__(agent_host, name)
        self.arrows_shot = 0

    def reset(self):
        self.obs = super().reset()
        self.arrows_shot = 0
        self.agent_host.sendCommand('chat /enchant ' + self.name + ' infinity 1')
        return self.obs

    def step(self, command):
        if command[4] >= .5:
                self.agent_host.sendCommand('attack 1')
        else:
                self.agent_host.sendCommand('attack 0')
        if command[5] >= .5:
            self.agent_host.sendCommand('use 1')
            time.sleep(1.1)
            self.arrows_shot += 1
        else:
            self.agent_host.sendCommand('use 0')