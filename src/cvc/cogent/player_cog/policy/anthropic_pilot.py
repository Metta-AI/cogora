from __future__ import annotations

from typing import Any

from mettagrid_sdk.sdk import MacroDirective, MettagridState

from cvc.cogent.player_cog.policy import helpers as _h
from cvc.cogent.player_cog.policy.helpers.types import KnownEntity
from cvc.cogent.player_cog.policy.semantic_cog import (
    MettagridSemanticPolicy,
    SemanticCogAgentPolicy,
    SharedWorldModel,
)
from cvc.cogent.player_cog.policy.pilot_base import PilotAgentPolicy, PilotCyborgPolicy
from cvc.cogent.player_cog.runtime.anthropic_pilot import AnthropicPilotSession
from mettagrid.policy.policy import AgentPolicy
from mettagrid.policy.policy_env_interface import PolicyEnvInterface
from mettagrid.simulator import Action

__all__ = [
    "AnthropicCyborgPolicy",
    "AnthropicPilotAgentPolicy",
    "AnthropicPilotSession",
]

_ELEMENTS = ("carbon", "oxygen", "germanium", "silicon")
# Max distance from hub for miners (stay safe, reduce deaths)
_MINER_MAX_HUB_DISTANCE = 15


def _shared_resources(state: MettagridState) -> dict[str, int]:
    if state.team_summary is None:
        return {r: 0 for r in _ELEMENTS}
    return {r: int(state.team_summary.shared_inventory.get(r, 0)) for r in _ELEMENTS}


def _least_resource(resources: dict[str, int]) -> str:
    return min(_ELEMENTS, key=lambda r: resources[r])


class AlphaV65ReplicaAgentPolicy(SemanticCogAgentPolicy):
    """Replica of v65 behavior: base budgets, no network/hotspot penalties."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_weight = 0.0
        self._hotspot_weight = 0.0

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        return 0


class AlphaV65PlusBiasAgentPolicy(SemanticCogAgentPolicy):
    """V65-style targeting + resource bias. Best of both worlds."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_weight = 0.0
        self._hotspot_weight = 0.0

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        return 0


