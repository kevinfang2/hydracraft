---
layout: default
title: Proposal
---

# Proposal

## Summary
Our project aims to create a multi-agent environment in Minecraft where agents are spawned in a PvP deathmatch scenario. Each agent will be given the image output of their in game character (similar to what a human player gets in the game), and its goal is to specify an action output that maintains its survival in the world and eliminates other players in the world. Each AI agent will spawn in a random tile and be given a random weapon.

We plan to experiment with both image and video input. Video will be a stack of images to create a sense of history within the model. We will encourage agents to explore the world and have the world’s history be a factor in decision making.

Things to consider:
- Item balance -> how many weapons we want them to learn.
- World Balance -> Are there going to be obstacles within the generated world and if so how does it impact game balance as a whole.
- World size -> we want to encourage aggression, and need each player to be within each other most of the time.
- Number of agents -> start with 2 and move up.

Possible applications could be having more interesting AI bots as enemies, as well as bots that are able to consider other agents in an adversarial environment.

## AI/ML algorithms


We envision using several ML algorithms to implement this: first we would an image/video classifier (image/video -> task) to extract features and then these features will be inputted into a multi-headed network comprised of reinforcement learning heads (dqn, ddqn).

### Image/Video -> Task 
This is the most straightforward approach. This would be essentially a classification task (use Resnet/ I3D, etc.). We will start with training this first, then focus on implementing various reinforcement learning methods (DQN, DDQN, etc.).

### HydraNet (Image/Video -> (world grid, player information, etc) -> task)
In this approach, the goal is to have a multiheaded network where there are many heads involving smaller tasks, with a final head for deciding the action of the agent, all with a shared feature extractor.

For the smaller tasks, we would use supervised learning. An example would be predicting a world grid from the video/image input. For this specific task, we could use the data from assignment1.

After training these smaller tasks, we can introduce reinforcement learning to predict an action for the agent. During training, we would freeze the feature extractor and the other subtasks, and use them all as input. If there are already existing bots in Minecraft, we can experiment with placing them in the environment against our bots. This way, our agents don't have to learn how to play while all being beginners.

We also need to decide if there are any intermediary rewards we would like to assign during the task training network. In a 2 player context, once the other player dies, we can assign a 1 to the winning player, and a -1 to the non winning player. The more players we add, the more complicated this becomes. Should we factor things like player survival, inflicting damage on players, survival time, and takedowns? 
 


## Evaluation Plan
It’s hard to assign concrete metrics in how well our task prediction model will work. Unlike chess, there are not established ELO criteria and established game knowledge that we can play off of. If we are able to find existing Minecraft PvP bots, we can use them as a point of comparison. If not, the performance of the final task prediction model will largely be anecdotal. However, for our hydranet architecture plan, we can use ground truth and evaluation metrics such as MSE, cross entropy, etc. to evaluate how well intermediary values perform.

There are a few sanity cases we can use to verify that our project works. One such case is to have one area where an agent is pitted against an unresponsive character. The agent should be able to easily dispatch the unresponsive character showing that the agent understands how to fight. This case can be expanded to areas with more than one unresponsive character. Some moonshot cases would be an arena full of obstacles with any number of agents fighting each other at one time to see who would win.

## Appointment with the Instructor
October 19, Tuesday, 2pm