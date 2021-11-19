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



try:
    import MalmoPython
except:
    import malmo.MalmoPython as MalmoPython
import os
import sys
import time
import uuid
from collections import namedtuple
import gym
import arena
import basic

import ray
from ray.rllib.agents import ppo

# 0 is sword, 1 is bow
AGENT_INFO = {
    'robot1': 0,
    'robot2': 1
}
NUM_AGENTS = len(AGENT_INFO)



EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')
class multi_agent_start(gym.Env):

    def __init__(self, env_config):

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
        agent_hosts += [MalmoPython.AgentHost() for x in range(1, NUM_AGENTS) ]

        # Set up debug output:
        for ah in agent_hosts:
            ah.setDebugOutput(DEBUG)    # Turn client-pool connection messages on/off.

#        if sys.version_info[0] == 2:
#            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
#       else:
#           import functools
#            print = functools.partial(print, flush=True)

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
                        print("suh", e)
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

        client_pool = MalmoPython.ClientPool()
        for x in range(10000, 10000 + NUM_AGENTS + 1):
            client_pool.add( MalmoPython.ClientInfo('127.0.0.1', x) )

        # num_missions = 5 if INTEGRATION_TEST_MODE else 30000
        # for mission_no in range(1, num_missions+1):
            # xml = getXML()
            # print(xml)
        xml = arena.create_mission(AGENT_INFO)
        my_mission = MalmoPython.MissionSpec(xml, True)
        experimentID = str(uuid.uuid4())

        for i in range(len(agent_hosts)):
            safeStartMission(agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)

        safeWaitForStart(agent_hosts)
        multi = True
        for i in agent_hosts:
            world_state = i.getWorldState()
            multi = multi and world_state.has_mission_begun
        while not multi:
            time.sleep(0.1)
            multi = True
            for i in agent_hosts:
                world_state = i.getWorldState()
                multi = multi and world_state.has_mission_begun
                for error in world_state.errors:
                    print("\nError:", error.text)

if __name__ == '__main__':
    ray.init()
    trainer = ppo.PPOTrainer(env=multi_agent_start, config={
        'env_config': {},  # No environment parameters to configure
        'framework': 'torch',  # Use pyotrch instead of tensorflow
        'num_gpus': 0,  # We aren't using GPUs
        'num_workers': 0  # We aren't using parallelism
    })

    while True:
        print(trainer.train())