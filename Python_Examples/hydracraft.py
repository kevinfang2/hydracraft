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

from builtins import range
from past.utils import old_div
import MalmoPython
import json
import logging
import math
import os
import random
import sys
import time
import re
import uuid
from collections import namedtuple
from operator import add

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

# Create one agent host for parsing:
agent_hosts = [MalmoPython.AgentHost()]

# Parse the command-line options:
agent_hosts[0].addOptionalFlag( "debug,d", "Display debug information.")
agent_hosts[0].addOptionalIntArgument("agents,n", "Number of agents to use, including observer.", 2)

try:
    agent_hosts[0].parse( sys.argv )
except RuntimeError as e:
    print('ERROR:',e)
    print(agent_hosts[0].getUsage())
    exit(1)
if agent_hosts[0].receivedArgument("help"):
    print(agent_hosts[0].getUsage())
    exit(0)

DEBUG = agent_hosts[0].receivedArgument("debug")
INTEGRATION_TEST_MODE = agent_hosts[0].receivedArgument("test")
agents_requested = agent_hosts[0].getIntArgument("agents")
NUM_AGENTS = max(1, agents_requested) # Will be NUM_AGENTS robots running around, plus one static observer.
NUM_MOBS = NUM_AGENTS * 2
NUM_ITEMS = NUM_AGENTS * 2

# Create the rest of the agent hosts - one for each robot, plus one to give a bird's-eye view:
agent_hosts += [MalmoPython.AgentHost() for x in range(1, NUM_AGENTS) ]

# Set up debug output:
for ah in agent_hosts:
    ah.setDebugOutput(DEBUG)    # Turn client-pool connection messages on/off.

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)

def agentName(i):
    return "Robot#" + str(i + 1)

def safeStartMission(agent_host, my_mission, my_client_pool, my_mission_record, role, expId):
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

def safeWaitForStart(agent_hosts):
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

def calcTurnValue(us, them, current_yaw):
    ''' Calc turn speed required to steer "us" towards "them".'''
    dx = them[0] - us[0]
    dz = them[1] - us[1]
    yaw = -180 * math.atan2(dx, dz) / math.pi
    difference = yaw - current_yaw
    while difference < -180:
        difference += 360;
    while difference > 180:
        difference -= 360;
    difference /= 180.0;
    return difference

def getVelocity(this_agent, entities, current_yaw, current_pos, current_health):
    ''' Calculate a good velocity to head in, according to the entities around us.'''
    # Get all the points of interest (every entity apart from the robots)
    poi = [ent for ent in entities if not ent.name.startswith("Robot")]
    if len(poi) == 0:
        return 0,0  # Nothing around, so just stand still.

    # Get position of all zombies
    zombies = [ent for ent in poi if ent.name == "Zombie"]
    # Get position of all collectibles
    items = [ent for ent in poi if not ent.name == "Zombie"]

    # Useful lambdas:
    distance = lambda entA, entB : abs(entA.x - entB.x) + abs(entA.y - entB.y) + abs(entA.z - entB.z)
    proximity_score = lambda target, entities : sum([old_div(1.0, (1 + distance(target, ent) * distance(target, ent))) for ent in entities if not ent == target])

    # Now, score each poi to find the one we most want to visit.
    scores = []
    for ent in poi:
        dist_from_us = abs(ent.x - current_pos[0]) + abs(ent.z - current_pos[1])
        dist_score = old_div(1.0, (1 + dist_from_us * dist_from_us))
        zombie_proximity = proximity_score(ent, zombies)
        if zombie_proximity == 0:
            zombie_proximity = 1    # Happens if there are no more zombies left.
        item_proximity = proximity_score(ent, items)
        turn_distance = abs(calcTurnValue(current_pos, (ent.x, ent.z), current_yaw))
        scores.append(dist_score * item_proximity * (1 - turn_distance) * (1 - turn_distance) / zombie_proximity)

    # Pick the best-scoring entity:
    i = scores.index(max(scores))
    ent = poi[i]
    # Turn value to head towards it:
    turn = calcTurnValue(current_pos, (ent.x, ent.z), current_yaw)
    # Calculate a speed to use - helps to avoid orbiting:
    dx = ent.x - current_pos[0]
    dz = ent.z - current_pos[1]
    speed = 1.0 - (old_div(1.0, (1.0 + abs(old_div(dx,3.0)) + abs(old_div(dz,3.0)))))
    if abs(dx) + abs(dz) < 1.5:
        speed = 0
    return turn, speed

