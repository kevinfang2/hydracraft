import math
import random

TRACK_WIDTH = 30
TRACK_BREADTH = 30
TRACK_HEIGHT = 30
TIMELIMIT = 25000
WEAPON_MAPPING = {}
WEAPONS = {}

def getWeapon(agentName):
    '''Returns the weapon of agent
    arguments:
    - agentName

    Returns id of weapon with following mapping
    weapons:
        - 0 for sword
        - 1 for bow arrow
    '''
    if agentName not in WEAPON_MAPPING.keys():
        return agentName
    return WEAPON_MAPPING[agentName]

def create_mission(agent_info, trackw=TRACK_WIDTH, trackb=TRACK_BREADTH, trackh=TRACK_HEIGHT, timelimit=TIMELIMIT):
    '''Creates the xml for a given encounter:
    arguments:
        - trackw: the width of observation grid
        - trackb: the breadth of observation grid
        - entity: the mob type to spawn
        - timelimit: the time limit in ms for the encounter'''
    missionXML='''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
              <About>
                <Summary>Fighting Simulator</Summary>
                <Description>Defeat Enemy to Continue!</Description>
              </About>
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
                        '''
                        <DrawBlock x='0'  y='2' z='0' type='air' />
                        <DrawBlock x='0'  y='1' z='0' type='stone' />
                    </DrawingDecorator>
                    <ServerQuitWhenAnyAgentFinishes description="server sees murder happen"/>
                </ServerHandlers>
            </ServerSection>
    '''

    for name,weapon in agent_info.items():
        missionXML += '''<AgentSection mode="Survival">
        <Name>''' + name + '''</Name>
        <AgentStart>
          <Placement x="''' + str(random.randint(-17,17)) + '''" y="2" z="''' + str(random.randint(-17,17)) + '''"/>
            <Inventory>
          '''
        if(weapon == 0):
            missionXML += '''<InventoryObject slot="0" type="wooden_sword" quantity="1"/>'''
        else:
            missionXML += '''<InventoryObject slot="1" type="bow" quantity="1"/>
                <InventoryObject slot="2" type="arrow" quantity="64"/>'''
        
        missionXML += '''
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
    missionXML += '</Mission>'
    return missionXML
