import pytest
import os

from titan.population import *
from titan.agent import Agent
from titan.parse_params import create_params


@pytest.fixture
def params(tmpdir):
    param_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "params", "basic.yml"
    )
    return create_params(None, param_file, tmpdir)


@pytest.fixture
def make_agent():
    def _make_agent(SO="MSM", age=30, race="WHITE", DU="None"):
        return Agent(SO, age, race, DU)

    return _make_agent


@pytest.fixture
def make_population(params):
    def _make_population(n=100):
        params.model.num_pop = n
        return Population(params)

    return _make_population


# helper method to generate a fake number deterministically
class FakeRandom:
    def __init__(self, num: float, fake_choice: int = 0):
        self.num = num
        self.fake_choice = fake_choice

    def random(self):
        return self.num

    def randrange(self, start, stop, step=1):
        return start

    def randint(self, start, stop):
        return start

    def choice(self, seq):
        return seq[-1]

    def choices(self, seq, weights=None, k=1):
        return list(seq)[self.fake_choice]


def test_pop_init(make_population):
    n_pop = 100
    pop = make_population(n=n_pop)

    assert pop.all_agents.num_members() == n_pop

    # test umbrella sets are all consistent
    parent_sets = ["drug_use_agents", "sex_type_agents", "race_agents"]
    for set_name in parent_sets:
        set = getattr(pop, set_name)

        assert set.num_members() == n_pop

        child_pops = 0
        for child_set in set.iter_subset():
            child_pops += child_set.num_members()

        assert child_pops == n_pop


def test_create_agent(make_population):
    pop = make_population()

    a1 = pop.create_agent("WHITE")
    assert a1.race == "WHITE"
    assert a1.prep_opinion in range(
        5
    ), f"Agents opinion of injectible PrEP is out of bounds {a1.prep_opinion}"

    a2 = pop.create_agent("BLACK")
    assert a2.race == "BLACK"

    a3 = pop.create_agent("WHITE", "HM")
    assert a3.so == "HM"
    assert a3.race == "WHITE"

    # check PWID and HIV and high risk
    pop.pop_random = FakeRandom(-0.1)
    a4 = pop.create_agent("WHITE")
    assert a4.drug_use == "Inj"
    assert a4.hiv
    assert a4.aids
    assert a4.hiv_dx
    assert a4.haart
    assert a4.haart_adherence == 5
    assert a4.haart_time == 0
    assert a4.intervention_ever
    assert a4.high_risk
    assert a4.high_risk_ever

    # check not PWID and HIV
    pop.pop_random = FakeRandom(0.999)
    a4 = pop.create_agent("WHITE")
    assert a4.drug_use == "None"
    assert a4.hiv is False
    assert a4.prep is False
    assert a4.intervention_ever is False


def test_create_agent_proportions(make_population, params):
    pop = make_population()

    n = 1000
    race = "WHITE"
    # check proportions
    pop.pop_weights[race] = {"values": ["HM", "HF"], "weights": [0.1, 0.9]}
    prop_idu = round(params.demographics[race]["PWID"].ppl * n)
    num_HM = 0
    num_HF = 0
    num_PWID = 0
    for i in range(n):
        a = pop.create_agent(race)
        if a.drug_use == "Inj":
            num_PWID += 1

        if a.so == "HF":
            num_HF += 1
        elif a.so == "HM":
            num_HM += 1
        else:
            assert False

    assert num_HM > 70 and num_HM < 130
    assert num_HF > 830 and num_HF < 930
    assert num_PWID > prop_idu - 50 and num_PWID < prop_idu + 50


def test_add_remove_agent_to_pop(make_population):
    pop = make_population()
    agent = pop.create_agent("WHITE", "HM")
    agent.drug_use = "Inj"
    agent.hiv = True
    agent.aids = True
    agent.intervention_ever = True
    agent.haart = True
    agent.prep = True
    agent.hiv_dx = True
    agent.incar = True
    agent.high_risk = True

    pop.add_agent(agent)

    assert agent in pop.all_agents.members
    assert agent in pop.race_agents.members
    assert agent in pop.race_white_agents.members
    assert agent in pop.sex_type_agents.members
    assert agent in pop.sex_type_HM_agents.members
    assert agent in pop.drug_use_agents.members
    assert agent in pop.drug_use_inj_agents.members
    assert agent in pop.hiv_agents.members
    assert agent in pop.hiv_aids_agents.members
    assert agent in pop.intervention_agents.members
    assert agent in pop.intervention_haart_agents.members
    assert agent in pop.intervention_haart_agents.members
    assert agent in pop.intervention_prep_agents.members
    assert agent in pop.intervention_dx_agents.members
    assert agent in pop.incarcerated_agents.members
    assert agent in pop.high_risk_agents.members

    assert pop.graph.has_node(agent)

    # check not in all agent sets
    assert agent not in pop.race_black_agents.members

    pop.remove_agent(agent)

    assert agent not in pop.all_agents.members
    assert agent not in pop.race_agents.members
    assert agent not in pop.race_white_agents.members
    assert agent not in pop.sex_type_agents.members
    assert agent not in pop.sex_type_HM_agents.members
    assert agent not in pop.drug_use_agents.members
    assert agent not in pop.drug_use_inj_agents.members
    assert agent not in pop.hiv_agents.members
    assert agent not in pop.hiv_aids_agents.members
    assert agent not in pop.intervention_agents.members
    assert agent not in pop.intervention_haart_agents.members
    assert agent not in pop.intervention_haart_agents.members
    assert agent not in pop.intervention_prep_agents.members
    assert agent not in pop.intervention_dx_agents.members
    assert agent not in pop.incarcerated_agents.members
    assert agent not in pop.high_risk_agents.members

    assert not pop.graph.has_node(agent)