def drawMobs():
    xml = ""
    for i in range(NUM_MOBS):
        x = str(random.randint(-17,17))
        z = str(random.randint(-17,17))
        xml += '<DrawEntity x="' + x + '" y="214" z="' + z + '" type="Zombie"/>'
    return xml

def drawItems():
    xml = ""
    for i in range(NUM_ITEMS):
        x = str(random.randint(-17,17))
        z = str(random.randint(-17,17))
        xml += '<DrawItem x="' + x + '" y="224" z="' + z + '" type="apple"/>'
    return xml

def getXML():
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
                            <FlatWorldGenerator generatorString="3;7,2;1;"/>
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

    for i in range(NUM_AGENTS):
        xml += '''<AgentSection mode="Survival">
        <Name>''' + agentName(i) + '''</Name>
        <AgentStart>
          <Placement x="''' + str(random.randint(-17,17)) + '''" y="2" z="''' + str(random.randint(-17,17)) + '''"/>
          <Inventory>
            <InventoryObject type="wooden_pickaxe" slot="0" quantity="1"/>
          </Inventory>
        </AgentStart>
        <AgentHandlers>
          <ContinuousMovementCommands turnSpeedDegs="360"/>
          <ChatCommands/>
          <MissionQuitCommands/>
          <RewardForCollectingItem>
            <Item type="apple" reward="1"/>
          </RewardForCollectingItem>
          <ObservationFromNearbyEntities>
            <Range name="entities" xrange="40" yrange="2" zrange="40"/>
          </ObservationFromNearbyEntities>
          <ObservationFromRay/>
          <ObservationFromFullStats/>
        </AgentHandlers>
      </AgentSection>'''

    xml += '</Mission>'
    return xml

# Set up a client pool.
# IMPORTANT: If ANY of the clients will be on a different machine, then you MUST
# make sure that any client which can be the server has an IP address that is
# reachable from other machines - ie DO NOT SIMPLY USE 127.0.0.1!!!!
# The IP address used in the client pool will be broadcast to other agents who
# are attempting to find the server - so this will fail for any agents on a
# different machine.
client_pool = MalmoPython.ClientPool()
for x in range(10000, 10000 + NUM_AGENTS + 1):
    client_pool.add( MalmoPython.ClientInfo('127.0.0.1', x) )

# Keep score of how our robots are doing:
survival_scores = [0 for x in range(NUM_AGENTS)]    # Lasted to the end of the mission without dying.
apple_scores = [0 for x in range(NUM_AGENTS)]       # Collecting apples is good.
zombie_kill_scores = [0 for x in range(NUM_AGENTS)] # Good! Help rescue humanity from zombie-kind.
player_kill_scores = [0 for x in range(NUM_AGENTS)] # Bad! Don't kill the other players!

