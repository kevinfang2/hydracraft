import six

import random
from mission import Mission, MissionEnvironment, MissionStateBuilder


# Simple multi-agent mission, with 2 agents and an observer based on:
# https://github.com/Microsoft/malmo/blob/master/Malmo/samples/Python_examples/multi_agent_test.py
class MultiAgent(Mission):
    def __init__(self, ms_per_tick):
        mission_name = 'multi_agent'
        agent_names = ['Agent_1', 'Agent_2']

        self.NUM_MOBS = 30
        self.NUM_ITEMS = 4
        
        DENSITY = 0.1

        def stones():
            stone = ''
            for i in range(-18,18):
                for j in range(-18,18):
                    if random.randint(0,100)/100. < DENSITY:
                        stone +="<DrawBlock x='%s'  y='2' z='%s' type='bedrock' />"%(i,j)
            return stone

        def drawFence():
            fence = ''
            for i in range(-20,20):
                for j in range(-20,20):
                    fence += "<DrawBlock x='20' y='2' z='{}' type='fence'/>".format(i)
                    fence += "<DrawBlock x='-20' y='2' z='{}' type='fence'/>".format(i)
                    fence += "<DrawBlock x='{}' y='2' z='20' type='fence'/>".format(i)
                    fence += "<DrawBlock x='{}' y='2' z='-20' type='fence'/>".format(i)
            return fence
            
        mission_xml='''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
              <About>
                <Summary>Fighting Simulator</Summary>
                <Description>Defeat Enemy to Continue!</Description>
              </About>
              <ModSettings>
                <MsPerTick>50</MsPerTick>
              </ModSettings>
              <ServerSection>
                <ServerInitialConditions>
                    <Time>
                        <StartTime>6000</StartTime>
                           <AllowPassageOfTime>false</AllowPassageOfTime>
                        </Time>
                    <AllowSpawning>false</AllowSpawning>
                </ServerInitialConditions>
                <ServerHandlers>
                    <FlatWorldGenerator generatorString="3;7,2;1;"/>
                    <DrawingDecorator>''' + \
                        "<DrawCuboid x1='{}' x2='{}' y1='2' y2='2' z1='{}' z2='{}' type='air'/>".format(-50, 50,
                                                                                            -50, 50) + \
                        "<DrawCuboid x1='{}' x2='{}' y1='1' y2='1' z1='{}' z2='{}' type='stone'/>".format(-50, 50,
                                                                                            -50,
                                                                                            50) + \
                        stones() +\
                        drawFence() +\
                        '''<DrawBlock x="0" y="226" z="0" type="fence"/>''' + self.drawMobs() + \
                        '''
                        <DrawBlock x='0'  y='2' z='0' type='air' />
                        <DrawBlock x='0'  y='1' z='0' type='stone' />
                    </DrawingDecorator>
                    <ServerQuitWhenAnyAgentFinishes description="server sees murder happen"/>
                </ServerHandlers>
            </ServerSection>
          '''

        # Add an agent section for each robot. Robots run in survival mode.
        # Give each one a wooden pickaxe for protection...
        for i in range(len(agent_names[:-1])):
            weapon = random.randint(0,1)

            mission_xml += '''<AgentSection mode="Survival">
                <Name>''' + agent_names[i] + '''</Name>
                <AgentStart>
                  <Placement x="''' + str(random.randint(-17, 17)) + '''" y="2" z="''' + str(
                random.randint(-17, 17)) + '''"/>
                    <Inventory>
                '''
            # if(weapon == 0):
            mission_xml += '''<InventoryObject slot="0" type="wooden_sword" quantity="1"/>'''
            # else:
                # mission_xml += '''<InventoryObject slot="1" type="bow" quantity="1"/>
                    # <InventoryObject slot="2" type="arrow" quantity="64"/>'''
                
            mission_xml += '''
                </Inventory>
            </AgentStart>
            <AgentHandlers>
                <VideoProducer>
                    <Width>512</Width>
                    <Height>512</Height>
                </VideoProducer>
                <ObservationFromFullStats/>
                <ContinuousMovementCommands turnSpeedDegs="45"/>

                <RewardForTimeTaken initialReward="500" delta="-5" density="MISSION_END"/>
                <RewardForDamagingEntity>
                    <Mob type="Zombie" reward="10000"/>
                </RewardForDamagingEntity>
            </AgentHandlers>
            </AgentSection>'''

        mission_xml += '''</Mission>'''
        
        super(MultiAgent, self).__init__(mission_name=mission_name, agent_names=agent_names, mission_xml=mission_xml)

    def drawMobs(self):
        xml = ""
        for i in range(self.NUM_MOBS):
            x = str(random.randint(-17, 17))
            z = str(random.randint(-17, 17))
            xml += '<DrawEntity x="' + x + '" y="1" z="' + z + '" type="Zombie"/>'
        return xml

    def drawItems(self):
        xml = ""
        for i in range(self.NUM_ITEMS):
            x = str(random.randint(-17, 17))
            z = str(random.randint(-17, 17))
            xml += '<DrawItem x="' + x + '" y="224" z="' + z + '" type="apple"/>'
        return xml


# Define the mission environment
class MultiAgentEnvironment(MissionEnvironment):
    def __init__(self, mission_name, mission_xml, remotes, state_builder, role=0, recording_path=None,
                 force_world_reset=True):
        actions = ['move 1', 'move -1', 'turn 1', 'turn -1', 'attack 1']

        self._abs_max_reward = 10  # For reward normalization needed by some RL algorithms

        super(MultiAgentEnvironment, self).__init__(mission_name, mission_xml, actions, remotes, state_builder,
                                                    role=role, recording_path=recording_path,
                                                    force_world_reset=force_world_reset)

    # Do an action
    def step(self, action):
        action_id = action
        assert 0 <= action_id <= self.available_actions, \
            "action %d is not valid (should be in [0, %d[)" % (action_id,
                                                               self.available_actions)

        # For discrete action space, do the environment action corresponding to the action id sent by the agent
        action = self._actions[action_id]
        assert isinstance(action, six.string_types)
        if self._action_count > 0:
            if self._previous_action == 'attack 1':
                self._agent.sendCommand('attack 0')
        self._agent.sendCommand(action)
        self._previous_action = action
        self._action_count += 1

        self._await_next_obs()
        return self.state, sum([reward.getValue() for reward in self._world.rewards]), self.done, {}

    @property
    def abs_max_reward(self):
        return self._abs_max_reward


# Return low-level observations
class MultiAgentStateBuilder(MissionStateBuilder):
    def __init__(self):
        super(MultiAgentStateBuilder, self).__init__()

    def build(self, environment):
        world_obs = environment.world_observations
        return world_obs
