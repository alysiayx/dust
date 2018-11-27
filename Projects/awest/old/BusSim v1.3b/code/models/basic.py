# basicModel
'''
An agent based model so basic, a `child` made it.
'''
import numpy as np
import matplotlib.pyplot as plt


class Agent:

    def __init__(self):
        self.location = np.random.uniform(size=2)
        return

    def step(self):
        self.move()
        return

    def move(self):
        self.location += .01
        self.location %= 1
        return


class Model:

    def __init__(self, population):
        self.params = (population,)
        self.agents = list([Agent() for _ in range(population)])
        self.boundaries = np.array([[0, 0], [1, 1]])
        return

    def step(self):
        [agent.step() for agent in self.agents]
        return

    def agents2state(self, do_ravel=True):
        state = [agent.location for agent in self.agents]
        if do_ravel:
            state = np.ravel(state)
        else:
            state = np.array(state)
        return state

    def state2agents(self, state):
        for i in range(len(self.agents)):
            self.agents[i].location = state[2*i:2*i+2]
        return

    def ani(model):
        state = model.agents2state(do_ravel=False).T
        plt.clf()
        plt.plot(state[0], state[1], '.k', alpha=.5)
        plt.axis((0, 1, 0, 1))
        plt.pause(.1)
        return