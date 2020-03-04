import pytest

from copy import deepcopy
import os

from titan.model import *
from titan.agent import Agent, Relationship
from titan.parse_params import create_params


@pytest.fixture
def params(tmpdir):
    param_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "params", "basic.yml"
    )
    return create_params(None, param_file, tmpdir)


@pytest.fixture
def make_agent():
    def _make_agent(SO="MSM", age=30, race="BLACK", DU="None"):
        return Agent(SO, age, race, DU)

    return _make_agent


@pytest.fixture
def make_model(params):
    def _make_model():
        return HIVModel(params)

    return _make_model


# helper method to generate a fake number deterministically
class FakeRandom:
    def __init__(self, num: float):
        self.num = num

    def random(self):
        return self.num

    def randrange(self, start, stop, step):
        return start

    def sample(self, seq, rate):
        return seq

    def choice(self, seq):
        return seq[0]

    def randint(self, start, stop):
        return start


# ================================ MODEL TESTS =================================


def test_model_init_error(params):
    params.model.seed.run = 0.5
    with pytest.raises(ValueError):
        HIVModel(params)


def test_model_init(params):
    model = HIVModel(params)

    assert model.run_seed > 0
    assert model.pop.pop_seed > 0

    assert model.new_infections.num_members() == 0
    assert model.new_dx.num_members() == 0
    assert model.new_incar_release.num_members() == 0
    assert model.new_high_risk.num_members() == 0

    assert model.total_dx == 0
    assert model.needle_exchange == False


@pytest.mark.skip("too parameter dependent to test at this point")
def test_update_AllAgents():
    pass


def test_agents_interact(make_model, make_agent):
    model = make_model()
    a = make_agent(race="WHITE", SO="HM")
    p = make_agent(race="WHITE", SO="HF")
    rel = Relationship(a, p, 10, bond_type="sexOnly")

    model.run_random = FakeRandom(0.6)

    a.incar = True
    assert model.agents_interact(0, rel) is False

    a.incar = False
    assert model.agents_interact(0, rel) is False  # neither HIV

    a.hiv = True
    p.hiv = True
    assert model.agents_interact(0, rel) is False  # both HIV

    p.hiv = False

    assert model.agents_interact(0, rel)  # sex transmssion
    assert p.hiv is False  # but nothing happened (see skipped test)

    a.drug_use = "Inj"
    p.drug_use = "Inj"

    model.run_random = FakeRandom(-0.1)

    assert model.agents_interact(0, rel)  # needle transmission
    assert p.hiv

    p.hiv = False
    model.run_random = FakeRandom(1.1)

    assert model.agents_interact(0, rel)  # needle and sex
    assert p.hiv is False  # but nothing happened


def test_needle_transmission(make_model, make_agent):
    model = make_model()
    a = make_agent(race="WHITE", DU="Inj", SO="HM")
    p = make_agent(race="WHITE", DU="Inj", SO="HF")

    with pytest.raises(AssertionError):
        model.needle_transmission(a, p, time=0)

    a.hiv = True
    a.hiv_time = 1  # acute

    model.run_random = FakeRandom(-0.1)

    model.needle_transmission(a, p, time=0)

    assert p.hiv


def test_sex_transmission(make_model, make_agent):
    model = make_model()
    a = make_agent()
    p = make_agent()
    rel = Relationship(a, p, 10, bond_type="sexOnly")

    a.hiv = True
    a.hiv_time = 1  # acute

    rel.total_sex_acts = 0

    model.run_random = FakeRandom(0.6)

    # test partner becomes
    model.sex_transmission(rel, 0)

    assert p.hiv


def test_sex_transmission_do_nothing(make_model, make_agent):
    model = make_model()
    a = make_agent()
    p = make_agent()
    rel = Relationship(a, p, 10, bond_type="sexOnly")

    with pytest.raises(ValueError):
        model.sex_transmission(rel, 0)

    a.hiv = True
    p.hiv = True

    # test nothing happens
    model.sex_transmission(rel, 0)