class AlphaBiasOnlyAgentPolicy(SemanticCogAgentPolicy):
    """Base policy + resource bias only. No budget/retreat changes."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaDoubleScrambleAgentPolicy(SemanticCogAgentPolicy):
    """Base policy + 2 scramblers from step 100 for more opponent disruption."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)

        if objective == "resource_coverage":
            return 0, 0

        if step < 30:
            pressure_budget = 2
        elif step < 3000:
            pressure_budget = 6  # 4 aligners + 2 scramblers, 2 miners
            if min_res < 1 and not can_hearts:
                pressure_budget = 2
            elif min_res < 3:
                pressure_budget = 4
        else:
            pressure_budget = 6
            if min_res < 1 and not can_hearts:
                pressure_budget = 3

        scrambler_budget = 0
        if step >= 100:
            scrambler_budget = 2
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaSuperAggroAgentPolicy(SemanticCogAgentPolicy):
    """Maximum aggression: 6 pressure from step 30, resource bias."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)

        if objective == "resource_coverage":
            return 0, 0

        if step < 20:
            pressure_budget = 3
        else:
            pressure_budget = 6  # 4a + 2s = 2 miners
            if min_res < 1 and not can_hearts:
                pressure_budget = 3

        scrambler_budget = 0
        if step >= 50:
            scrambler_budget = 2
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaScrambleHeavyAgentPolicy(SemanticCogAgentPolicy):
    """3 scramblers + 3 aligners + 2 miners. Heavy disruption focus."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)

        if objective == "resource_coverage":
            return 0, 0

        if step < 30:
            return 2, 0

        pressure_budget = 6  # 3a + 3s, 2 miners
        if min_res < 1 and not can_hearts:
            pressure_budget = 3

        scrambler_budget = min(3, pressure_budget // 2) if step >= 100 else 0
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaNoScrambleAgentPolicy(SemanticCogAgentPolicy):
    """All aligners, no scramblers. 5 aligners + 3 miners."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)

        if objective == "resource_coverage":
            return 0, 0

        if step < 30:
            return 2, 0

        aligner_budget = 5
        if min_res < 1 and not can_hearts:
            aligner_budget = 2

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, 0


class AlphaCogAgentPolicy(SemanticCogAgentPolicy):
    """Optimized agent policy: aggressive alignment with scrambler defense."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_budget_change_step = 0
        # Init budget adapts to team size, capped to leave 1 miner
        num_agents = self.policy_env_info.num_agents
        self._current_aligner_budget = min(4, max(num_agents - 1, 1))

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Stable role allocation. Avoids role oscillation that wastes gear."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if objective == "economy_bootstrap":
                return 1, 0
            return 1, 0

        if num_agents <= 4:
            if step < 10:
                return 1, 0
            aligner_budget = 2
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 10:
            return min(2, num_agents - 1), 0
        if step < 100:
            aligner_budget = min(3, num_agents - 2)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, 0

        aligner_budget = min(4, num_agents - 2)
        scrambler_budget = 1 if step >= 200 else 0

        if min_res < 1 and not _h.team_can_refill_hearts(state):
            aligner_budget = max(aligner_budget - 1, 1)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Miners: retreat if too far from hub (prevent deaths in dangerous territory)."""
        if super()._should_retreat(state, role, safe_target):
            return True
        # Extra safety for miners: don't wander too far from hub
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            hp = int(state.self_state.inventory.get("hp", 0))
            # Retreat if far from hub with low-ish HP
            # Need enough HP to walk back + safety margin
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 20:
                return True
        return False


# Keep these for backwards compatibility with tournament uploads
class AnthropicPilotAgentPolicy(PilotAgentPolicy):
    _LLM_ANALYSIS_INTERVAL = 500  # Run LLM analysis every N steps

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_budget_change_step = 0
        num_agents = self.policy_env_info.num_agents
        self._current_aligner_budget = min(4, max(num_agents - 1, 1))

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        directive = MacroDirective(resource_bias=least)

        # Periodic LLM analysis — logs opinions without overriding strategy
        step = state.step or self._step_index
        if step > 0 and step % self._LLM_ANALYSIS_INTERVAL == 0:
            self._run_llm_analysis(state, directive)

        return directive

    def _run_llm_analysis(self, state: MettagridState, current_directive: MacroDirective) -> None:
        """Ask the LLM to analyze game state and log insights."""
        try:
            llm_directive = self._pilot_session.directive_for_state(state, memory=self._memory)
            print(
                f"[LLM] step={state.step} agent={self._agent_id} "
                f"llm_objective={llm_directive.objective} "
                f"llm_bias={llm_directive.resource_bias} "
                f"llm_note={llm_directive.note} "
                f"heuristic_bias={current_directive.resource_bias}",
                flush=True,
            )
        except Exception as e:
            print(f"[LLM] step={state.step} agent={self._agent_id} error={e}", flush=True)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy-responsive with hysteresis — synced with AlphaCogAgentPolicy."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if objective == "economy_bootstrap":
                return 1, 0
            return 1, 0

        if num_agents <= 4:
            if step < 10:
                return 1, 0
            aligner_budget = 2
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        if step < 10:
            return min(2, num_agents - 1), 0
        if step < 100:
            aligner_budget = min(3, num_agents - 2)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, 0

        aligner_budget = min(4, num_agents - 2)
        scrambler_budget = 1 if step >= 200 else 0

        if min_res < 1 and not _h.team_can_refill_hearts(state):
            aligner_budget = max(aligner_budget - 1, 1)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Miners: retreat if too far from hub."""
        if super()._should_retreat(state, role, safe_target):
            return True
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            hp = int(state.self_state.inventory.get("hp", 0))
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 20:
                return True
        return False


class AnthropicCyborgPolicy(PilotCyborgPolicy):
    short_names = ["anthropic-cyborg", "claude-cyborg", "cyborg-anthropic"]
    _session_class = AnthropicPilotSession
    _agent_policy_class = AnthropicPilotAgentPolicy
    _background_reviews_default = True

    def _provider_session_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        return {
            "api_key": kwargs.get("api_key"),
            "api_key_file": kwargs.get("api_key_file"),
            "anthropic_api_key": kwargs.get("anthropic_api_key"),
            "anthropic_api_key_file": kwargs.get("anthropic_api_key_file"),
        }


class AlphaV65ReplicaPolicy(MettagridSemanticPolicy):
    """Replica of v65: base budgets, no network/hotspot penalties."""
    short_names = ["alpha-v65-replica"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65ReplicaAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65PlusBiasPolicy(MettagridSemanticPolicy):
    """V65 targeting + resource bias."""
    short_names = ["alpha-v65-bias"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65PlusBiasAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaBiasOnlyPolicy(MettagridSemanticPolicy):
    """Base policy + resource bias. Uses base budgets (aggressive like v65)."""
    short_names = ["alpha-bias-only"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaBiasOnlyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaDoubleScramblePolicy(MettagridSemanticPolicy):
    """Base + resource bias + 2 scramblers from step 100."""
    short_names = ["alpha-double-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaDoubleScrambleAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaSuperAggroPolicy(MettagridSemanticPolicy):
    """Maximum aggression: 6 pressure from step 30."""
    short_names = ["alpha-super-aggro"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSuperAggroAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaScrambleHeavyPolicy(MettagridSemanticPolicy):
    """3 scramblers + 3 aligners. Heavy disruption."""
    short_names = ["alpha-scramble-heavy"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaScrambleHeavyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaNoScramblePolicy(MettagridSemanticPolicy):
    """All aligners, no scramblers."""
    short_names = ["alpha-no-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaNoScrambleAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaCyborgPolicy(MettagridSemanticPolicy):
    """Lightweight policy without LLM dependencies."""
    short_names = ["alpha-cyborg"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCogAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]
