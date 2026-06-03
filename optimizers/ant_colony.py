import numpy


class AntColonyOptimizer(object):
    """
    Ant colony optimizer.

    graph = transition matrix
    goal = index of goal nodes
    f_obj = objective function to evaluate on ant's subgraph
    n_ants - number of ants
    alpha = pheromone influence parameter
    beta = distance influence parameter
    rho = pheromone decay parameter
    tau_max = maximum pheromone an ant can lay down
    """

    def __init__(self, graph, goal, f_obj, n_ants, alpha, beta, rho, tau_max):
        self.graph = graph
        self.goal = goal
        self.f_obj = f_obj
        self.n_ants = n_ants
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.tau_max = tau_max
        self.tau = self.graph.copy()
        self.best = None
        self.converged = False
        self.iters = 0

    def tick(self):
        # Edge Selection
        pxy = self.tau ** self.alpha * self.graph ** self.beta
        print(pxy)
        ants = []
        for ant in range(self.n_ants):
            visited = []
            node = 0
            while node not in self.goal:
                node = numpy.random.choice(
                    list(range(pxy[node, :].size)),
                    p=pxy[node, :] / numpy.sum(pxy[node, :])
                ).item()
                visited.append(node)
            ants.append(visited)

        # Check for convergence (all ants on same path)
        self.converged = True
        for idx in range(1, len(ants)):
            if ants[idx - 1] != ants[idx]:
                self.converged = False
                break

        # Evaluate Subgraphs
        print(f"### ITER {self.iters} ###")
        rewards = []
        for ant in ants:
            r, args = self.f_obj(ant)
            r = -r
            if self.best is None or r > self.best[0]:
                self.best = (r, ant, args)
            print(f"Ant Reward: {r}")
            rewards.append(r)
        rewards = numpy.array(rewards)
        rewards = rewards - numpy.amin(rewards)
        rewards = rewards / numpy.amax(rewards)
        
        # Pheromone Update
        dtau = []
        for ant, reward in zip(ants, rewards):
            sg = numpy.zeros(pxy.shape)
            prev = 0
            for node in ant:
                sg[prev, node] = 1
                prev = node
            dtau.append(reward * sg)
        self.tau = (1 - self.rho) * pxy + sum(dtau)
        self.iters += 1
        return

    def optimize(self):
        while not self.converged:
            self.tick()
        return self.best