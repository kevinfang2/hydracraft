#!/usr/bin/env python
# Please ensure that you have a Minecraft client running on port 10000
# by doing :
# $MALMO_MINECRAFT_ROOT/launchClient.sh -port 10000

import marlo
import time

client_pool = [('127.0.0.1', 10000)]
join_tokens = marlo.make('MarLo-FightArena-v0',
        params={
            "client_pool": client_pool,
            "videoResolution" : [800, 600],
            "recordDestination": "test.tgz",
            "recordRewards": True,
            "client_pool" : client_pool,
            "recordMP4" : [30,30]
            })
        # As this is a single agent scenario,

# there will just be a single token
def run_agent(join_token):
    env = marlo.init(join_token)
    frame = env.reset()
    done = False
    while not done:
        _action = env.action_space.sample()
        obs, reward, done, info = env.step(_action)
        time.sleep(0.1)
        print("reward:", reward)
        print("done:", done)
        print("info", info)


for _join_token in join_tokens:
    run_agent(_join_token)