def test_pca_interaction(make_model, make_agent):
    model = make_model()
    a = make_agent()
    p = make_agent()
    a.prep_opinion = 4  # REVIEWED opinino and awareness are both prep things right? should the be prepended with prep_? YES
    p.prep_opinion = 2
    a.prep_awareness = True

    model.run_random = FakeRandom(1.0)

    model.pop.graph.add_edge(a, p)
    model.pop.graph.add_edge(a, "edge")

    rel = Relationship(a, p, 10, bond_type="multiplex")
    model.pca_interaction(rel, 5, force=True)

    assert p.prep_awareness

    model.pca_interaction(rel, 6, force=True)

    assert p.prep_opinion == 3


def test_hiv_convert(make_model, make_agent):
    model = make_model()
    a = make_agent()
    a.prep = True

    model.run_random = FakeRandom(-0.1)

    model.hiv_convert(a)

    assert a.hiv
    assert a.hiv_time == 1
    assert a in model.new_infections.members
    assert a in model.pop.hiv_agents.members
    assert a.prep is False


def test_enroll_needle_exchange(make_model):
    model = make_model()
    model.run_random = FakeRandom(-0.1)  # all "Inj" agents will be _SNE_bool

    # make at least one agent PWID
    model.pop.all_agents.members[0].drug_use = "Inj"

    assert model.needle_exchange is False

    model.enroll_needle_exchange()

    assert model.needle_exchange is True

    for a in model.pop.all_agents:
        if a.drug_use == "Inj":
            assert a.sne


def test_become_high_risk(make_model, make_agent):
    model = make_model()
    a = make_agent()

    model.become_high_risk(a, 10)

    assert a in model.pop.high_risk_agents.members
    assert a in model.new_high_risk.members
    assert a.high_risk
    assert a.high_risk_ever
    assert a.high_risk_time == 10


def test_incarcerate_diagnosed(make_model, make_agent):
    model = make_model()
    a = make_agent(SO="HM", race="WHITE")  # incarceration only for HM and HF?
    a.hiv = True
    a.hiv_dx = True

    model.run_random = FakeRandom(-0.1)  # always less than params

    model.incarcerate(a, 10)

    assert a.incar
    assert a.incar_time == 1
    assert a in model.pop.incarcerated_agents.members
    assert a.haart
    assert a.haart_adherence == 5
    assert a.haart_time == 10
    assert a in model.pop.intervention_haart_agents.members


def test_incarcerate_not_diagnosed(make_model, make_agent):
    model = make_model()
    a = make_agent(SO="HM", race="WHITE")  # incarceration only for HM and HF?
    a.hiv = True

    p = make_agent(SO="HF")
    rel = Relationship(a, p, 10, bond_type="sexOnly")

    model.run_random = FakeRandom(-0.1)  # always less than params

    model.incarcerate(a, 0)

    assert a.incar
    assert a.incar_time == 1
    assert a in model.pop.incarcerated_agents.members
    assert a.hiv_dx

    assert p in model.pop.high_risk_agents.members
    assert p in model.new_high_risk.members
    assert p.high_risk
    assert p.high_risk_ever
    assert p.high_risk_time > 0


def test_incarcerate_unincarcerate(make_model, make_agent):
    model = make_model()
    a = make_agent()

    a.incar = True
    a.incar_time = 2
    model.pop.incarcerated_agents.add_agent(a)

    model.incarcerate(a, 0)

    assert a.incar
    assert a.incar_time == 1
    assert a in model.pop.incarcerated_agents.members

    model.incarcerate(a, 0)

    assert a.incar is False
    assert a.incar_time == 0
    assert a not in model.pop.incarcerated_agents.members
    assert a in model.new_incar_release.members
    assert a.incar_ever


def test_diagnose_hiv(make_model, make_agent):
    model = make_model()
    a = make_agent()

    model.run_random = FakeRandom(1.1)  # always greater than param
    model.diagnose_hiv(a, 0)

    assert a.hiv_dx is False
    assert a not in model.new_dx.members
    assert a not in model.pop.intervention_dx_agents.members

    model.run_random = FakeRandom(-0.1)  # always less than param
    model.diagnose_hiv(a, 0)

    assert a.hiv_dx
    assert a in model.new_dx.members
    assert a in model.pop.intervention_dx_agents.members


def test_diagnose_hiv_already_tested(make_model, make_agent):
    model = make_model()
    a = make_agent()

    a.hiv_dx = True

    model.run_random = FakeRandom(-0.1)  # always less than param
    model.diagnose_hiv(a, 0)

    assert a.hiv_dx
    assert a not in model.new_dx.members
    assert a not in model.pop.intervention_dx_agents.members


