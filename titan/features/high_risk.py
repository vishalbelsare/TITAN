# mypy: always-true=HighRisk

from typing import Dict, ClassVar, Optional

from . import base_feature
from .. import utils
from .. import agent
from .. import population
from .. import model


class HighRisk(base_feature.BaseFeature):

    name = "high_risk"
    stats = [
        "high_risk_new",
        "high_risk_new_hiv",
        "high_risk_new_aids",
        "high_risk_new_dx",
        "high_risk_new_haart",
        "hiv_new_high_risk",
        "hiv_new_high_risk_ever",
    ]
    """
        High Risk collects the following stats:

        * high_risk_new - number of agents that became active high risk this time step
        * high_risk_new_hiv - number of agents that became active high risk this time step with HIV
        * high_risk_new_aids - number of agents that became active high risk this time step with AIDS
        * high_risk_new_dx - number of agents that became active high risk this time step with diagnosed HIV
        * high_risk_new_haart - number of agents that became active high risk this time step with active HAART
        * inf_HR6m - number of agents that became active with HIV this time step who are high risk
        * inf_HRever - number of agents that became active with HIV this time step were ever high risk
    """

    count: ClassVar[int] = 0

    def __init__(self, agent: "agent.Agent"):
        super().__init__(agent)

        self.active = False
        self.time: Optional[int] = None
        self.duration = 0
        self.ever = False

    @classmethod
    def init_class(cls, params):
        """
        Initialize the count of high risk agents to 0.

        args:
            params: the population params
        """
        cls.count = 0

    def init_agent(self, pop: "population.Population", time: int):
        """
        Initialize the agent for this feature during population initialization (`Population.create_agent`).  Called on only features that are enabled per the params.

        Based on agent demographic params, randomly initialize agent as high risk.

        args:
            pop: the population this agent is a part of
            time: the current time step
        """
        if (
            pop.pop_random.random()
            < self.agent.location.params.demographics[self.agent.race][
                self.agent.sex_type
            ].high_risk.init
        ):
            self.become_high_risk(time)

    def update_agent(self, model: "model.HIVModel"):
        """
        Update the agent for this feature for a time step.  Called once per time step in `HIVModel.update_all_agents`. Agent level updates are done after population level updates.   Called on only features that are enabled per the params.

        Update high risk agents or remove them from high risk pool.  An agent becomes high_risk through the incarceration feature

        args:
            model: the instance of HIVModel currently being run
        """
        if not self.active:
            return None

        if self.duration > 0:
            self.duration -= 1
        else:
            self.remove_agent(self.agent)
            self.active = False

            if model.params.features.incar:
                for bond in self.agent.location.params.high_risk.partnership_types:
                    self.agent.mean_num_partners[
                        bond
                    ] -= self.agent.location.params.high_risk.partner_scale
                    self.agent.mean_num_partners[bond] = max(
                        0, self.agent.mean_num_partners[bond]
                    )  # make sure not negative
                    self.agent.target_partners[bond] = utils.poisson(
                        self.agent.mean_num_partners[bond], model.np_random
                    )
                    while (
                        len(self.agent.partners[bond])
                        > self.agent.target_partners[bond]
                    ):
                        rel = utils.safe_random_choice(
                            self.agent.relationships, model.run_random
                        )
                        if rel is not None:
                            rel.progress(force=True)
                            model.pop.remove_relationship(rel)

    @classmethod
    def add_agent(cls, agent: "agent.Agent"):
        """
        Add an agent to the class (not instance).

        Increment the count of high risk agents. Add the agent to the set of newly high risk agents.

        args:
            agent: the agent to add to the class attributes
        """
        cls.count += 1

    @classmethod
    def remove_agent(cls, agent: "agent.Agent"):
        """
        Remove an agent from the class (not instance).

        Decrement the count of high risk agents.

        args:
            agent: the agent to remove from the class attributes
        """
        cls.count -= 1

    def set_stats(self, stats: Dict[str, int], time: int):
        if self.time == time:
            stats["high_risk_new"] += 1
            if self.agent.hiv:
                stats["high_risk_new_hiv"] += 1
                if self.agent.aids:
                    stats["high_risk_new_aids"] += 1
                if self.agent.hiv_dx:
                    stats["high_risk_new_dx"] += 1
                    if self.agent.haart.active:  # type: ignore[attr-defined]
                        stats["high_risk_new_haart"] += 1

        if self.agent.hiv_time == time:  # newly hiv
            if self.active:
                stats["hiv_new_high_risk"] += 1
            if self.ever:
                stats["hiv_new_high_risk_ever"] += 1

    # ============== HELPER METHODS ================

    def become_high_risk(self, time: int, duration: int = None):
        """
        Mark an agent as high risk and assign a duration to their high risk period

        args:
            time: the time step the agent is becoming high risk
            duration: duration of the high risk period, defaults to param value if not passed [params.high_risk.sex_based]
        """

        if not self.agent.location.params.features.high_risk:
            return None

        self.add_agent(self.agent)

        if not self.ever:
            self.time = time

        self.active = True
        self.ever = True

        if duration is not None:
            self.duration = duration
        else:
            self.duration = self.agent.location.params.high_risk.sex_based[
                self.agent.sex_type
            ].duration
