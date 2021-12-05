TRACK_WIDTH = 30
TRACK_BREADTH = 30
TRACK_HEIGHT = 30
TIMELIMIT = 25000
MAX_COMMANDS = 100
WEAPON_MAPPING = {}
WEAPONS = {}
DENSITY = 0
BUILDING = 0

# 0 is sword, 1 is bow
AGENT_INFO = {
    'sword': 0,
    'bow': 1,
    'axe' : 2,
    'pickaxe' : 3
}

NUM_AGENTS = len(AGENT_INFO)

obs_size = 11
ARENA_SIZE = 11
ARENA_HEIGHT = 2