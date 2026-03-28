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


class AlphaBiasOnlyAgentPolicy(SemanticCogAgentPolicy):
    """Base policy + resource bias only. No budget/retreat changes."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


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