num_missions = 5 if INTEGRATION_TEST_MODE else 30000
for mission_no in range(1, num_missions+1):
    print("Running mission #" + str(mission_no))
    # Create mission xml - use forcereset if this is the first mission.
    my_mission = MalmoPython.MissionSpec(getXML(), True)

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

    for i in range(len(agent_hosts)):
        safeStartMission(agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)

    safeWaitForStart(agent_hosts)

    time.sleep(1)
    running = True
    current_yaw = [0 for x in range(NUM_AGENTS)]
    current_pos = [(0,0) for x in range(NUM_AGENTS)]
    current_life = [20 for x in range(NUM_AGENTS)]
    # When an agent is killed, it stops getting observations etc. Track this, so we know when to bail.
    unresponsive_count = [10 for x in range(NUM_AGENTS)]
    num_responsive_agents = lambda: sum([urc > 0 for urc in unresponsive_count])

    timed_out = False

    while num_responsive_agents() > 0 and not timed_out:
        for i in range(NUM_AGENTS):
            ah = agent_hosts[i]
            world_state = ah.getWorldState()
            if world_state.is_mission_running == False:
                timed_out = True
            if world_state.is_mission_running and world_state.number_of_observations_since_last_state > 0:
                unresponsive_count[i] = 10
                msg = world_state.observations[-1].text
                ob = json.loads(msg)
                if "Yaw" in ob:
                    current_yaw[i] = ob[u'Yaw']
                if "Life" in ob:
                    life = ob[u'Life']
                    if life != current_life[i]:
                        current_life[i] = life
                if "PlayersKilled" in ob:
                    player_kill_scores[i] = -ob[u'PlayersKilled']
                if "MobsKilled" in ob:
                    zombie_kill_scores[i] = ob[u'MobsKilled']
                if "XPos" in ob and "ZPos" in ob:
                    current_pos[i] = (ob[u'XPos'], ob[u'ZPos'])
                if "entities" in ob:
                    entities = [EntityInfo(k["x"], k["y"], k["z"], k["name"]) for k in ob["entities"]]
                    turn, speed = getVelocity(agentName(i), entities, current_yaw[i], current_pos[i], current_life[i])
                    ah.sendCommand("move " + str(speed))
                    ah.sendCommand("turn " + str(turn))
                if u'LineOfSight' in ob:
                    los = ob[u'LineOfSight']
                    if los[u'hitType'] == "entity" and los[u'inRange'] and los[u'type'] == "Zombie":
                        ah.sendCommand("attack 1")
                        ah.sendCommand("attack 0")
            elif world_state.number_of_observations_since_last_state == 0:
                unresponsive_count[i] -= 1
            if world_state.number_of_rewards_since_last_state > 0:
                for rew in world_state.rewards:
                    apple_scores[i] += rew.getValue()

        time.sleep(0.05)
    print()

    if not timed_out:
        # All agents except the watcher have died.
        # We could wait for the mission to time out, but it's quicker
        # to make the watcher quit manually:
        agent_hosts[-1].sendCommand("quit")
    else:
        # We timed out. Bonus score to any agents that survived!
        for i in range(NUM_AGENTS):
            if unresponsive_count[i] > 0:
                print("SURVIVOR: " + agentName(i))
                survival_scores[i] += 1

    print("Waiting for mission to end ", end=' ')
    # Mission should have ended already, but we want to wait until all the various agent hosts
    # have had a chance to respond to their mission ended message.
    hasEnded = False
    while not hasEnded:
        hasEnded = True # assume all good
        print(".", end="")
        time.sleep(0.1)
        for ah in agent_hosts:
            world_state = ah.getWorldState()
            if world_state.is_mission_running:
                hasEnded = False # all not good

    win_counts = [0 for robot in range(NUM_AGENTS)]
    winner_survival = survival_scores.index(max(survival_scores))
    winner_zombies = zombie_kill_scores.index(max(zombie_kill_scores))
    winner_players = player_kill_scores.index(max(player_kill_scores))
    winner_apples = apple_scores.index(max(apple_scores))
    win_counts[winner_survival] += 1
    win_counts[winner_zombies] += 1
    win_counts[winner_players] += 1
    win_counts[winner_apples] += 1

    print()
    print("=========================================")
    print("Survival scores: ", survival_scores, "Winner: ", agentName(winner_survival))
    print("Zombie kill scores: ", zombie_kill_scores, "Winner: ", agentName(winner_zombies))
    print("Player kill scores: ", player_kill_scores, "Winner: ", agentName(winner_players))
    print("Apple scores: ", apple_scores, "Winner: ", agentName(winner_apples))
    print("=========================================")
    print("CURRENT OVERALL WINNER: " + agentName(win_counts.index(max(win_counts))))
    print()

    time.sleep(2)


