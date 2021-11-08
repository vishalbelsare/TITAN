from . import utils
from .location import Location

# ================ CORE PROBABILITIES ========================


@utils.memo
def get_death_rate(
    hiv: bool,
    aids: bool,
    drug_type: str,
    sex_type: str,
    haart_adh: bool,
    race: str,
    location: Location,
    steps_per_year: int,
    exit_type: str,
) -> float:
    """
    Find the death rate of an agent given a set of attributes.

    args:
        hiv: whether the agent is HIV+
        aids: whether the agent has AIDS
        drug_type: whether the PWID base death rate should be used or the base one
        haart_adh: whether an agent is haart adherent
        race: the race of the agent
        location: agent's location
        exit_type: the method for exit

    returns:
        the probability of an agent with these characteristics dying in a given time step
    """
    param = location.params.demographics

    death_param = param[race].sex_type[sex_type].drug_type[drug_type].exit[exit_type]

    p = death_param.base

    if aids:
        p *= death_param.aids
    elif hiv:
        if haart_adh:
            p *= death_param.haart_adherent
        else:
            p *= death_param.hiv

    if p == 0.0:
        print(f"{exit_type}, {death_param}")
    # putting it into per 1 person-month from per 1000 person years
    print("============")
    print(f"{p} {p / (1000 * steps_per_year)} {sex_type} {drug_type} {race}")
    return p / (1000 * steps_per_year)