def test_update_haart_t1(make_model, make_agent):
    model = make_model()
    a = make_agent(race="WHITE")

    a.hiv = True

    # nothing happens, not tested
    model.update_haart(a, 1)
    assert a.haart_adherence == 0
    assert a.haart is False
    assert a not in model.pop.intervention_haart_agents.members

    # t0 agent initialized HAART
    a.hiv_dx = True

    # go on haart
    model.run_random = FakeRandom(
        -0.1
    )  # means this will always be less than params even though not physically possible in reality
    model.update_haart(a, 1)

    assert a.haart_adherence == 5
    assert a.haart_time == 1
    assert a.haart
    assert a in model.pop.intervention_haart_agents.members

    # go off haart
    model.update_haart(a, 1)

    assert a.haart_adherence == 0
    assert a.haart_time == 0
    assert a.haart is False
    assert a not in model.pop.intervention_haart_agents.members


def test_discontinue_prep_force(make_model, make_agent):
    model = make_model()
    a = make_agent()

    # set up so the agent appears to be on PrEP
    a.prep = True
    a.prep_reason = ["blah"]
    model.pop.intervention_prep_agents.add_agent(a)

    model.discontinue_prep(a, True)

    assert a.prep is False
    assert a.prep_reason == []
    assert a not in model.pop.intervention_prep_agents.members


def test_discontinue_prep_decrement_time(make_model, make_agent):
    model = make_model()
    a = make_agent()

    # set up so the agent appears to be on PrEP
    a.prep = True
    a.prep_reason = ["blah"]
    model.pop.intervention_prep_agents.add_agent(a)

    model.discontinue_prep(a)

    assert a.prep
    assert a.prep_reason == ["blah"]


def test_discontinue_prep_decrement_end(make_model, make_agent):
    model = make_model()
    a = make_agent(race="WHITE")

    model.run_random = FakeRandom(-0.1)

    # set up so the agent appears to be on PrEP
    a.prep = True
    a.prep_reason = ["blah"]
    model.pop.intervention_prep_agents.add_agent(a)

    model.discontinue_prep(a)

    assert a.prep is False
    assert a.prep_reason == []
    assert a not in model.pop.intervention_prep_agents.members


def test_discontinue_prep_decrement_not_end(make_model, make_agent):
    model = make_model()
    a = make_agent()

    model.run_random = FakeRandom(1.1)

    # set up so the agent appears to be on PrEP
    a.prep = True
    a.prep_reason = ["blah"]
    a.prep_last_dose = 3
    model.pop.intervention_prep_agents.add_agent(a)

    model.discontinue_prep(a)

    assert a.prep
    assert a.prep_reason == ["blah"]
    assert a.prep_last_dose == -1  # 3 -> -1 -> +1 == 0 # Inj no longer in PrEP types
    assert a in model.pop.intervention_prep_agents.members
    # assert a.prep_load > 0 # Inj no longer in PrEP types


def test_initiate_prep_assertions(make_model, make_agent):
    model = make_model()
    a = make_agent()

    # no PreP if already PreP
    a.prep = True
    assert model.initiate_prep(a, 0) is None

    # no PrEP if already HIV
    a.prep = False
    a.hiv = True
    assert model.initiate_prep(a, 0) is None


def test_initiate_prep_force_adh(make_model, make_agent):
    model = make_model()
    a = make_agent()

    # forcing, adherant, inj
    model.run_random = FakeRandom(-0.1)
    model.initiate_prep(a, 0, True)
    assert a.prep
    assert a in model.pop.intervention_prep_agents.members
    assert a in model.new_prep.members
    assert a.prep_adherence == 1
    # assert a.prep_load > 0.0 # Inj no longer in PrEP types
    assert a.prep_last_dose == 0


def test_initiate_prep_force_non_adh(make_model, make_agent):
    model = make_model()
    a = make_agent()
    # forcing, non-adherant, inj
    model.run_random = FakeRandom(1.0)
    model.initiate_prep(a, 0, True)
    assert a.prep
    assert a in model.pop.intervention_prep_agents.members
    assert a in model.new_prep.members
    assert a.prep_adherence == 0
    # assert a.prep_load > 0.0 # Inj no longer in PrEP types
    assert a.prep_last_dose == 0


