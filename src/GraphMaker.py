import numpy as np
import ast
from matplotlib import pyplot as plt
log_frequency = 100

with open('returns.txt', 'r') as f:
    returns = f.readlines()
    steps = []
    scores = []
    jumps = []
    distance = []
    attacks = []
    hits = []
    for i in returns:
        temp = i.strip().split('\t')
        steps.append(int(temp[0]))
        scores.append(ast.literal_eval(temp[1]))
        jumps.append(ast.literal_eval(temp[2]))
        distance.append(ast.literal_eval(temp[3]))
        attacks.append(ast.literal_eval(temp[4]))
        hits.append(ast.literal_eval(temp[5]))
    box = np.ones(log_frequency) / log_frequency
    sword_scores = []
    bow_scores = []
    axe_scores = []
    pickaxe_scores = []
    for i in scores:
        sword_scores.append(i['sword'])
        bow_scores.append(i['bow'])
        axe_scores.append(i['axe'])
        pickaxe_scores.append(i['pickaxe'])
    returns_smooth_sword = np.convolve(sword_scores, box, mode='same')
    returns_smooth_bow = np.convolve(bow_scores, box, mode='same')
    returns_smooth_axe = np.convolve(axe_scores, box, mode='same')
    returns_smooth_pickaxe = np.convolve(pickaxe_scores, box, mode='same')
    plt.clf()
    plt.plot(steps, returns_smooth_sword, label='Sword')
    plt.plot(steps, returns_smooth_bow, label='Bow')
    plt.plot(steps, returns_smooth_axe, label='Axe')
    plt.plot(steps, returns_smooth_pickaxe, label='Pickaxe')
    plt.title('Scores')
    plt.ylabel('Return')
    plt.xlabel('Steps')
    plt.legend()
    plt.savefig('returnScores.png')


    sword_jumps = []
    bow_jumps = []
    axe_jumps = []
    pickaxe_jumps = []
    for i in jumps:
        sword_jumps.append(i['sword'])
        bow_jumps.append(i['bow'])
        axe_jumps.append(i['axe'])
        pickaxe_jumps.append(i['pickaxe'])
    returns_smooth_sword = np.convolve(sword_jumps, box, mode='same')
    returns_smooth_bow = np.convolve(bow_jumps, box, mode='same')
    returns_smooth_axe = np.convolve(axe_jumps, box, mode='same')
    returns_smooth_pickaxe = np.convolve(pickaxe_jumps, box, mode='same')

    sword_dist = []
    bow_dist = []
    axe_dist = []
    pickaxe_dist = []
    for i in distance:
        sword_dist.append(i['sword'])
        bow_dist.append(i['bow'])
        axe_dist.append(i['axe'])
        pickaxe_dist.append(i['pickaxe'])

    true_sword_dist = []
    for i in range(len(sword_dist)):
        if i == 0:
            true_sword_dist.append(sword_dist[i])
        else:
            true_sword_dist.append(sword_dist[i]-sword_dist[i-1])

    true_bow_dist = []
    for i in range(len(bow_dist)):
        if i == 0:
            true_bow_dist.append(bow_dist[i])
        else:
            true_bow_dist.append(bow_dist[i] - bow_dist[i - 1])

    true_axe_dist = []
    for i in range(len(axe_dist)):
        if i == 0:
            true_axe_dist.append(axe_dist[i])
        else:
            true_axe_dist.append(axe_dist[i] - axe_dist[i - 1])

    true_pickaxe_dist = []
    for i in range(len(pickaxe_dist)):
        if i == 0:
            true_pickaxe_dist.append(pickaxe_dist[i])
        else:
            print(pickaxe_dist[i])
            print(pickaxe_dist[i - 1])
            true_pickaxe_dist.append(pickaxe_dist[i] - pickaxe_dist[i - 1])

    returns_dist_smooth_sword = np.convolve(true_sword_dist, box, mode='same')
    returns_dist_smooth_bow = np.convolve(true_bow_dist, box, mode='same')
    returns_dist_smooth_axe = np.convolve(true_axe_dist, box, mode='same')
    returns_dist_smooth_pickaxe = np.convolve(true_pickaxe_dist, box, mode='same')
    plt.clf()
    plt.plot(steps, returns_smooth_sword, label='Sword Jumps')
    plt.plot(steps, returns_smooth_bow, label='Bow Jumps')
    plt.plot(steps, returns_smooth_axe,label='Axe Jumps')
    plt.plot(steps, returns_smooth_pickaxe, label='Pickaxe Jumps')
    plt.title('Jumps')
    plt.ylabel('Return')
    plt.xlabel('Steps')
    plt.legend()
    plt.savefig('returnJump.png')

    plt.clf()
    plt.plot(steps, returns_dist_smooth_sword, label='Sword Distance')
    plt.plot(steps, returns_dist_smooth_bow, label='Bow Distance')
    plt.plot(steps, returns_dist_smooth_axe, label='Axe Distance')
    plt.plot(steps, returns_dist_smooth_pickaxe, label='Pickaxe Distance')
    plt.title('Distance')
    plt.ylabel('Return')
    plt.xlabel('Steps')
    plt.legend()
    plt.savefig('returnDist.png')


    sword_jumps = []
    bow_jumps = []
    axe_jumps = []
    pickaxe_jumps = []
    for i in hits:
        sword_jumps.append(i['sword'])
        bow_jumps.append(i['bow'])
        axe_jumps.append(i['axe'])
        pickaxe_jumps.append(i['pickaxe'])
    returns_smooth_sword = np.convolve(sword_jumps, box, mode='same')
    returns_smooth_bow = np.convolve(bow_jumps, box, mode='same')
    returns_smooth_axe = np.convolve(axe_jumps, box, mode='same')
    returns_smooth_pickaxe = np.convolve(pickaxe_jumps, box, mode='same')

    sword_dist = []
    bow_dist = []
    axe_dist = []
    pickaxe_dist = []
    for i in attacks:
        sword_dist.append(i['sword'])
        bow_dist.append(i['bow'])
        axe_dist.append(i['axe'])
        pickaxe_dist.append(i['pickaxe'])

    true_sword_dist = []
    for i in range(len(sword_dist)):
        if i == 0:
            true_sword_dist.append(sword_dist[i])
        else:
            true_sword_dist.append(sword_dist[i]-sword_dist[i-1])

    true_bow_dist = []
    for i in range(len(bow_dist)):
        if i == 0:
            true_bow_dist.append(bow_dist[i])
        else:
            true_bow_dist.append(bow_dist[i] - bow_dist[i - 1])

    true_axe_dist = []
    for i in range(len(axe_dist)):
        if i == 0:
            true_axe_dist.append(axe_dist[i])
        else:
            true_axe_dist.append(axe_dist[i] - axe_dist[i - 1])

    true_pickaxe_dist = []
    for i in range(len(pickaxe_dist)):
        if i == 0:
            true_pickaxe_dist.append(pickaxe_dist[i])
        else:
            true_pickaxe_dist.append(pickaxe_dist[i] - pickaxe_dist[i - 1])

    returns_dist_smooth_sword = np.convolve(true_sword_dist, box, mode='same')
    returns_dist_smooth_bow = np.convolve(true_bow_dist, box, mode='same')
    returns_dist_smooth_axe = np.convolve(true_axe_dist, box, mode='same')
    returns_dist_smooth_pickaxe = np.convolve(true_pickaxe_dist, box, mode='same')
    plt.clf()
    plt.plot(steps, returns_smooth_sword, label='Sword Jumps')
    plt.plot(steps, returns_smooth_bow, label='Bow Jumps')
    plt.plot(steps, returns_smooth_axe, label='Axe Jumps')
    plt.plot(steps, returns_smooth_pickaxe, label='Pickaxe Jumps')
    plt.title('Hits')
    plt.ylabel('Return')
    plt.xlabel('Steps')
    plt.legend()
    plt.savefig('returnHits.png')

    plt.clf()
    plt.plot(steps, returns_dist_smooth_sword, label='Sword Distance')
    plt.plot(steps, returns_dist_smooth_bow, label='Bow Distance')
    plt.plot(steps, returns_dist_smooth_axe, label='Axe Distance')
    plt.plot(steps, returns_dist_smooth_pickaxe, label='Pickaxe Distance')
    plt.title('Attacks')
    plt.ylabel('Return')
    plt.xlabel('Steps')
    plt.legend()
    plt.savefig('returnAttacks.png')