def test_get_age(make_population, params):
    pop = make_population()

    race = "WHITE"

    expected_ages = [15, 25, 35, 45, 55]
    for i in range(1, 6):
        # make sure rand is less than the setting
        pop.pop_random = FakeRandom(params.demographics[race].age[i].prob - 0.001)
        age, ageBin = pop.get_age(race)
        assert age == expected_ages[i - 1]
        assert ageBin == i


def test_update_agent_partners_no_match(make_population, params):
    pop = make_population(n=1)
    params.model.num_pop = 0

    agent = pop.all_agents.members[0]  # the only agent in the pop

    pop.update_agent_partners(agent, pop.all_agents)  # noMatch == True
    assert agent in pop.graph.nodes()
    assert len(pop.graph.edges()) == 0


def test_update_agent_partners_match(make_population, params):
    pop = make_population(n=0)
    a = pop.create_agent("WHITE", "MSM")
    p = pop.create_agent("WHITE", "MSM")
    # ensure random sex partner no assorting
    pop.pop_random = FakeRandom(1.1)
    a.drug_use = "None"
    p.drug_use = "None"
    pop.add_agent(a)
    pop.add_agent(p)

    pop.update_agent_partners(a, pop.all_agents)
    assert a in pop.graph.nodes()
    assert p in pop.graph.nodes()
    assert len(pop.graph.edges()) == 1


def test_update_partner_assignments_match(make_population, params):
    pop = make_population(n=0)
    a = pop.create_agent("WHITE", "MSM")
    p = pop.create_agent("WHITE", "MSM")
    # ensure random sex partner no assorting
    pop.pop_random = FakeRandom(1.1)
    a.drug_use = "None"
    p.drug_use = "None"
    pop.add_agent(a)
    pop.add_agent(p)
    a.mean_num_partners = 100
    p.mean_num_partners = 100

    pop.update_partner_assignments()
    assert a in pop.graph.nodes()
    assert p in pop.graph.nodes()
    assert len(pop.graph.edges()) == 1


def test_update_partner_assignments_no_match(make_population, params):
    pop = make_population(n=0)
    a = pop.create_agent("WHITE", "MSM")
    p = pop.create_agent("WHITE", "HM")
    # ensure random sex partner no assorting
    pop.pop_random = FakeRandom(1.1)
    a.drug_use = "None"
    p.drug_use = "None"
    pop.add_agent(a)
    pop.add_agent(p)

    params.model.num_pop = 0

    pop.update_partner_assignments()
    assert a in pop.graph.nodes()
    assert p in pop.graph.nodes()
    assert len(pop.graph.edges()) == 0


def test_network_init_scale_free(params):
    """Test if all Inj,NonInj,None drug use agents are in the population"""
    net = Population(params)
    assert params.model.num_pop == net.all_agents.num_members()

    for agent in net.all_agents:
        assert agent in net.graph.nodes()

    for agent in net.all_agents:
        assert agent.drug_use in ["Inj", "NonInj", "None"]
        assert agent.so in params.classes.sex_types


def test_network_init_max_k(params):
    """Test if all Inj,NonInj,None drug use agents are in the population"""
    params.model.network.type = "max_k_comp_size"
    net = Population(params)
    assert params.model.num_pop == net.all_agents.num_members()

    for agent in net.all_agents:
        assert agent in net.graph.nodes()

    for agent in net.all_agents:
        assert agent.drug_use in ["Inj", "NonInj", "None"]
        assert agent.so in params.classes.sex_types


def test_population_consistency_DU(params):
    """Test if Drug users add up"""
    net = Population(params)
    check_sum_DU = (
        net.drug_use_inj_agents.num_members()
        + net.drug_use_noninj_agents.num_members()
        + net.drug_use_none_agents.num_members()
    )

    assert net.drug_use_agents.num_members() == check_sum_DU
    assert params.model.num_pop == check_sum_DU


def test_population_consistency_HIV(params):
    """Test HIV consistency"""
    net = Population(params)
    for agent in net.all_agents:
        if agent.hiv:
            assert agent in net.hiv_agents

    for agent in net.hiv_agents:
        assert agent.hiv
