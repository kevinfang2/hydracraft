import Constants
import json
import sys
import time
from collections import namedtuple
import numpy as np
import gym, ray
from gym.spaces import Discrete, Box

try:
    import MalmoPython
except:
    import malmo.MalmoPython as MalmoPython


EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

class BasicBot():
    """BasicBot will be given an AgentHost in its run method and just track down & attack various enemies"""
    def __init__(self, agent_host, name):
        self.name = name
        self.obs_size = 11
        self.agent_host = agent_host
        self.action_space = gym.spaces.Box(low=np.array([-1.0, -1.0, 0.0, 0.0]), high=np.array([1.0, 1.0, 1.0, 1.0]),
                                           dtype=np.float32)
        self.observation_space = Box(0, 99, shape=(2 * self.obs_size * self.obs_size,), dtype=np.float32)
        self.episode_step = 0
        self.obs = None
        self.episode_step = 0
        self.episode_return = 0
        self.returns = []
        self.steps = []
        self.last_life = 20
        return


    def get_observation(self, world_state):
        """
        Use the agent observation API to get a flattened 2 x 30 x 30 grid around the agent.
        The agent is in the center square facing up.

        Args
            world_state: <object> current agent world state

        Returns
            observation: <np.array> the state observation
        """
        obs = np.zeros((2 * self.obs_size * self.obs_size, ))

        while world_state.is_mission_running:
            time.sleep(0.1)
            world_state = self.agent_host.getWorldState()
            if len(world_state.errors) > 0:
                raise AssertionError('Could not load grid.')

            if world_state.number_of_observations_since_last_state > 0:
                # First we get the json from the observation API
                msg = world_state.observations[-1].text
                observations = json.loads(msg)
                if 'floorAll' not in observations:
                    continue
                # Get observation
                grid = observations['floorAll']
                for i, x in enumerate(grid):
                    if x == 'air':
                        obs[i] = 0
                    if x == 'stone':
                        obs[i] = 1
                # Rotate observation with orientation of agent
                obs = obs.reshape((2, self.obs_size, self.obs_size))
                xpos= self.obs_size //2
                zpos= self.obs_size //2

                for i , x in enumerate(observations['entities']):
                    if x['name'] != self.name:
                        cords = (int(x['y'])-1, xpos + int(x['x'])-1, zpos +int(x['z'])-1)
                        if max(cords) < self.obs_size and min(cords) >= 0:
                            obs[int(x['y'])-1, xpos + int(x['x'])-1, zpos +int(x['z'])-1] = 99
                yaw = observations['Yaw']
                if yaw >= 225 and yaw < 315:
                    obs = np.rot90(obs, k=1, axes=(1, 2))
                elif yaw >= 315 or yaw < 45:
                    obs = np.rot90(obs, k=2, axes=(1, 2))
                elif yaw >= 45 and yaw < 135:
                    obs = np.rot90(obs, k=3, axes=(1, 2))
                obs = obs.flatten()

                break

        return obs

    def step(self, command):
        '''Obs has the following keys:
                ['PlayersKilled', 'TotalTime', 'Life', 'ZPos', 'IsAlive',
                'Name', 'entities', 'DamageTaken', 'Food', 'Yaw', 'TimeAlive',
                'XPos', 'WorldTime', 'Air', 'DistanceTravelled', 'Score', 'YPos',
                'Pitch', 'MobsKilled', 'XP']
                '''
        self.agent_host.sendCommand('move ' + str(command[0]))
        self.agent_host.sendCommand('turn ' + str(command[1]))
        time.sleep(0.5)
        self.episode_step += 1

        world_state = self.agent_host.getWorldState()
        msg = world_state.observations[-1].text
        ob = json.loads(msg)
        for error in world_state.errors:
            print("Error:", error.text)
        self.obs = self.get_observation(world_state)

        # Get Done
        done = not world_state.is_mission_running

        # Get Reward
        reward = 0
        for r in world_state.rewards:
            reward += r.getValue()
        for i in ob['entities']:
            if i['name'] == 'robot1' and self.name == 'robot2' or i['name'] == 'robot2' and self.name == 'robot1':
                reward = (self.last_life-i['life'])/2 *0.1
                if reward < 0:
                    reward = 0
        self.last_life = ob['entities'][1]['life']
        self.episode_return += reward
        print(self.episode_return)
        return self.obs, reward, done, dict()

    def reset(self):
        """
        Resets the environment for the next episode.

        Returns
            observation: <np.array> flattened initial obseravtion
        """
        # Reset Malmo
        world_state = self.agent_host.getWorldState()
        self.episode_return = 0
        self.agent_host.sendCommand('chat /enchant ' + self.name + ' unbreaking 3')
        self.agent_host.sendCommand('chat /gamerule doNaturalRegen false')

        # Get Observation
        self.obs = self.get_observation(world_state)


        return self.obs

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

