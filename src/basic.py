from builtins import range
from past.utils import old_div
import json
import sys
import time
from collections import namedtuple
from operator import add

import arena


class BasicBot:
    """BasicBot will be given an AgentHost in its run method and just track down & attack various enemies"""
    def __init__(self):
        return

    def step(self, agent_host):
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.number_of_observations_since_last_state > 0:
            msg = world_state.observations[-1].text
            ob = json.loads(msg)
            '''Obs has the following keys:
            ['PlayersKilled', 'TotalTime', 'Life', 'ZPos', 'IsAlive',
            'Name', 'entities', 'DamageTaken', 'Food', 'Yaw', 'TimeAlive',
            'XPos', 'WorldTime', 'Air', 'DistanceTravelled', 'Score', 'YPos',
            'Pitch', 'MobsKilled', 'XP']
            '''
            
            # print(ob['entities'], ob['XPos'], ob['YPos'])

            xPos = ob['XPos']
            yPos = ob['YPos']
            zPos = ob['ZPos']
            yaw = ob['Yaw']
            pitch = ob['Pitch']
            target = self.getNextTarget(ob['entities'])

            if target == None: # No enemies nearby
                if target != None:
                    sys.stdout.write("Not found: "+target['name'] + "\n")
                agent_host.sendCommand("move 0") # stop moving
                agent_host.sendCommand("attack 0") # stop attacking
                agent_host.sendCommand("turn 0") # stop turning
                agent_host.sendCommand("pitch 0") # stop looking up/down
            else:# enemy nearby, kill kill kill
                deltaYaw = 5
                deltaPitch = 5
                agent_host.sendCommand("turn " + str(deltaYaw))
                agent_host.sendCommand("pitch " + str(deltaPitch))
                agent_host.sendCommand("attack 1")

        for error in world_state.errors:
            print("Error:", error.text)

    def run(self, agent_host):
        """ Run the Agent on the world """
        agent_host.sendCommand("move 0.25")
        world_state = agent_host.getWorldState()
        while world_state.is_mission_running:
            #sys.stdout.write("*")
            time.sleep(0.1)
            world_state = agent_host.getWorldState()
            if world_state.number_of_observations_since_last_state > 0:
                msg = world_state.observations[-1].text
                ob = json.loads(msg)
                '''Obs has the following keys:
                ['PlayersKilled', 'TotalTime', 'Life', 'ZPos', 'IsAlive',
                'Name', 'entities', 'DamageTaken', 'Food', 'Yaw', 'TimeAlive',
                'XPos', 'WorldTime', 'Air', 'DistanceTravelled', 'Score', 'YPos',
                'Pitch', 'MobsKilled', 'XP']
                '''
                # print(ob.keys())

                xPos = ob['XPos']
                yPos = ob['YPos']
                zPos = ob['ZPos']
                yaw = ob['Yaw']
                pitch = ob['Pitch']
                target = self.getNextTarget(ob['entities'])

                if target == None: # No enemies nearby
                    if target != None:
                        sys.stdout.write("Not found: "+target['name'] + "\n")
                    agent_host.sendCommand("move 0") # stop moving
                    agent_host.sendCommand("attack 0") # stop attacking
                    agent_host.sendCommand("turn 0") # stop turning
                    agent_host.sendCommand("pitch 0") # stop looking up/down
                else:# enemy nearby, kill kill kill
                    deltaYaw = 5
                    deltaPitch = 5
                    agent_host.sendCommand("turn " + str(deltaYaw))
                    agent_host.sendCommand("pitch " + str(deltaPitch))
                    agent_host.sendCommand("attack 1")

            for error in world_state.errors:
                print("Error:", error.text)

    def getNextTarget(self, entities):
        for entity in entities:
            if entity['name'] != "MurderBot":
                return entity

    '''
    To Be Done:
        Discretize distance, player health, and current_weapon into states:
            Distance (melee, close, far), Health (<10%, 10-60%, 60-100%), current_weapon (sword, bow)
        Add a state for EnemyType in the Specialist
    '''

