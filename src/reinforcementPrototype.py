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
import json
from builtins import range

import numpy as np
from matplotlib import pyplot as plt

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

from gym.spaces import Discrete, Box
import ray
from ray.rllib.agents import ppo
from ray.rllib.env.multi_agent_env import MultiAgentEnv

# 0 is sword, 1 is bow
AGENT_INFO = {
    'robot1': 0,
    'robot2': 1
}
NUM_AGENTS = len(AGENT_INFO)

ARENA_SIZE = 11
ARENA_HEIGHT = 2


EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')
class environment(MultiAgentEnv):
    def __init__(self, env_config):
        # Static Parameters
        self.bots = []
        self.size = ARENA_SIZE
        self.reward_density = .1
        self.penalty_density = .02
        self.obs_size = 5
        self.max_episode_steps = 100
        self.log_frequency = 10
        self.action_dict = {
            0: 'move 1',  # Move one block forward
            1: 'turn 1',  # Turn 90 degrees to the right
            2: 'turn -1',  # Turn 90 degrees to the left
            3: 'attack 1'  # Destroy block
        }

        self.action_space = gym.spaces.Box(low=np.array([-1.0, -1.0, 0.0]), high=np.array([1.0, 1.0, 1.0]),
                                           dtype=np.float32)
        self.observation_space = Box(0, 99, shape=(ARENA_HEIGHT * ARENA_SIZE * ARENA_SIZE,), dtype=np.float32)

        # Rllib Parameters

        # Malmo Parameters
        self.agent_hosts = [MalmoPython.AgentHost()]
        try:
            self.agent_hosts[0].parse(sys.argv)
        except RuntimeError as e:
            print('ERROR:', e)
            print(self.agent_hosts[0].getUsage())
            exit(1)
        self.agent_hosts += [MalmoPython.AgentHost() for x in range(1, NUM_AGENTS)]
        self.bots += [basic.BasicBot(self.agent_hosts[x], "robot"+str(x+1)) for x in range(len(self.agent_hosts))]
        self.obs = None
        self.episode_step = 0
        self.episode_return = {}
        for i in range(NUM_AGENTS):
            self.episode_return["robot"+str(i+1)] = 0
        self.returns = []
        self.steps = []

    def reset(self):
        world_state = self.init_malmo()

        # Reset Variables
        self.returns.append(self.episode_return)
        current_step = self.steps[-1] if len(self.steps) > 0 else 0
        self.steps.append(current_step + self.episode_step)
        self.episode_return = {}
        for i in range(NUM_AGENTS):
            self.episode_return["robot" + str(i + 1)] = 0
        self.episode_step = 0

        # Log
        if len(self.returns) > self.log_frequency + 1 and \
                len(self.returns) % self.log_frequency == 0:
            self.log_returns()

        # Get Observation
        self.obs = {}
        for i in range(len(self.bots)):
            self.obs["robot" + str(i+1)] = self.bots[i].reset()

        return self.obs

    def step(self, action):
        self.episode_step += 1
        self.obs = {}
        reward = {}
        done = {}
        extra = {}
        for i in range(len(self.bots)):
            try:
                temp_obs, temp_reward, temp_done,temp_extra = self.bots[i].step(action[self.bots[i].name])
                self.obs["robot" + str(i + 1)] = temp_obs
                reward["robot" + str(i + 1)] = temp_reward
                done["robot" + str(i + 1)] = temp_done
                extra["robot" + str(i + 1)] = temp_extra
                self.episode_return["robot" + str(i + 1)] += reward["robot" + str(i + 1)]
                pass
            except Exception as e:
                print(e)
                pass
        #Terrible way to do this when have time fix to go through action list and not bots
        finished = len(done) == NUM_AGENTS or len(done) == 0
        for i in done:
            finished = finished and done[i]
        done["__all__"] = finished
        if finished:
            print("END", self.episode_return)
        return  self.obs, reward, done, extra

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
                    print("Other error:", e)
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
        # num_missions = 5 if INTEGRATION_TEST_MODE else 30000
        # for mission_no in range(1, num_missions+1):
        # xml = getXML()
        # print(xml)
        xml = arena.create_mission(AGENT_INFO)
        my_mission = MalmoPython.MissionSpec(xml, True)

        client_pool = MalmoPython.ClientPool()
        for x in range(10000, 10000 + NUM_AGENTS + 1):
            client_pool.add(MalmoPython.ClientInfo('127.0.0.1', x))
        experimentID = str(uuid.uuid4())

        for i in range(len(self.agent_hosts)):
            self.safeStartMission(self.agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)
        world_state = []
        self.safeWaitForStart(self.agent_hosts)
        multi = True
        for i in self.agent_hosts:
            world_state.append(i.getWorldState())
            multi = multi and world_state[-1].has_mission_begun
        while not multi:
            world_state = []
            time.sleep(0.1)
            multi = True
            for i in self.agent_hosts:
                world_state.append(i.getWorldState())
                multi = multi and world_state[-1].has_mission_begun
                for error in world_state.errors:
                    print("\nError:", error.text)
        return world_state

    def log_returns(self):
        """
        Log the current returns as a graph and text file

        Args:
            steps (list): list of global steps after each episode
            returns (list): list of total return of each episode
        """
        box = np.ones(self.log_frequency) / self.log_frequency
        robot1_scores = []
        robot2_scores = []
        for i in self.returns[1:]:
            robot1_scores.append(i['robot1'])
            robot2_scores.append(i['robot2'])
        returns_smooth_agent_1 = np.convolve(robot1_scores, box, mode='same')
        returns_smooth_agent_2 = np.convolve(robot2_scores, box, mode='same')
        plt.clf()
        plt.plot(self.steps[1:], returns_smooth_agent_1, 'g-', label='Agent 1')
        plt.plot(self.steps[1:], returns_smooth_agent_2, 'b--', label='Agent 2')
        plt.title('Fighter')
        plt.ylabel('Return')
        plt.xlabel('Steps')
        plt.legend()
        plt.savefig('returns.png')

        with open('returns.txt', 'w') as f:
            for step, value in zip(self.steps[1:], self.returns[1:]):
                f.write("{}\t{}\t{}\n".format(step, value['robot1'], value['robot2']))


if __name__ == '__main__':
    #TODO: policy for each robot
    robot_act_space = gym.spaces.Box(low=np.array([-1.0, -1.0, 0.0]), high=np.array([1.0, 1.0, 1.0]),
                                       dtype=np.float32)
    robot_obs_space = Box(0, 99, shape=(2 * ARENA_SIZE * ARENA_SIZE,), dtype=np.float32)
    ray.init()
    trainer = ppo.PPOTrainer(env=environment, config=
    {"multiagent": {
        "policies": {
            # the first tuple value is None -> uses default policy
            "robot": (None, robot_obs_space, robot_act_space, {"gamma": 0.85}),
        },
        "policy_mapping_fn":
            lambda agent_id:
                "robot"
    },
        'env_config': {},  # No environment parameters to configure
        'framework': 'torch',  # Use pyotrch instead of tensorflow
        'num_gpus': 0,  # We aren't using GPUs
        'num_workers': 0  # We aren't using parallelism
    })

    while True:
        print(trainer.train())