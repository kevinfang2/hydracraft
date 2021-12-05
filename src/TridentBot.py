import basic
import time

class TridentBot(basic.BasicBot):
    def __init__(self, agent_host, name):
        super().__init__(agent_host, name)
        self.tridents_thrown = 0

    def step(self, command):
        if command[4] >= .5:
                self.agent_host.sendCommand('attack 1')
        else:
                self.agent_host.sendCommand('attack 0')
        if command[5] >= .5:
            self.agent_host.sendCommand('use 1')
            time.sleep(1.1)
            self.tridents_thrown += 1
        else:
            self.agent_host.sendCommand('use 0')
        super().step(command)