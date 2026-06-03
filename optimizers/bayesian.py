from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from scipy.stats import norm
from scipy.optimize import minimize

import itertools
import random
import math

import pandas
import numpy
import sys


class BayesianOptimizer():
    """Bayesian optimizer.

    :param objective_f: Callable objective function that takes named arguments corresponding to each decision variable.  This function must
        return a float.
    :param constraint_f: List of callable constraint functions that take named arguments corresponding to each decision variable.  These
        functions must return a float.
    :param constraints: List of constraint values corresponding to each constraint function, i.e., the value which the constraint function must
        not fall below.
    :param variables: Dictionary of optimizations variables with entries in the form { <name> : (<lower bound>, <upper bound> } for continuous
        variables and { <name> : [<set of possible values>] } for discrete variables.
    :param n_init: Number of initial samples.
    :param n_iter: Maximum number of iterations to run.
    :param acquisition_f: Acquisition function.  Choices are: "ei" (expected improvement), "pi" (probability of improvement), or "ucb" (upper
        confidence bound).
    :param early_stopping: Stop after n iterations with no improvement in the objective. If set to 0, the optimization will continue until n_iter
        is reached.
    :param n_restarts: Number of restarts when training Gaussian Regressor.
    :param batch_size: Batchsize for gradient optimizer to minimize EI function.
    """

    def __init__(self,
                 objective_f: callable,
                 constraint_f: list[callable] | None,
                 constraints: list[float] | None,
                 variables: dict[str, list | tuple],
                 n_init: int,
                 n_iter: int,
                 acquisition_f: str,
                 early_stopping: int = 0,
                 n_restarts: int = 32,
                 batch_size: int = 32) -> None:
        self.objective_f = objective_f
        self.constraint_f = constraint_f
        self.constraints = constraints
        self.variables = variables
        self.n_init = n_init
        self.n_iter = n_iter
        self.n_restarts = n_restarts
        self.batch_size = batch_size
        self.acquisition_f = acquisition_f
        self.categorical_vars = {}
        self.ordinal_vars = {}
        for var, support in self.variables.items():
            if isinstance(support, tuple):
                self.ordinal_vars[var] = support
            elif isinstance(support, set):
                self.categorical_vars[var] = support
            else:
                raise Exception("Range must be a tuple or a set.")
        self.gauss_prs = []
        self.constraint_prs = []
        for var in itertools.product(*[v for v in self.categorical_vars.values()]):
            self.gauss_prs.append(GaussianProcessRegressor(
                kernel=RBF(length_scale_bounds=(1e-37, 1e37)),
                n_restarts_optimizer=self.n_restarts,
                normalize_y=True,
            ))
            if self.constraint_f is not None:
                self.constraint_prs.append(GaussianProcessRegressor(
                    kernel=RBF(length_scale_bounds=(1e-37, 1e37)),
                    n_restarts_optimizer=self.n_restarts,
                ))
        self.early_stopping = early_stopping

    def _get_expected_improvement(self, x_new, gpr_idx):
        # First get estimate from Gaussian surrogate
        mean_y_new, sigma_y_new = self.gauss_prs[gpr_idx].predict(np.array([x_new]), return_std=True)
        sigma_y_new = sigma_y_new.reshape(-1,1)
        #print(mean_y_new)
        #print(sigma_y_new)
        if sigma_y_new == 0.0:
            return 0.0
        #mean_c_new, sigma_c_new = self.constraint_pr.predict(np.array([x_new]), return_std=True)
        #pf = norm.cdf(self.constraint, loc=mean_c_new, scale=sigma_c_new)
        
        
        mean_y = self.gauss_pr.predict(self.x_init)
        max_mean_y = np.max(mean_y)
        z = (mean_y_new - max_mean_y) / sigma_y_new
        exp_imp = (mean_y_new - max_mean_y) * norm.cdf(z) + sigma_y_new * norm.pdf(z)
        return exp_imp
        #return pf * exp_imp

    def _get_probability_improvement(self, x_new, gpr_idx):
        mean_y_new, sigma_y_new = self.gauss_prs[gpr_idx].predict(np.array([x_new]), return_std=True)
        sigma_y_new = sigma_y_new.reshape(-1, 1)
        if sigma_y_new == 0.0:
            return 0.0
        
        mean_y = self.gauss_pr.predict(self.x_init)
        max_mean_y = np.max(mean_y)
        pi = (mean_y_new - max_mean_y) / sigma_y_new


        mean_c_new, sigma_c_new = self.constraint_pr.predict(np.array([x_new]), return_std=True)
        pf = norm.cdf(self.constraint, loc=mean_c_new, scale=sigma_c_new)
        return pi
        #return pf * pi

    def _get_upper_confidence_bound(self, x_new, gpr_idx):
        mean_y_new, sigma_y_new = self.gauss_prs[gpr_idx].predict(np.array([x_new]), return_std=True)
        sigma_y_new = sigma_y_new.reshape(-1, 1)
        if sigma_y_new == 0.0:
            return 0.0

        mean_c_new, sigma_c_new = self.constraint_pr.predict(np.array([x_new]), return_std=True)
        pf = norm.cdf(self.constraint, loc=mean_c_new, scale=sigma_c_new)
        return mean_y_new + sigma_y_new
        #return pf * (mean_y_new + sigma_y_new)  


    def _acquisition_function(self, x, grp_idx):
        if self.acquisition_f == 'ei':
            return -self._get_expected_improvement(x, grp_idx).ravel()
        elif self.acquisition_f == 'pi':
            return -self._get_probability_improvement(x, grp_idx).ravel()
        elif self.acquisition_f == 'ucb':
            return -self._get_upper_confidence_bound(x, grp_idx).ravel()


    def _initialize(self):
        self.x_prev = []
        self.y_prev = []
        self.c_prev = []
        for n in range(self.n_init):
            x = {}
            for var, support in self.variables:
                if isinstance(support, tuple):
                    x[var] = random.random(*support)
                elif isinstance(support, set):
                    x[var] = random.choice(support)
            self.x_prev.append(x)
            self.y_prev.append(self.objective_f(**x))
            if self.constraints is not None:
                self.c_prev.append(self.constraint_f(**x))


    def _get_next_probable_point(self, x, y, grp_id):
        min_ei = float(sys.maxsize)
        x_optimal = None
        scale = 1
        for x_start in (np.random.random((self.batch_size, x.shape[1])) * scale):
            #response = minimize(fun=self._acquisition_function, x0 =x_start, method='L-BFGS-B')
            response = minimize(fun=self._acquisition_function, x0=x_start, args=(grp_id,), method='CG')
            if response.fun < min_ei:
                min_ei = response.fun
                x_optimal = response.x
        return x_optimal, min_ei

    def _extend_prior_with_posterior_data(self, x, y, c):
        self.x_init = np.append(self.x_init, x, axis=0)
        self.y_init = np.append(self.y_init, np.array(y), axis=0)
        self.c_init = np.append(self.c_init, np.array(c), axis=0)


    def _hist_to_numpy(self) -> tuple[list[numpy.array], list[numpy.array], list[numpy.array]]:
        x = []
        y = []
        for cat in itertools.product(*[v for v in self.categorical_vars.values()]):
            x_cat = []
            y_cat = []
            for prevx, prevy, prevc in zip(self.x_prev, self.y_prev):
                if all([cat[i] == prevx[c] for i, c in enumerate(self.categorical_vars.keys())]):
                    x_cat_n = []
                    y_cat_n = []
                    for idx, var in enumerate(self.ordinal_vars.keys()):
                        x_cat_n.append(prevx[var])
                        y_cat_n.append(prevy)
                    x_cat.append(x_cat_n)
                    y_cat.append(y_cat_n)
            x.append(numpy.array(x_cat))
            y.append(numpy.array(y_cat))
        c = []
        # TODO: Handle constraints
        return x, y, c

    def _x_next_to_dict(x_next, cat):
        cat_vals = list(itertools.product(*[v for v in self.categorical_vars.values()]))[cat]
        x = {}
        for idx, var in self.categorical_vars.keys():
            x[var] = cat_vals[idx]
        for idx, item in self.ordinal_vars.items():
            k, v = item
            x[k] = min(max(x[idx], k[0]), k[1])
        return x

    def _get_random_x(cat):
        cat_vals = list(itertools.product(*[v for v in self.categorical_vars.values()]))[cat]
        x = {}
        for idx, var in self.categorical_vars.keys():
            x[var] = cat_vals[idx]
        for var, support in self.ordinal_vars.items():
            x[var] = random.random(*support)
        return x

    def optimize(self):
        self._initialize()
        y_max = max(self.y_prev)
        y_max_ind = self.y_prev.index(y_max)
        optimal_x = self.x_prev[y_max_ind]
        #optimal_ei = None
        n_iter_no_improvement = 0
        for i in range(self.n_iter):
            # TODO: Handle Constraints
            x, y, _ = self._hist_to_numpy()
            ucbs = []
            x_nxts = []
            y_nxts = []
            for cat, data in enumerate(zip(x, y)):
                x_cat, y_cat = data
                if len(x_cat) > 0:
                    x_scaler = MinMaxScaler((-1, 1))
                    x_scaler.fit(x_cat)
                    y_scaler = MinMaxScaler((-1, 1))
                    y_scaler.fit(y_cat)
                    self.gauss_prs[cat].fit(x_scaler.transform(self.x_cat), y_scaler.transform(self.y_cat))
                    #self.constraint_pr.fit(scaler.transform(self.x_init), self.c_init <= self.constraint)
                    x_next, ei = self._get_next_probable_point(x_scaler.transform(self.x_cat), y_scaler.transform(self.y_cat), cat)
                    x_next = scaler.inverse_transform(x_next.reshape(1, -1))
                    x_nxts.append(self._x_next_to_dict(x_next, cat))
                    ucbs.append(ei + math.sqrt(2 * math.log(len(x_cat)) / len(self.x_prev)))
                else:
                    x_nxts.append(self._get_random_x(cat))
                    ucbs.append(float('inf'))
            # Choose bandit arm to play
            nxt_idx = ucbs.index(max(ucbs))
            self.x_prev.append(x_nxts[nxt_idx])
            self.y_prev.append(self.objective_f(**x_nxts[nxt_idx]))
            #self._extend_prior_with_posterior_data(x_next, y_next, c_next)

            print(f'Current y: {y_max}')
            
            if self.y_prev[-1] > y_max: #and c_next <= self.constraint:
                y_max = y_prev[-1]
                optimal_x = x_prev[-1]
                #optimal_ei = ei
                n_iter_no_improvement = 0

            if n_iter_no_improvement > self.early_stopping and self.early_stopping > 0:
                break


        return optimal_x, y_max