def temp():
    # Rllib docs: https://docs.ray.io/en/latest/rllib.html
    # Malmo XML docs: https://docs.ray.io/en/latest/rllib.html

    try:
        from malmo import MalmoPython
    except:
        import MalmoPython

    import sys
    import time
    import json
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
                3: 'attack 1'  # Destroy block
            }

            # Rllib Parameters
            self.action_space = gym.spaces.Box(low=np.array([-1.0, -1.0, 0.0]), high=np.array([1.0, 1.0, 1.0]),
                                               dtype=np.float32)
            self.observation_space = Box(0, 1, shape=(self.obs_height * self.obs_size * self.obs_size,),
                                         dtype=np.float32)

            # Malmo Parameters
            self.agent_host = MalmoPython.AgentHost()
            try:
                self.agent_host.parse(sys.argv)
            except RuntimeError as e:
                print('ERROR:', e)
                print(self.agent_host.getUsage())
                exit(1)

            # DiamondCollector Parameters
            self.obs = None
            self.allow_break_action = False
            self.episode_step = 0
            self.episode_return = 0
            self.returns = []
            self.steps = []

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

        def step(self, action):
            """
            Take an action in the environment and return the results.

            Args
                action: <int> index of the action to take

            Returns
                observation: <np.array> flattened array of obseravtion
                reward: <int> reward from taking action
                done: <bool> indicates terminal state
                info: <dict> dictionary of extra information
            """

            # Get Action
            if action[-1] >= .5:
                action[-1] = 1
            else:
                action[-1] = 0
            command = action
            if command[2] != 1 or self.allow_break_action:
                self.agent_host.sendCommand("move " + command[0])
                self.agent_host.sendCommand("turn " + command[1])
                self.agent_host.sendCommand("attack " + command[2])
                time.sleep(1)
                self.episode_step += 1

            # Get Observation
            world_state = self.agent_host.getWorldState()
            for error in world_state.errors:
                print("Error:", error.text)
            self.obs, self.allow_break_action = self.get_observation(world_state)

            # Get Done
            done = not world_state.is_mission_running

            # Get Reward
            reward = 0
            for r in world_state.rewards:
                reward += r.getValue()
            self.episode_return += reward

            return self.obs, reward, done, dict()

        def get_mission_xml(self):
            return '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
                    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

                        <About>
                            <Summary>Diamond Collector</Summary>
                        </About>

                        <ServerSection>
                            <ServerInitialConditions>
                                <Time>
                                    <StartTime>12000</StartTime>
                                    <AllowPassageOfTime>false</AllowPassageOfTime>
                                </Time>
                                <Weather>clear</Weather>
                            </ServerInitialConditions>
                            <ServerHandlers>
                                <FlatWorldGenerator generatorString="3;7,2;1;"/>
                                <DrawingDecorator>''' + \
                   "<DrawCuboid x1='{}' x2='{}' y1='2' y2='2' z1='{}' z2='{}' type='air'/>".format(-self.size,
                                                                                                   self.size,
                                                                                                   -self.size,
                                                                                                   self.size) + \
                   "<DrawCuboid x1='{}' x2='{}' y1='1' y2='1' z1='{}' z2='{}' type='stone'/>".format(-self.size,
                                                                                                     self.size,
                                                                                                     -self.size,
                                                                                                     self.size) + \
                   '''<DrawBlock x='0'  y='2' z='0' type='air' />
                                    <DrawBlock x='0'  y='1' z='0' type='stone' />
                                </DrawingDecorator>
                                <ServerQuitWhenAnyAgentFinishes/>
                            </ServerHandlers>
                        </ServerSection>

                        <AgentSection mode="Survival">
                            <Name>player1</Name>
                            <AgentStart>
                                <Placement x="24.5" y="2" z="0.5" pitch="45" yaw="0"/>
                                <Inventory>
                                    <InventoryItem slot="0" type="diamond_sword"/>
                                </Inventory>
                            </AgentStart>
                            <AgentHandlers>
                                <ContinuousMovementCommands/>
                                <ObservationFromFullStats/>
                                <ObservationFromRay/>
                                <ObservationFromGrid>
                                    <Grid name="floorAll">
                                        <min x="-''' + str(int(self.obs_size / 2)) + '''" y="-1" z="-''' + str(
                int(self.obs_size / 2)) + '''"/>
                                        <max x="''' + str(int(self.obs_size / 2)) + '''" y="9" z="''' + str(
                int(self.obs_size / 2)) + '''"/>
                                    </Grid>
                                </ObservationFromGrid>
                                <AgentQuitFromReachingCommandQuota total="''' + str(self.max_episode_steps * 3) + '''" />
                                <AgentQuitFromTouchingBlockType>
                                    <Block type="bedrock" />
                                </AgentQuitFromTouchingBlockType>
                            </AgentHandlers>
                        </AgentSection>

                        <AgentSection mode="Survival">
                            <Name>player2</Name>
                            <AgentStart>
                                <Placement x="-24.5" y="2" z="0.5" pitch="45" yaw="0"/>
                                <Inventory>
                                    <InventoryItem slot="0" type="diamond_sword"/>
                                </Inventory>
                            </AgentStart>
                            <AgentHandlers>
                                <ContinuousMovementCommands/>
                                <ObservationFromFullStats/>
                                <ObservationFromRay/>
                                <ObservationFromGrid>
                                    <Grid name="floorAll">
                                        <min x="-''' + str(int(self.obs_size / 2)) + '''" y="-1" z="-''' + str(
                int(self.obs_size / 2)) + '''"/>
                                        <max x="''' + str(int(self.obs_size / 2)) + '''" y="9" z="''' + str(
                int(self.obs_size / 2)) + '''"/>
                                    </Grid>
                                </ObservationFromGrid>
                                <AgentQuitFromReachingCommandQuota total="''' + str(self.max_episode_steps * 3) + '''" />
                                <AgentQuitFromTouchingBlockType>
                                    <Block type="bedrock" />
                                </AgentQuitFromTouchingBlockType>
                            </AgentHandlers>
                        </AgentSection>
                    </Mission>'''

        def init_malmo(self):
            """
            Initialize new malmo mission.
            """
            my_mission = MalmoPython.MissionSpec(self.get_mission_xml(), True)
            my_mission_record = MalmoPython.MissionRecordSpec()
            my_mission.requestVideo(800, 500)
            my_mission.setViewpoint(1)

            max_retries = 3
            my_clients = MalmoPython.ClientPool()
            my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10000))
            my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10001))  # add Minecraft machines here as available

            for retry in range(max_retries):
                try:
                    self.agent_host.startMission(my_mission, my_clients, my_mission_record, 0, 'DiamondCollector')
                    break
                except RuntimeError as e:
                    if retry == max_retries - 1:
                        print("Error starting mission:", e)
                        exit(1)
                    else:
                        time.sleep(2)

            world_state = self.agent_host.getWorldState()
            while not world_state.has_mission_begun:
                time.sleep(0.1)
                world_state = self.agent_host.getWorldState()
                for error in world_state.errors:
                    print("\nError:", error.text)

            return world_state

        def get_observation(self, world_state):
            """
            Use the agent observation API to get a flattened 2 x 5 x 5 grid around the agent.
            The agent is in the center square facing up.

            Args
                world_state: <object> current agent world state

            Returns
                observation: <np.array> the state observation
                allow_break_action: <bool> whether the agent is facing a diamond
            """
            obs = np.zeros((2 * self.obs_size * self.obs_size,))
            allow_break_action = False

            while world_state.is_mission_running:
                time.sleep(0.1)
                world_state = self.agent_host.getWorldState()
                if len(world_state.errors) > 0:
                    raise AssertionError('Could not load grid.')

                if world_state.number_of_observations_since_last_state > 0:
                    # First we get the json from the observation API
                    msg = world_state.observations[-1].text
                    observations = json.loads(msg)

                    # Get observation
                    grid = observations['floorAll']
                    for i, x in enumerate(grid):
                        obs[i] = x == 'diamond_ore' or x == 'lava'

                    # Rotate observation with orientation of agent
                    obs = obs.reshape((2, self.obs_size, self.obs_size))
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
