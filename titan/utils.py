import random
from functools import wraps
from typing import TypeVar, Optional, Collection, Union

import networkx as nx  # type: ignore

from . import distributions
from .parse_params import ObjMap


def get_check_rand_int(seed: int) -> int:
    """
    Check the value passed of a seed, make sure it's an int, if 0, get a random seed

    args:
        seed: integer to check or replace with a seed

    returns:
        validated seed
    """
    if type(seed) is not int or seed < 0:
        raise ValueError("Random seed must be positive integer")
    elif seed == 0:
        return random.randint(1, 1000000)
    else:
        return seed


def safe_divide(numerator: int, denominator: int) -> float:
    """
    Divide two numbers, but default 0 if denominator is 0, otherwise divide as normal.

    args:
        numerator: number being divided
        denominator: number doing the dividing

    returns:
        resulting number
    """
    if denominator == 0:
        return 0.0
    else:
        return 1.0 * numerator / denominator


# Requirement for safe_random_choice function
T = TypeVar("T")


def safe_random_choice(seq: Collection[T], rand_gen, weights=None) -> Optional[T]:
    """
    Return None or a random choice from a collection of items

    args:
        seq: collection to select a random item from
        rand_gen: random number generator
        weights: an optional collection of weights to use instead of a uniform distribution

    returns:
        an item, or `None` if the collection is empty
    """
    if not seq:
        return None

    if isinstance(seq, set):
        seq = tuple(seq)

    choices = rand_gen.choices(seq, weights=weights)
    return choices[0]


def safe_shuffle(seq: Collection[T], rand_gen) -> Optional[Collection[T]]:
    """
    Return None or a shuffled sequence

    args:
        seq: collection to shuffle
        rand_gen: random number generator

    returns:
        shuffled sequence, or `None` if empty
    """
    if seq:
        if isinstance(seq, set):
            rand_gen.shuffle(list(seq))
            return seq
        else:
            rand_gen.shuffle(seq)
            return seq
    else:
        return None


def safe_dist(dist_info: ObjMap, rand_gen) -> Union[int, float]:
    """
    Draw a value from a distribution as defined in `dist_info`.

    args:
        dist_info: a definition of a distribution to use [params.classes.distributions]
        rand_gen: random number generator

    returns:
        a value drawn from the distribution
    """
    # gather arguments
    args = []
    for i in range(1, len(dist_info.vars) + 1):
        val = dist_info.vars[i].value
        type_caster = eval(dist_info.vars[i].value_type)
        val = type_caster(val)
        args.append(val)

    dist_type = dist_info.dist_type

    try:  # does dist exist in numpy?
        dist = getattr(rand_gen, dist_type)
        value = dist(*args)
    except AttributeError:
        try:  # does dist exist in distributions.py
            dist = getattr(distributions, dist_type)
            value = dist(rand_gen, *args)
        except AttributeError:
            raise AttributeError(f"Distribution type {dist_type} not found!")

    if hasattr(value, "__iter__"):  # check if value is any type of sequence
        return value[0]
    else:
        return value


def binom_0(n: int, p: float):
    """
    Mirrors scipy binom.pmf as used in code
    """
    return (1 - p) ** n


def poisson(mu: float, np_rand):
    """
    Mirrors scipy poisson.rvs function as used in code
    """
    return np_rand.poisson(mu)


def memo(f):
    """
    Decorator to memoize a function
    (caches results given args, only use if deterministic)
    """
    cache = {}

    @wraps(f)
    def wrap(*arg):
        if arg not in cache:
            cache[arg] = f(*arg)
        return cache[arg]

    return wrap


def get_param_from_path(params: ObjMap, param_path: str, delimiter: str):
    """
    Given a params object and a delimited path, get the leaf of the params tree
    and the last key to access it
    """
    path = param_path.split(delimiter)
    path_params = params
    for p in path[:-1]:
        try:
            path_params = path_params[p]
        except KeyError:
            path_params = path_params[int(p)]

    return path_params, path[-1]


def scale_param(params: ObjMap, param_path: str, scalar: float, delimiter="|"):
    """
    Given the params and a parameter path in the format prep|cap, scale the
    current value by the scalar
    """
    scaling_item, last_key = get_param_from_path(params, param_path, delimiter)

    old_val = scaling_item[last_key]
    print(f"scaling - {param_path}: {old_val} => {old_val * scalar}")
    scaling_item[last_key] = old_val * scalar


def override_param(params: ObjMap, param_path: str, value, delimiter="|"):
    """
    Given the params and a parameter path in the format prep|cap, change the
    current value to new value
    """
    override_item, last_key = get_param_from_path(params, param_path, delimiter)
    try:
        old_val = override_item[last_key]
    except KeyError:
        last_key = int(last_key)
        old_val = override_item[last_key]

    print(f"overriding - {param_path}: {old_val} => {value}")
    override_item[last_key] = value


def total_probability(p: float, num_acts: int) -> float:
    """
    Given a per act probability and a number of acts, return the total probability.

    args:
        p: the per act probability
        num_acts: the number of acts

    returns:
        the total probability
    """
    if num_acts == 1:
        return p
    elif num_acts >= 1:
        return 1.0 - binom_0(num_acts, p)
    else:
        return 0.0


def connected_components(graph):
    """
    Get connected components in graph

    args:
        graph: the model's underlying graph

    returns:
        list of connected components
    """
    return list(graph.subgraph(c).copy() for c in nx.connected_components(graph))


def get_independent_bin(rand_gen, bin_def: ObjMap) -> int:
    """
    Get the bin key given independent bins.  A probability is selected at random, then each bin's `prob` is compared to it, the first bin that has a `prob` less than or equal to that probability is returned.

    args:
        rand_gen: A random number generator
        bin_def: The ObjMap containing the bins

    returns:
        The integer key of the matched bin (or last bin if no matches)
    """
    rand_val = rand_gen.random()
    for bin, fields in bin_def.items():
        if rand_val <= fields.prob:
            break

    return bin


def get_cumulative_bin(rand_gen, bin_def: ObjMap) -> int:
    """
    Get the bin key given cumulative bins.  A probability is selected at random, then each bin's `prob` is compared to it, the first bin that has a cumulative `prob` (e.g. for bin 2, the prob of bin 1 plus the prob of bin 2) less than or equal to that probability is returned.

    args:
        rand_gen: random number generator
        bin_def: ObjMap containing the bins

    returns:
        integer key of the matched bin (or last bin if no matches)
    """
    rand_val = rand_gen.random()
    p = 0.0
    for bin, fields in bin_def.items():
        p += fields.prob
        if rand_val <= p:
            break

    return bin
