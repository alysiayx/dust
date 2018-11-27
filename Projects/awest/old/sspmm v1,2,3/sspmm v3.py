# sspmm.py
'''
StationSim (aka Mike's model) converted into python.

Todos:
multiprocessing
kd-tree close enough
profile functions
'''
import numpy as np
from copy import deepcopy
import matplotlib.pyplot as plt


# A simple error function used for debugging.
def error(text='Self created error.'):
    from sys import exit
    print()
    exit(text)
    return


# An approximate method for calculating the p=2-norm.
sqrt_2 = 1 / np.sqrt(2)
def cheap_norm(array, axis=None):
    n = np.sum(np.abs(array), axis) * sqrt_2
    return n


class KD_Tree:

    def __init__(self, k):
        self.k = k
        return

    def build(self, points, depth=0):
        n = len(points)
        if n:
            axis = depth % self.k
            sorted_points = sorted(points, key=lambda point: point[axis])
            tree = {
                'point': sorted_points[n // 2],
                'left': self.build(sorted_points[:n // 2], depth + 1),
                'right': self.build(sorted_points[n // 2 + 1:], depth + 1),
            }
        else:
            tree = None
        return tree

    def search_square(self, tree, point, depth=0, best=None):
        if tree is not None:
            axis = depth % self.k
            next_best = None
            next_branch = None
            if best is None or self.distance(point, tree['point']) < self.distance(point, best):
                next_best = tree['point']
            else:
                next_best = best
            if point[axis] < tree['point'][axis]:
                next_branch = tree['left']
            else:
                next_branch = tree['right']
            best = self.search_square(next_branch, point, depth + 1, next_best)
        return best

    def search_radius(self, tree, point, depth=0):
        if tree is None:
            best = None
        else:
            axis = depth % self.k
            next_branch = None
            opposite_branch = None
            if point[axis] < tree['point'][axis]:
                next_branch = tree['left']
                opposite_branch = tree['right']
            else:
                next_branch = tree['right']
                opposite_branch = tree['left']
            best = self.closer_distance(point, self.search_radius(next_branch, point, depth + 1), tree['point'])
            if self.distance(point, best) > abs(point[axis] - tree['point'][axis]):
                best = self.closer_distance(point, self.search_radius(opposite_branch, point, depth + 1), best)
        return best

    def distance(self, p1, p2):
        d = cheap_norm(p1 - p2)
        return d

    def closer_distance(self, pivot, p1, p2):
        if p1 is None:
            p = p2
        elif p2 is None:
            p = p1
        elif self.distance(pivot, p1) < self.distance(pivot, p2):
            p = p1
        else:
            p = p2
        return p


class NextRandom:
    # To find random number useage type 'random.np_', or even 'random'

    def __init__(self):
        np.random.seed(303)
        self.random_number_usage = 0
        return

    def np_uniform(self, high=1, low=0, shape=1):
        r = np.random.random(shape)
        r = r * (high - low)
        self.random_number_usage += np.size(r)
        return r

    def np_gaussian(self, mu=0, sigma=1, shape=1):
        r = np.random.standard_normal(shape)
        r = r * sigma**2 + mu
        self.random_number_usage += np.size(r)
        return r

    def np_integer(self, high=1, low=0, shape=1):
        r = np.random.randint(low, high + 1, shape)
        self.random_number_usage += np.size(r)
        return r


class Agent:

    def __init__(self, model):
        self.unique_id = model.agent_count
        model.agent_count += 1
        self.active = 0  # 0 = not started, 1 = started, 2 = finished
        # Location
        entrance = random.np_integer(model.entrances - 1)
        self.location = model.loc_entrances[entrance][0]
        # Parameters
        self.loc_desire = model.loc_exits[random.np_integer(model.exits - 1)][0]
        return

    def step(self, model):
        if self.active == 0:
            self.activate(model)
        elif self.active == 1:
            self.move(model)
            if model.do_save:
                self.save()
            self.exit_query(model)
        return

    def activate(self, model):
        self.speed_desire = max(random.np_gaussian(model.speed_desire_max), model.speed_desire_min)
        new_location = self.location
        new_location[1] += model.entrance_space * random.np_uniform(-.5, +.5)
        # Empty space to step off of 'train'
        self.separation = model.initial_separation
        if not self.collision(model, new_location):
            self.active = 1
            model.pop_active += 1
            self.location = new_location
            self.separation = model.separation
            # Save
            if model.do_save:
                self.start_time = model.time
                self.history_loc = []
        return

    def move(self, model):
        '''
        Description:
            This mechanism moves the agent. It checks certain conditions for collisions at decreasing speeds.
            First check for direct new_location in the desired direction.
            Second check for a new_location in a varied desired direction.
            Third check for a new_location with a varied current direction.

        Dependencies:
            collision - any agents in radius
                neighbourhood - find neighbours in radius
            lerp      - linear extrapolation

        Arguments:
            self

        Returns:
            new_location
        '''
        # Decreasing Speeds
        speeds = np.linspace(self.speed_desire, model.speed_min, 15)
        for speed in speeds:
            new_location = self.lerp(self.loc_desire, self.location, speed)
            if not self.collision(model, new_location):
                break
        # Wiggle
        if speed == model.speed_min:
            new_location = self.location + random.np_integer(low=-1, high=+1, shape=2)
        # Boundary check
        within_bounds = all(model.boundaries[0] <= new_location) and all(new_location <= model.boundaries[1])
        if not within_bounds:
            new_location = np.clip(new_location, model.boundaries[0], model.boundaries[1])
        # Move
        self.location = new_location
        return

    def collision(self, model, new_location):
        '''
        Description:
            Determine whether or not there is another object at this location.
            Requires get neighbour from mesa?

        Dependencies:
            neighbourhood - find neighbours in radius

        Arguments:
            model.boundaries
                ((f, f), (f, f))
                A pair of tuples defining the lower limits and upper limits to the rectangular world.
            new_location
                (f, f)
                The potential location of an agent.

        Returns:
            collide
                b
                The answer to whether this position is blocked
        '''
        within_bounds = all(model.boundaries[0] <= new_location) and all(new_location <= model.boundaries[1])
        if not within_bounds:
            collide = True
        elif self.neighbourhood(model, new_location):
            collide = True
        else:
            collide = False
        return collide

    def neighbourhood(self, model, new_location, do_kd_tree=True, just_one=True, forward_vision=True):
        '''
        Description:
            Get agents within the defined separation.

        Arguments:
            self.unique_id
                i
                The current agent's unique identifier
            self.separation
                f
                The radius in which to search
            model.agents
                <agent object>s
                The set of all agents
            new_location
                (f, f)
                A location tuple
            just_one
                b
                Defines if more than one neighbour is needed.
            forward_vision
                b
                Restricts separation radius to only infront.

        Returns:
            neighbours
                <agent object>s
                A set of agents in a region
        '''
        if model.do_kd_tree:
            location = model.kd.search_radius(model.tree, new_location)
            neighbours = self.separation < cheap_norm(location - new_location)
        else:
            neighbours = []
            for agent in model.agents:
                if agent.active == 1:
                    if forward_vision and agent.location[0] < new_location[0]:
                        distance = self.separation + 1
                    else:
                        distance = cheap_norm(new_location - agent.location)
                    if distance < self.separation and agent.unique_id != self.unique_id:
                        neighbours.append(agent)
                        if just_one:
                            break
        return neighbours

    def lerp(self, loc1, loc2, speed):
        '''
        Description:
            Linear extrapolation at a constant rate
            https://en.wikipedia.org/wiki/Linear_interpolation

        Arguments:
            loc1
                (f, f)
                Point One defining the destination position
            loc2
                (f, f)
                Point Two defining the agent position
            speed
                f
                The suggested speed of the agent

        Returns:
            loc
                (f, f)
                The location if travelled at this speed
        '''
        distance = np.linalg.norm(loc1 - loc2)
        loc = loc2 + speed * (loc1 - loc2) / distance
        return loc

    def save(self):
        self.history_loc.append(self.location)
        return

    def exit_query(self, model):
        if np.linalg.norm(self.location - self.loc_desire) < model.exit_space:
            self.active = 2
            model.pop_active -= 1
            model.pop_finished += 1
            if model.do_save:
                model.time_taken.append(model.time - self.start_time)
        return


class Model:

    def __init__(self, params):
        for key, value in params.items():
            setattr(self, key, value)
        # Batch Details
        self.time = 0
        if self.do_save:
            self.time_taken = []
        # Model Parameters
        self.boundaries = np.array([[0, 0], [self.width, self.height]])
        self.pop_active = 0
        self.pop_finished = 0
        # Initialise
        self.initialise_gates()
        self.initialise_agents()
        return

    def step(self):
        self.time += 1
        if self.pop_finished < self.pop_total and self.delay < self.time:
            self.kdtree_build()
            for agent in self.agents:
                agent.step(self)
        return

    def initialise_gates(self):
        # Entrances
        self.loc_entrances = np.zeros((self.entrances, 2))
        self.loc_entrances[:, 0] = 0
        if self.entrances == 1:
            self.loc_entrances[0, 1] = self.height / 2
        else:
            self.loc_entrances[:, 1] = np.linspace(self.height / 4, 3 * self.height / 4, self.entrances)
        # Exits
        self.loc_exits = np.zeros((self.exits, 2))
        self.loc_exits[:, 0] = self.width
        if self.exits == 1:
            self.loc_exits[0, 1] = self.height / 2
        else:
            self.loc_exits[:, 1] = np.linspace(self.height / 4, 3 * self.height / 4, self.exits)
        return

    def initialise_agents(self):
        self.agent_count = 0
        self.agents = list([Agent(self) for _ in range(self.pop_total)])
        return

    def kdtree_build(self):
        self.kd = KD_Tree(2)
        locs = []
        for agent in self.agents:
            locs.append(agent.location)
        self.tree = self.kd.build(locs)
        return

    def agents2state(self):
        state = np.ravel([agent.location for agent in self.agents])
        return state

    def state2agents(self, state):
        for i in range(len(self.agents)):
            self.agents[i].location = state[2 * i:2 * i + 2]
        return

    def batch(self):
        for i in range(self.batch_iterations):
            self.step()
            if self.do_ani:
                self.ani_agents()
            if self.pop_finished == self.pop_total:
                print('Everyone made it!')
                break
        if self.do_save:
            self.stats()
            self.plot_subplots()
        return

    def ani_agents(self):
        plt.figure(1)
        plt.clf()
        for agent in self.agents:
            if agent.active == 1:
                plt.plot(*agent.location, '.k')
        plt.axis(np.ravel(self.boundaries, 'F'))
        plt.pause(1 / 30)
        return

    def plot_subplots(self):
        _, (ax1, ax2) = plt.subplots(2)
        for agent in self.agents:
            if agent.active == 2 and agent.unique_id < 50:
                locs = np.array(agent.history_loc).T
                ax1.plot(locs[0], locs[1], linewidth=.5)
        ax1.axis(np.ravel(self.boundaries, 'F'))
        ax2.hist(self.time_taken)
        plt.show()
        return

    def stats(self):
        print()
        print('Stats:')
        print('Finish Time: ' + str(self.time))
        print('Random number usage: ' + str(random.random_number_usage))
        print('Active / Finished / Total agents: ' + str(self.pop_active) + '/' + str(self.pop_finished) + '/' + str(self.pop_total))
        print('Average time taken: ' + str(np.mean(self.time_taken)) + 's')
        return


class ParticleFilter:

    def __init__(self, Model, model_params, params):
        for key, value in params.items():
            setattr(self, key, value)
        self.time = 0
        # Models
        self.base_model = Model(model_params)
        if self.do_copies:
            self.models = list([deepcopy(self.base_model) for _ in range(self.number_of_particles)])
        else:
            self.models = list([Model(model_params) for _ in range(self.number_of_particles)])
        self.dimensions = len(self.base_model.agents2state())
        # Filter
        self.states = np.empty((self.number_of_particles, self.dimensions))
        self.weights = np.ones(self.number_of_particles)
        # Results
        if self.do_save:
            self.means = []
            self.mean_errors = []
            self.variances = []

    def step(self):
        self.predict()
        self.reweight()
        self.resample()
        if self.do_save:
            truth = self.base_model.agents2state()
            self.save(truth)
        if self.do_ani:
            self.ani()
        return

    def reweight(self):
        if self.particle_std:
            self.states += random.np_gaussian(0, self.particle_std**2, shape=self.states.shape)
        measured_state = self.base_model.agents2state()
        if self.model_std:
            measured_state += random.np_gaussian(0, self.model_std**2, shape=measured_state.shape)
        distance = np.linalg.norm(self.states - measured_state, axis=1)
        self.weights = 1 / np.fmax(distance, 1e-99)  # to avoid fp_err
        self.weights /= np.sum(self.weights)
        return

    def resample(self):
        if not self.do_neff or 2 / self.number_of_particles < np.sum(np.square(self.weights)):
            offset_partition = (np.arange(self.number_of_particles) + random.np_uniform()) / self.number_of_particles
            cumsum = np.cumsum(self.weights)
            i, j = 0, 0
            indexes = np.zeros(self.number_of_particles, 'i')
            while i < self.number_of_particles and j < self.number_of_particles:  # error
                if offset_partition[i] < cumsum[j]:
                    indexes[i] = j
                    i += 1
                else:
                    j += 1
            self.states[:] = self.states[indexes]
            self.weights[:] = self.weights[indexes]
        return

    def predict(self):
        self.base_model.step()
        for particle in range(self.number_of_particles):
            if self.time:
                self.models[particle].state2agents(self.states[particle])
            self.models[particle].step()
            self.states[particle] = self.models[particle].agents2state()
        self.time += 1
        return

    def save(self, truth_state):
        mean = np.average(self.states, weights=self.weights, axis=0)
        variance = np.average((self.states - mean)**2, weights=self.weights, axis=0)
        if self.do_save:
            self.means.append(mean[:])
            self.mean_errors.append(np.linalg.norm(mean - truth_state, axis=0))
            self.variances.append(np.average(variance))
        return

    def ani(self):
        plt.figure(1)
        plt.clf()
        for agent in self.base_model.agents:
            if agent.active == 1:
                plt.plot(*agent.location, '.k')
        particle = 0
        markersizes = self.weights
        markersizes *= 4 / np.std(markersizes)     # revar
        markersizes += 4 - np.mean(markersizes)    # remean
        markersizes = np.clip(markersizes, .5, 8)  # clip
        for model in self.models:
            for agent in model.agents[:4]:
                if agent.active == 1:
                    locs = np.array([self.base_model.agents[agent.unique_id].location, agent.location]).T
                    plt.plot(*locs, '-k', alpha=.1, linewidth=.3)
                    plt.plot(*agent.location, '.r', alpha=.3, markersize=markersizes[particle])
            particle += 1
        plt.axis(np.ravel(self.base_model.boundaries, 'F'))
        plt.pause(1 / 30)
        return


if __name__ == '__main__':
    random = NextRandom()
    model_params = {
        'width': 200,
        'height': 100,
        'pop_total': 300,
        'entrances': 3,
        'entrance_space': 1,
        'exits': 2,
        'exit_space': 2,
        'speed_min': .1,
        'speed_desire_min': .5,
        'speed_desire_max': 2,
        'initial_separation': 1,
        'separation': 5,
        'delay': 2,
        'batch_iterations': 50,
        'do_save': False,
        'do_ani': False,
        'do_kd_tree': True
    }
    if not True:  # Run the model
        Model(model_params).batch()
    else:  # Run the particle filter
        model_params['do_save'] = False
        filter_params = {
            'number_of_particles': 10,
            'particle_std': 0,
            'model_std': 0,
            'do_copies': True,
            'do_neff': False,
            'do_save': False,
            'do_ani': True
        }
        pf = ParticleFilter(Model, model_params, filter_params)
        for _ in range(model_params['batch_iterations']):
            pf.step()