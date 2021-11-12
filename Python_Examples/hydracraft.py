from __future__ import print_function
from __future__ import division
# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Test of multi-agent missions - runs a number of agents in a shared environment.

try:
    from malmo import MalmoPython
except:
    import MalmoPython
from builtins import range
import os
import random
import sys
import time
import json
import uuid
from collections import namedtuple
import matplotlib.pyplot as plt
import numpy as np
from numpy.random import randint

import gym, ray
from gym.spaces import Discrete, Box
from ray.rllib.agents import ppo


class hydraCraft(gym.Env):

    def __init__(self, env_config):
        # Static Parameters
        self.size = 50
        self.num_agents = 2
        self.reward_density = .1
        self.penalty_density = .02
        self.obs_size = 30
        self.obs_height = 10
        self.max_episode_steps = 100
        self.log_frequency = 10
        self.action_dict = {
            0: 'move 1',  # Move one block forward
            1: 'turn 1',  # Turn 90 degrees to the right
            2: 'turn -1',  # Turn 90 degrees to the left
            3: 'attack 1'  # Swing Sword
        }

        # Rllib Parameters
        self.action_space = gym.spaces.Box(low=np.array([-1.0, -1.0, 0.0]), high=np.array([1.0, 1.0, 1.0]),
                                           dtype=np.float32)
        self.observation_space = Box(0, 1, shape=(self.obs_height * self.obs_size * self.obs_size,),
                                     dtype=np.float32)

        EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

        # Create one agent host for parsing:
        self.agent_hosts = [MalmoPython.AgentHost()]

        try:
            self.agent_hosts[0].parse(sys.argv)
        except RuntimeError as e:
            print('ERROR:', e)
            print(self.agent_hosts[0].getUsage())
            exit(1)

        # Create the rest of the agent hosts - one for each robot, plus one to give a bird's-eye view:
        self.agent_hosts += [MalmoPython.AgentHost() for x in range(1, self.num_agents)]

        if sys.version_info[0] == 2:
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

    def reset(self):
        """
        Resets the environment for the next episode.

        Returns
            observation: <np.array> flattened initial obseravtion
        """
        # Reset Malmo
        world_state = self.init_malmo()

        # Reset Variables
        self.returns.append(self.episode_return)
        current_step = self.steps[-1] if len(self.steps) > 0 else 0
        self.steps.append(current_step + self.episode_step)
        self.episode_return = 0
        self.episode_step = 0

        # Log
        if len(self.returns) > self.log_frequency + 1 and \
                len(self.returns) % self.log_frequency == 0:
            self.log_returns()

        # Get Observation
        self.obs, self.allow_break_action = self.get_observation(world_state)

        return self.obs

    # def step(self, action, agent_host):
    #     """
    #     Take an action in the environment and return the results.
    #
    #     Args
    #         action: <int> index of the action to take
    #
    #     Returns
    #         observation: <np.array> flattened array of obseravtion
    #         reward: <int> reward from taking action
    #         done: <bool> indicates terminal state
    #         info: <dict> dictionary of extra information
    #     """
    #
    #     # Get Action
    #     if action[-1] >= .5:
    #         action[-1] = 1
    #     else:
    #         action[-1] = 0
    #     command = action
    #     if command[2] != 1 or self.allow_break_action:
    #         agent_host.sendCommand("move " + command[0])
    #         agent_host.sendCommand("turn " + command[1])
    #         agent_host.sendCommand("attack " + command[2])
    #         time.sleep(1)
    #         self.episode_step += 1
    #
    #     # Get Observation
    #     world_state = self.agent_hosts.getWorldState()
    #     for error in world_state.errors:
    #         print("Error:", error.text)
    #     self.obs, self.allow_break_action = self.get_observation(world_state)
    #
    #     # Get Done
    #     done = not world_state.is_mission_running
    #
    #     # Get Reward
    #     reward = 0
    #     for r in world_state.rewards:
    #         reward += r.getValue()
    #     self.episode_return += reward
    #
    #     return self.obs, reward, done, dict()

    def get_mission_xml(self, reset):
        # Set up the Mission XML:
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
              <About>
                <Summary/>
              </About>
              <ModSettings>
                <MsPerTick>50</MsPerTick>
              </ModSettings>
                    <ServerSection>
                                <ServerInitialConditions>
                                    <Time>
                                        <StartTime>12000</StartTime>
                                        <AllowPassageOfTime>false</AllowPassageOfTime>
                                    </Time>
                                    <Weather>clear</Weather>
                                </ServerInitialConditions>
                                <ServerHandlers>
                                    <FlatWorldGenerator forceReset="'''+reset+'''"  generatorString="3;7,2;1;"/>
                                    <DrawingDecorator>''' + \
              "<DrawCuboid x1='{}' x2='{}' y1='2' y2='2' z1='{}' z2='{}' type='air'/>".format(-50, 50,
                                                                                              -50, 50) + \
              "<DrawCuboid x1='{}' x2='{}' y1='1' y2='1' z1='{}' z2='{}' type='stone'/>".format(-50, 50,
                                                                                                -50,
                                                                                                50) + \
              '''<DrawBlock x='0'  y='2' z='0' type='air' />
                               <DrawBlock x='0'  y='1' z='0' type='stone' />
                           </DrawingDecorator>
                           <ServerQuitWhenAnyAgentFinishes/>
                       </ServerHandlers>
                   </ServerSection>
    '''
        # Add an agent section for each robot. Robots run in survival mode.
        # Give each one a wooden pickaxe for protection...

        for i in range(self.num_agents):
            xml += '''<AgentSection mode="Survival">
                <Name>''' + self.agentName(i) + '''</Name>
                <AgentStart>
                  <Placement x="''' + str(random.randint(-17, 17)) + '''" y="2" z="''' + str(
                random.randint(-17, 17)) + '''"/>
                  <Inventory>
                    <InventoryObject type="wooden_pickaxe" slot="0" quantity="1"/>
                  </Inventory>
                </AgentStart>
                <AgentHandlers>
                  <ContinuousMovementCommands turnSpeedDegs="360"/>
                  <ChatCommands/>
                  <MissionQuitCommands/>
                  <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="2" zrange="40"/>
                  </ObservationFromNearbyEntities>
                  <ObservationFromRay/>
                  <ObservationFromFullStats/>
                </AgentHandlers>
              </AgentSection>'''

        xml += '</Mission>'
        return xml

    def agentName(self, i):
        return "Agent_" + str(i + 1)

    def safeStartMission(self, agent_host, my_mission, my_client_pool, my_mission_record, role, expId):
        used_attempts = 0
        max_attempts = 5
        print("Calling startMission for role", role)
        while True:
            try:
                # Attempt start:
                agent_host.startMission(my_mission, my_client_pool, my_mission_record, role, expId)
                break
            except MalmoPython.MissionException as e:
                errorCode = e.details.errorCode
                if errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                    print("Server not quite ready yet - waiting...")
                    time.sleep(2)
                elif errorCode == MalmoPython.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                    print("Not enough available Minecraft instances running.")
                    used_attempts += 1
                    if used_attempts < max_attempts:
                        print("Will wait in case they are starting up.", max_attempts - used_attempts, "attempts left.")
                        time.sleep(2)
                elif errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                    print("Server not found - has the mission with role 0 been started yet?")
                    used_attempts += 1
                    if used_attempts < max_attempts:
                        print("Will wait and retry.", max_attempts - used_attempts, "attempts left.")
                        time.sleep(2)
                else:
                    print("Other error:", e.message)
                    print("Waiting will not help here - bailing immediately.")
                    exit(1)
            if used_attempts == max_attempts:
                print("All chances used up - bailing now.")
                exit(1)
        print("startMission called okay.")

    def safeWaitForStart(self, agent_hosts):
        print("Waiting for the mission to start", end=' ')
        start_flags = [False for a in agent_hosts]
        start_time = time.time()
        time_out = 120  # Allow a two minute timeout.
        while not all(start_flags) and time.time() - start_time < time_out:
            states = [a.peekWorldState() for a in agent_hosts]
            start_flags = [w.has_mission_begun for w in states]
            errors = [e for w in states for e in w.errors]
            if len(errors) > 0:
                print("Errors waiting for mission start:")
                for e in errors:
                    print(e.text)
                print("Bailing now.")
                exit(1)
            time.sleep(0.1)
            print(".", end=' ')
        if time.time() - start_time >= time_out:
            print("Timed out while waiting for mission to start - bailing.")
            exit(1)
        print()
        print("Mission has started.")

    def init_malmo(self):
        """
        Initialize new malmo mission.
        """
        max_retries = 3
        client_pool = MalmoPython.ClientPool()
        for x in range(10000, 10000 + self.num_agents):
            client_pool.add(MalmoPython.ClientInfo('127.0.0.1', x))
       # return world_state

        for mission_no in range(1, 30000):
            print("Running mission #" + str(mission_no))
            # Create mission xml - use forcereset if this is the first mission.
            my_mission = MalmoPython.MissionSpec(self.get_mission_xml("true" if mission_no == 1 else "false"), True)

            # Generate an experiment ID for this mission.
            # This is used to make sure the right clients join the right servers -
            # if the experiment IDs don't match, the startMission request will be rejected.
            # In practice, if the client pool is only being used by one researcher, there
            # should be little danger of clients joining the wrong experiments, so a static
            # ID would probably suffice, though changing the ID on each mission also catches
            # potential problems with clients and servers getting out of step.

            # Note that, in this sample, the same process is responsible for all calls to startMission,
            # so passing the experiment ID like this is a simple matter. If the agentHosts are distributed
            # across different threads, processes, or machines, a different approach will be required.
            # (Eg generate the IDs procedurally, in a way that is guaranteed to produce the same results
            # for each agentHost independently.)
            experimentID = str(uuid.uuid4())

            for i in range(len(self.agent_hosts)):
                self.safeStartMission(self.agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i,
                                 experimentID)

            self.safeWaitForStart(self.agent_hosts)

            time.sleep(1)
            unresponsive_count = [10 for x in range(self.num_agents)]
            num_responsive_agents = lambda: sum([urc > 0 for urc in unresponsive_count])

            timed_out = False

            while num_responsive_agents() > 0 and not timed_out:
                for i in range(self.num_agents):
                    agent = self.agent_hosts[i]
                    world_state = agent.getWorldState()
                    obs = self.get_observation(world_state, i)
                    ################################
                    ####                        ####
                    #### This is Where Steps Go ####
                    ####                        ####
                    ################################
                time.sleep(0.05)
            print()

            if not timed_out:
                # All agents except the watcher have died.
                # We could wait for the mission to time out, but it's quicker
                # to make the watcher quit manually:
                self.agent_hosts[-1].sendCommand("quit")
            else:
                # We timed out. Bonus score to any agents that survived!
                for i in range(self.num_agents):
                    if unresponsive_count[i] > 0:
                        print("SURVIVOR: " + self.agentName(i))
                        self.survival_scores[i] += 1

            print("Waiting for mission to end ", end=' ')
            # Mission should have ended already, but we want to wait until all the various agent hosts
            # have had a chance to respond to their mission ended message.
            hasEnded = False
            while not hasEnded:
                hasEnded = True  # assume all good
                print(".", end="")
                time.sleep(0.1)
                for ah in self.agent_hosts:
                    world_state = ah.getWorldState()
                    if world_state.is_mission_running:
                        hasEnded = False  # all not good

    def get_observation(self, world_state, i):
        """
        Use the agent observation API to get a flattened grid around the agent.
        The agent is in the center square facing up.

        Args
            world_state: <object> current agent world state

        Returns
            observation: <np.array> the state observation
            allow_break_action: <bool> whether the agent is facing a diamond
        """
        obs = np.zeros((self.obs_height * self.obs_size * self.obs_size,))
        allow_break_action = False

        while world_state.is_mission_running:
            time.sleep(0.1)
            world_state = self.agent_hosts[i].getWorldState()
            if len(world_state.errors) > 0:
                raise AssertionError('Could not load grid.')

            if world_state.number_of_observations_since_last_state > 0:
                # First we get the json from the observation API
                msg = world_state.observations[-1].text
                observations = json.loads(msg)

                # Get observation
                grid = observations
                for i, x in enumerate(grid):
                    obs[i] = x == 'diamond_ore' or x == 'lava'

                # Rotate observation with orientation of agent
                obs = obs.reshape((self.obs_height, self.obs_size, self.obs_size))
                yaw = observations['Yaw']
                if yaw >= 225 and yaw < 315:
                    obs = np.rot90(obs, k=1, axes=(1, 2))
                elif yaw >= 315 or yaw < 45:
                    obs = np.rot90(obs, k=2, axes=(1, 2))
                elif yaw >= 45 and yaw < 135:
                    obs = np.rot90(obs, k=3, axes=(1, 2))
                obs = obs.flatten()

                allow_break_action = observations['LineOfSight']['type'] == 'diamond_ore'

                break

        return obs, allow_break_action

    def log_returns(self):
        """
        Log the current returns as a graph and text file

        Args:
            steps (list): list of global steps after each episode
            returns (list): list of total return of each episode
        """
        box = np.ones(self.log_frequency) / self.log_frequency
        returns_smooth = np.convolve(self.returns[1:], box, mode='same')
        plt.clf()
        plt.plot(self.steps[1:], returns_smooth)
        plt.title('Hydracollector')
        plt.ylabel('Return')
        plt.xlabel('Steps')
        plt.savefig('returns.png')

        with open('returns.txt', 'w') as f:
            for step, value in zip(self.steps[1:], self.returns[1:]):
                f.write("{}\t{}\n".format(step, value))

if __name__ == '__main__':
    ray.init()
    trainer = ppo.PPOTrainer(env=hydraCraft, config={
        'env_config': {},  # No environment parameters to configure
        'framework': 'torch',  # Use pyotrch instead of tensorflow
        'num_gpus': 0,  # We aren't using GPUs
        'num_workers': 0  # We aren't using parallelism
    })

    while True:
        print(trainer.train())