def test_initiate_prep_eligible(make_model, make_agent):
    model = make_model()

    # make sure there's room to add more prep agents
    model.pop.intervention_prep_agents.members = []
    a = make_agent(SO="HF")  # model is "CDCwomen"
    p = make_agent(DU="Inj")
    p.hiv_dx = True
    p.msmw = True
    rel = Relationship(a, p, 10, bond_type="sexOnly")
    # non-forcing, adherant, inj
    model.run_random = FakeRandom(-0.1)
    model.initiate_prep(a, 0)
    assert a.prep
    assert a in model.pop.intervention_prep_agents.members
    assert a in model.new_prep.members
    assert a.prep_adherence == 1
    # assert a.prep_load > 0.0 # Inj not in params prep_type anymore
    assert a.prep_last_dose == 0
    assert "PWID" in a.prep_reason
    assert "HIV test" in a.prep_reason
    assert "MSMW" in a.prep_reason


def test_progress_to_aids_error(make_agent, make_model):
    a = make_agent()
    model = make_model()
    num_aids = model.pop.hiv_aids_agents.num_members()  # get baseline

    # test error case, agent must be HIV+
    with pytest.raises(AssertionError):
        model.progress_to_aids(a)

    assert model.pop.hiv_aids_agents.num_members() == num_aids


def test_progress_to_aids_nothing(make_agent, make_model):
    a = make_agent()
    model = make_model()
    num_aids = model.pop.hiv_aids_agents.num_members()  # get baseline

    # test nothing case
    a.hiv = True
    a.haart_adherence = 1  # .0051 prob

    model.run_random = FakeRandom(0.9)  # no AIDS

    assert model.progress_to_aids(a) is None
    assert model.pop.hiv_aids_agents.num_members() == num_aids
    assert a.aids is False


def test_progress_to_aids_progress(make_agent, make_model):
    a = make_agent()
    model = make_model()
    num_aids = model.pop.hiv_aids_agents.num_members()  # get baseline

    a.hiv = True
    a.haart_adherence = 1  # .0051 prob

    # test progress case
    model.run_random = FakeRandom(0.001)  # AIDS

    assert model.progress_to_aids(a) is None
    assert model.pop.hiv_aids_agents.num_members() == num_aids + 1
    assert a in model.pop.hiv_aids_agents.members
    assert a.aids is True


def test_die_and_replace_none(make_model):
    model = make_model()
    model.run_random = FakeRandom(0.999)  # always greater than death rate
    baseline_pop = deepcopy(model.pop.all_agents.members)

    model.die_and_replace()

    ids = [a.id for a in baseline_pop]
    for agent in model.pop.all_agents.members:
        assert agent.id in ids


def test_die_and_replace_all(make_model):
    model = make_model()
    model.run_random = FakeRandom(0.0000001)  # always lower than death rate

    # un-incarcerate everyone
    for agent in model.pop.all_agents.members:
        agent.incar = False

    baseline_pop = deepcopy(model.pop.all_agents.members)
    old_ids = [a.id for a in baseline_pop]

    num_hm = len([x for x in baseline_pop if x.so == "HM"])
    num_white = len([x for x in baseline_pop if x.race == "WHITE"])

    model.die_and_replace()

    assert num_hm == len([x for x in model.pop.all_agents.members if x.so == "HM"])
    assert num_white == len(
        [x for x in model.pop.all_agents.members if x.race == "WHITE"]
    )

    new_ids = [a.id for a in model.pop.all_agents.members]
    death_ids = [a.id for a in model.deaths]

    for agent in model.pop.all_agents.members:
        assert agent.id not in old_ids
        assert agent in model.pop.graph.nodes()

    for agent in baseline_pop:
        assert agent.id not in new_ids
        assert agent not in model.pop.graph.nodes()
        assert agent.id in death_ids


def test_die_and_replace_incar(make_model):
    model = make_model()
    model.run_random = FakeRandom(0.0000001)  # always lower than death rate
    baseline_pop = deepcopy(model.pop.all_agents.members)
    old_ids = [a.id for a in baseline_pop]

    model.pop.all_agents.members[0].incar = True
    agent_id = model.pop.all_agents.members[0].id

    model.die_and_replace()

    new_ids = [a.id for a in model.pop.all_agents.members]
    death_ids = [a.id for a in model.deaths]

    assert agent_id in old_ids
    assert agent_id not in death_ids
    assert agent_id in new_ids