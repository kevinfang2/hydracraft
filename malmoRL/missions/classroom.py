import sys
import six
import numpy as np
import random

from mission import Mission, MissionEnvironment, MissionStateBuilder


# Simple single-agent mission
class Classroom(Mission):
    def __init__(self, ms_per_tick):
        self.mission_name = 'classroom'
        self.agent_names = ['Agent_1']
        self.mission_xml = self.get_mission_xml()

    def get_mission_xml(self):
        mission_name = 'classroom'
        agent_names = ['Agent_1']
        self.NUM_MOBS = 10
        
        DENSITY = 0.1

        def drawMobs():
            xml = ""
            for i in range(self.NUM_MOBS):
                x = str(random.randint(-10, 10))
                z = str(random.randint(-10, 10))
                xml += '<DrawEntity x="' + x + '" y="1" z="' + z + '" type="Zombie"/>'
            return xml


        def stones():
            stone = ''
            for i in range(50):
                for j in range(50):
                    if random.randint(0,100)/100. < DENSITY:
                        stone +="<DrawBlock x='%s'  y='2' z='%s' type='bedrock' />"%(i-25,j-25)
            return stone
            
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
                        <StartTime>18000</StartTime>
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
                      drawMobs() + \
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

        for i in range(len(agent_names)):
            weapon = random.randint(0,1)

            mission_xml += '''<AgentSection mode="Survival">
                <Name>''' + agent_names[i] + '''</Name>
                <AgentStart>
                  <Placement x="''' + str(random.randint(-17, 17)) + '''" y="2" z="''' + str(
                random.randint(-17, 17)) + '''"/>
                    <Inventory>
                '''
            if(weapon == 0):
                mission_xml += '''<InventoryObject slot="0" type="wooden_sword" quantity="1"/>'''
            else:
                mission_xml += '''<InventoryObject slot="0" type="bow" quantity="1"/>
                    <InventoryObject slot="1" type="arrow" quantity="64"/>'''
                
            mission_xml += '''
                </Inventory>
            </AgentStart>
            <AgentHandlers>
                <VideoProducer>
                  <Width>512</Width>
                  <Height>512</Height>
                </VideoProducer>
                <ObservationFromFullStats/>
                <ContinuousMovementCommands turnSpeedDegs="45">
                    <ModifierList type="deny-list">
                      <command>attack</command>
                    </ModifierList>
                </ContinuousMovementCommands>
                <RewardForCollectingItem>
                  <Item type="apple" reward="10"/>
                </RewardForCollectingItem>
                <RewardForTimeTaken initialReward="0" delta="1" density="PER_TICK"/>
                <RewardForDamagingEntity>
                <Mob type="Zombie" reward="1"/>
                </RewardForDamagingEntity>
                <RewardForSendingCommand reward="-1"/>
            </AgentHandlers>
            </AgentSection>'''

        mission_xml += '''</Mission>'''
        return mission_xml


# Define the mission environment
class ClassroomEnvironment(MissionEnvironment):
    def __init__(self, action_space, mission_name, mission_xml, remotes, state_builder, role=0, recording_path=None):
        if action_space == 'discrete':
            actions = ['move 1', 'move -1', 'turn 1', 'turn -1']
        elif action_space == 'continuous':
            actions = ['move', 'turn']
        else:
            print('Unknown action space')
            sys.exit()

        self._abs_max_reward = 1000  # For reward normalization needed by some RL algorithms

        super(ClassroomEnvironment, self).__init__(mission_name, mission_xml, actions, remotes, state_builder,
                                                   role=role, recording_path=recording_path)

    # Do an action. Supports either a single discrete action or a list/tuple of continuous actions
    def step(self, action):
        if isinstance(action, list) or isinstance(action, tuple):
            assert 0 <= len(action) <= self.available_actions, \
                "action list is not valid (should be of length [0, %d[)" % (
                    self.available_actions)
        else:
            action_id = action
            assert 0 <= action_id <= self.available_actions, \
                "action %d is not valid (should be in [0, %d[)" % (action_id,
                                                                   self.available_actions)

        if isinstance(action, list) or isinstance(action, tuple):
            # For continuous action space, do the environment action(s) by the amount sent by the agent for each
            action = [self._actions[i] + ' ' + str(action[i]) for i in range(len(action))]
        else:
            # For discrete action space, do the environment action corresponding to the action id sent by the agent
            action = self._actions[action_id]
            assert isinstance(action, six.string_types)

        if isinstance(action, list):
            for i in range(len(action)):
                self._agent.sendCommand(action[i])
        else:
            if self._previous_action == 'use 1':
                self._agent.sendCommand('use 0')
            self._agent.sendCommand(action)
        self._previous_action = action
        self._action_count += 1

        self._await_next_obs()
        return self.state, sum([reward.getValue() for reward in self._world.rewards]), self.done, {}

    @property
    def abs_max_reward(self):
        return self._abs_max_reward


# Define a mission state builder
class ClassroomStateBuilder(MissionStateBuilder):
    """
    Generate RGB frame state resizing to the specified width/height and depth
    """
    def __init__(self, width, height, grayscale):
        assert width > 0, 'width should be > 0'
        assert height > 0, 'height should be > 0'

        self._width = width
        self._height = height
        self._gray = bool(grayscale)

        super(ClassroomStateBuilder, self).__init__()

    def build(self, environment):
        import time
        time.sleep(5)
        img = environment.frame

        if img is not None:
            img = img.resize((self._width, self._height))

            if self._gray:
                img = img.convert('L')
            return np.array(img)
        else:
            return np.zeros((self._width, self._height, 1 if self._gray else 3)).squeeze()

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def grayscale(self):
        return self._gray
