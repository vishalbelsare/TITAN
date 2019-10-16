import pytest

from src.agent import *


@pytest.fixture
def make_agent():
    def _make_agent(id, SO="MSM", age=30, race="BLACK", DU="NDU"):
        return Agent(id, SO, age, race, DU)

    return _make_agent


@pytest.fixture
def make_relationship():
    def _make_relationship(id1, id2, SO="MSM", rel_type="#REVIEW", duration=10):
        return Relationship(id1, id2, SO, rel_type, duration)

    return _make_relationship


def test_agent_init(make_agent):
    a = make_agent(1)
    assert a._ID == 1
    assert a._timeAlive == 0

    # demographics
    assert a._SO == "MSM"
    assert a._age == 30
    assert a._race == "BLACK"
    assert a._DU == "NDU"
    assert a._ageBin == 0
    assert a._MSMW is False

    # partner params
    assert a._relationships == []
    assert a._partners == []
    assert a._num_sex_partners == 0
    assert a._num_NE_partners == 0
    assert a._mean_num_partners == 0
    assert a._sexualRole == "Vers"

    # STI params
    assert a._STI_pool == []
    assert a._HIV_bool is False
    assert a._HIV_time == 0
    assert a._AIDS_bool is False
    assert a._AIDS_time == 0
    assert a._PrEPresistance == 0

    # treatment params
    assert a._tested is False
    assert a._HAART_bool is False
    assert a._HAART_time == 0
    assert a._HAART_adh == 0
    assert a._SNE_bool is False
    assert a._PrEP_bool is False
    assert a._PrEP_time == 0
    assert a._PrEP_adh == 0
    assert a._treatment_bool is False
    assert a._treatment_time == 0
    assert a._OAT_bool is False
    assert a._naltrex_bool is False
    assert a._DOC_OAT_bool is False
    assert a._DOC_NAL_bool is False
    assert a._MATprev == 0
    assert a._oatValue == 0
    assert a._PrEP_reason == []

    # prep pharmacokinetics
    assert a._PrEP_load == 0.0
    assert a._PrEP_lastDose == 0

    # high risk params
    assert a._highrisk_type is None
    assert a._highrisk_bool is False
    assert a._highrisk_time == 0
    assert a._everhighrisk_bool is False

    # incarceration
    assert a._incar_bool is False
    assert a._ever_incar_bool is False
    assert a._incar_time == 0
    assert a._incar_treatment_time == 0


def test_get_id(make_agent):
    a = make_agent(1)
    assert a.get_ID() == 1


def test_bond_unbond(make_agent, make_relationship):
    a = make_agent(1)
    p = make_agent(2)
    r = make_relationship(a, p)
    a.bond(p, r)
    assert r in p._relationships
    assert p in a._partners
    assert r in a._relationships
    assert a in p._partners
    assert a._num_sex_partners == 1
    assert p._num_sex_partners == 1

    p.unbond(a, r)
    assert r not in p._relationships
    assert p not in a._partners
    assert r not in a._relationships
    assert a not in p._partners
    assert a._num_sex_partners == 1
    assert p._num_sex_partners == 1


def test_partner_list(make_agent, make_relationship):
    a = make_agent(1)

    assert a.partner_list() == []

    p = make_agent(2)
    r = make_relationship(a, p)
    a.bond(p, r)  # REVIEW what is the logic behind relationship -> bond -> pair?

    assert a.partner_list() == [2]
    assert p.partner_list() == [1]


def test_relationship_init(make_agent, make_relationship):
    a = make_agent(1)
    p = make_agent(2)
    r = make_relationship(a, p)

    assert r._ID1 == a
    assert r._ID2 == p
    assert r._ID == 100002
    assert r.get_ID() == 100002

    # properties
    assert r._SO == "MSM"
    assert r._rel_type == "#REVIEW"
    assert r._duration == 10
    assert r._total_sex_acts == 0

    # STI
    assert r._STI_pool == []
    assert r._HIV_bool is False
    assert r._HIV_time == 0
    assert r._AIDS_bool is False
    assert r._AIDS_time == 0

    # treatment
    assert r._tested is False
    assert r._HAART_bool is False
    assert r._HAART_time == 0
    assert r._HAART_adh == 0

    # incarceration
    assert r._incar_bool is False
    assert r._incar_time == 0


@pytest.mark.skip(
    reason="#REVIEW relationships are assumed to be bonded, but that's not enforced in the code/constructor (at least compactly)"
)
def test_progress(make_agent, make_relationship):
    pass


def test_Agent_set_init(make_agent):
    s = Agent_set("test")

    assert s._ID == "test"
    assert s._members == []
    assert s._subset == {}

    assert s._parent_set is None
    assert s._numerator == s


def test_add_remove_agent(make_agent):
    a = make_agent(1)
    s = Agent_set("test")

    s.add_agent(a)

    assert s._members == [a]
    assert s.is_member(a)
    assert s.num_members() == 1

    s.remove_agent(a)

    assert s._members == []
    assert s.is_member(a) is False
    assert s.num_members() == 0