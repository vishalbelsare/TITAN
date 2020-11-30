import pytest

from titan.interactions import Injection
from titan.agent import Relationship

from conftest import FakeRandom


@pytest.mark.unit
def test_injection_transmission(make_model, make_agent):
    model = make_model()
    model.time = model.params.hiv.start_time + 2
    a = make_agent(race="white", DU="Inj", SO="HM")
    p = make_agent(race="white", DU="Inj", SO="HF")
    rel = Relationship(a, p, 10, bond_type="Inj")

    assert Injection.interact(model, rel) is False  # one agent must be HIV+

    a.hiv = True
    a.hiv_time = model.time - 1  # acute

    model.run_random = FakeRandom(-0.1)

    assert Injection.interact(model, rel)

    assert p.hiv


@pytest.mark.unit
def test_injection_transmission_do_nothing(make_model, make_agent):
    model = make_model()
    model.time = model.params.hiv.start_time + 2
    a = make_agent(race="white", DU="Inj", SO="HM")
    p_inj = make_agent(race="white", DU="Inj", SO="HF")
    p_sex = make_agent(race="white", DU="Inj", SO="HF")
    rel_Inj = Relationship(a, p_inj, 10, bond_type="Inj")
    rel_Sex = Relationship(a, p_sex, 10, bond_type="Sex")

    assert Injection.interact(model, rel_Inj) is False

    a.hiv = True

    with pytest.raises(AssertionError) as excinfo:
        assert Injection.interact(model, rel_Sex)
    assert "No injection acts allowed in" in str(excinfo)

    p_inj.hiv = True
    assert Injection.interact(model, rel_Inj) is False
