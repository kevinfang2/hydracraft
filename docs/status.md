---
layout: default
title: Status
---
[Video](https://www.youtube.com/watch?v=9Z33M762EtU)

##Summary

Our project aims to create a multi-agent environment in Minecraft where agents are spawned in a PvP deathmatch scenario. Each agent will be given the observation space from Malmo, and its goal is to specify an action output that maintains its survival in the world and eliminates other players in the world. Each AI agent will have a designated weapon, either a bow, sword, trident, or crossbow, and will learn how to most effectively use each weapon. We are interested in seeing how each of the weapons compare to each other in learned behavior.

##Approach

We used a Proximal Policy Optimization (PPO) algorithm using the implementation from Ray-rllib. We had an action space of size 1 x 3 and an observation space of 11 x 11 blocks centered around the agent with 0 being air, 1 being a stone block and 99 being the other agent. For this example we used a single policy that governs each agent, in the future we are planning on experimenting with multiple policies and other algorithms.

For our environment, we use a 22 by 22 grid in Malmo, blocked by a stone wall, with a singular other agents. The reward is -1 for dying and 0.1 for every heart of damage inflicted to the other agent. After running it overnight with over 35000 steps our results looked like this.

![](C:\Users\Killian\Malmo\Results\returns_overnight.png)
##Evaluation

The goal for qualitative evaluation is simply to have multiple agents with complex strategies fighting each other. For example, if an agent is using the bow and arrow, we would like to see some form of kiting away from the enemy, while an agent using a sword might be using the obstacles to get closer to the other agent. We can analyze the overall performance of all agents against each other, using statistics such as time survived, kills secured, damage dealt, in addition to the eye test to analyze a given agent weapon strategy profile.

For quantitative evaluation, we could set the agents into a scene with mobs, and compare the number of mobs killed and health taken compared to baseline models and human input, as well as having the usual evaluation metrics such as MSE, cross entropy, reward, etc. to evaluate how well the network is performing.

##Remaining Goals

One remaining goal that we still have to implement is randomized obstacles and buildings within the arena. Obstacles and buildings will allow more complexity and variation to be learned by the agents. Obstacles allow agents with short-range weapons to learn to use cover to avoid the arrows and approach the agent with more health while long-range agents will be able to use buildings to get a height advantage over the agents.

Another goal, that has yet to be tried for the sake of simplicity, is increasing the number of agents to at least 4. This is not something hard to implement rather we would like to ensure our algorithms work well with 2 agents before increasing the complexity. A larger agent space would result in more complex quantitative statistics, which we have not figured out how to measure yet. Furthermore, we still need to add more measurements in general, such as average distance from agents, average steps alive, average damage taken, average damage dealt, and accuracy have yet to be implemented outputs.

Our final goal is to increase the amount of input that each agent trains uponOur stretch goal is to explore multi-modal/multi-input models, where we use several different input types/ additional tokens, in order to coerce more complete or complex strategies. Of course, such a result would be hard to quantify in terms of improvement, especially if we attempt to force concepts such as map awareness explicitly into the agent.

The largest obstacle will likely be training environment, as we had a lot of difficulty setting up Malmo on AWS. If needed to, we can simply dockerize this entire repository and run it on GPUs through docker. Aside from that, it may be difficult obtaining alternative data (world map, mob locations). One possible idea may be using an observer agent that has a birds eye view of the map, and is able to communicate this to the agent as a for of ground truth.

##Video
Video shows agent training PPO. The clip is a just initialized run of the project while the clip at the end is a clip after it has been trained overnight for 35000 steps.


##Resources
https://github.com/petrosgk/MalmoRL
https://github.com/keras-rl/keras-rl
https://github.com/microsoft/malmo
https://github.com/ray-project/ray