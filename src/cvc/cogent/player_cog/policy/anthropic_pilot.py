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
        """Economy-responsive with hysteresis. Adapts to team size."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        num_agents = self.policy_env_info.num_agents
        if num_agents <= 4:
            max_pressure = max(num_agents // 2, 1)
        else:
            max_pressure = max(num_agents - 1, 1)

        # Phase 1: Economy bootstrap
        if step < 10:
            return min(2, max_pressure), 0

        # Phase 2: Early ramp
        if step < 50:
            aligner_budget = 4 if min_res >= 3 else 3
            return min(aligner_budget, max_pressure), 0

        # Phase 3: Steady state with hysteresis
        desired = self._current_aligner_budget
        if min_res >= 5:
            desired = 5
        elif min_res < 1 and not _h.team_can_refill_hearts(state):
            desired = 3
        elif min_res < 1:
            desired = 4

        if desired != self._current_aligner_budget:
            if step - self._last_budget_change_step >= 200 or desired < self._current_aligner_budget:
                self._current_aligner_budget = desired
                self._last_budget_change_step = step

        aligner_budget = self._current_aligner_budget
        scrambler_budget = 0

        # Add scrambler at step 300
        if step >= 300 and num_agents >= 4:
            scrambler_budget = 1

        # Cap total pressure
        total = aligner_budget + scrambler_budget
        if total > max_pressure:
            aligner_budget = max(max_pressure - scrambler_budget, 0)

        if objective == "resource_coverage":
            return 0, 0
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
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 10:
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
        min_miners = 2 if num_agents >= 4 else 1
        max_pressure = max(num_agents - min_miners, 1)

        if step < 10:
            return min(2, max_pressure), 0
        if step < 50:
            aligner_budget = 4 if min_res >= 3 else 3
            return min(aligner_budget, max_pressure), 0

        desired = self._current_aligner_budget
        if min_res >= 5:
            desired = 5
        elif min_res < 1 and not _h.team_can_refill_hearts(state):
            desired = 3
        elif min_res < 1:
            desired = 4

        if desired != self._current_aligner_budget:
            if step - self._last_budget_change_step >= 200 or desired < self._current_aligner_budget:
                self._current_aligner_budget = desired
                self._last_budget_change_step = step

        aligner_budget = self._current_aligner_budget
        scrambler_budget = 0
        if step >= 300 and num_agents >= 6:
            scrambler_budget = 1

        total = aligner_budget + scrambler_budget
        if total > max_pressure:
            aligner_budget = max(max_pressure - scrambler_budget, 0)

        if objective == "resource_coverage":
            return 0, 0
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
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 10:
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
            )
        return self._agent_policies[agent_id]
