---
layout: default
title: Status
---

### Summary

Our project aims to create a multi-agent environment in Minecraft where agents are spawned in a PvP deathmatch scenario. Each agent will be given the observation space from Malmo, and its goal is to specify an action output that maintains its survival in the world and eliminates other players in the world. Each AI agent will spawn in a random tile and be given a random weapon between bow or sword. Each agent will also be given the weapon of the opponent so that they are able to develop weapon specific strategies for each.

### Approach

We use Deep Q-Learning (DQN), which is essentially using a neural network to approximate Q-values. In regular Q-learning, (state,action) pairs are mapped to Q-values, or estimated rewards, using the following equation to create an accurate mapping. The equation essentially updates each pair by a reward and by an estimation of future reward multiplied by a discount factor $\gamma$.

$$ Q(s,a) = r(s,a) + \gamma max_aQ(s',a')$$

In DQN, this same goal is achieved but we use a neural network to approximate the Q equation, using a Q network and a Target network, which are identical in structure and purpose, the difference being that the Target network is updated far less frequently to prevent changes from affecting states in the immediate future.

In Malmo, we use this in a 50 by 50 grid in Malmo, blocked by a fence, with randomly generated blocks filled with mobs and other agents. The reward is -5 for each timetaken, 1000 for killing a mob, and -1000 for dying.


### Evaluation

The goal for qualitative evaluation is simply to have multiple agents with complex strategies fighting each other. For example, if an agent is using the bow and arrow, we would like to see some form of kiting away from the enemy, while an agent using a sword might be using the obstacles to get closer to the other agent. 

For quantitative evaluation, we could set the agents into a scene with mobs, and compare the number of mobs killed and health taken compared to baseline models and human input, as well as having the usual evaluation metrics such as MSE, cross entropy, reward, etc. to evaluate how well the network is performing.


### Remaining Goals

The current model used by the DQN is simply a few LSTM blocks chained. We would like to experiment with making the neural network more complicated, hopefully being able to factor in our original plan of forcing the network to learn multiple goals such as an updated world map or guessing the location of the mobs.

These would likely prompt the agent to develop more complicated strategies. If we have additional time, we could also try using the DDPG and comparing the two networks performances. 

The largest obstacle will likely be training environment, as we had a lot of difficulty setting up Malmo on AWS. If needed to, we can simply dockerize this entire repository and run it on GPUs through docker. Aside from that, it may be difficult obtaining alternative data (world map, mob locations). One possible idea may be using an observer agent that has a birds eye view of the map, and is able to communicate this to the agent as a for of ground truth.



### Video

Video shows agent training DQN. We have not set up AWS so it has not finished training, but this is after 2000 iterations.

<iframe width="560" height="315" src="https://www.youtube.com/embed/q-LZeefbmKQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>


### Resources
1. https://github.com/petrosgk/MalmoRL
2. https://github.com/keras-rl/keras-rl
   