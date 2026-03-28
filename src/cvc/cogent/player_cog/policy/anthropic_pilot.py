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


class AlphaV65TrueReplicaAgentPolicy(SemanticCogAgentPolicy):
    """True v65 replica: uses original hub_penalty targeting, expansion 5/30, retreat_margin=15."""

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 15  # v65 used 15, not 20
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 10
        margin += int(state.self_state.inventory.get("heart", 0)) * 5
        margin += min(_h.resource_total(state), 12) // 2
        if not _h.has_role_gear(state, role):
            margin += 10
        if (state.step or 0) >= 2_500:
            margin += 10 if role in {"aligner", "scrambler"} else 5
        return hp <= safe_steps + margin

    def _nearest_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else None
        hubs = self._world_model.entities(entity_type="hub", predicate=lambda entity: entity.team == team_id)
        friendly_junctions = self._known_junctions(state, predicate=lambda entity: entity.owner == team_id)
        network_sources = [*hubs, *friendly_junctions]
        candidates = []
        for entity in self._known_junctions(state, predicate=lambda junction: junction.owner in {None, "neutral"}):
            if not _h.within_alignment_network(entity.position, network_sources):
                continue
            candidates.append(entity)
        if not candidates:
            return None
        directed_candidate = self._directive_target_candidate(candidates)
        if directed_candidate is not None:
            return directed_candidate
        enemy_junctions = self._known_junctions(
            state, predicate=lambda junction: junction.owner not in {None, "neutral", team_id},
        )
        unreachable = [
            entity
            for entity in self._known_junctions(state, predicate=lambda junction: junction.owner in {None, "neutral"})
            if entity not in candidates
        ]
        return min(
            candidates,
            key=lambda entity: (
                _h.v65_aligner_target_score(
                    current_position=current_pos,
                    candidate=entity,
                    unreachable=unreachable,
                    enemy_junctions=enemy_junctions,
                    claimed_by_other=_h.is_claimed_by_other(
                        claims=self._shared_claims,
                        candidate=entity.position,
                        agent_id=self._agent_id,
                        step=self._step_index,
                    ),
                    hub_position=hub_pos,
                ),
                entity.position,
            ),
        )

    def _preferred_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        candidate = self._nearest_alignable_neutral_junction(state)
        sticky = self._sticky_align_target(state)
        if sticky is None:
            return candidate
        if candidate is None:
            return sticky
        from cvc.cogent.player_cog.policy.semantic_cog import _TARGET_SWITCH_THRESHOLD
        current_pos = _h.absolute_position(state)
        team_id = _h.team_id(state)
        neutral_junctions = self._world_model.entities(
            entity_type="junction", predicate=lambda junction: junction.owner in {None, "neutral"},
        )
        enemy_junctions = self._world_model.entities(
            entity_type="junction", predicate=lambda junction: junction.owner not in {None, "neutral", team_id},
        )
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else None
        sticky_score = _h.v65_aligner_target_score(
            current_position=current_pos,
            candidate=sticky,
            unreachable=[entity for entity in neutral_junctions if entity.position != sticky.position],
            enemy_junctions=enemy_junctions,
            claimed_by_other=False,
            hub_position=hub_pos,
        )[0]
        candidate_score = _h.v65_aligner_target_score(
            current_position=current_pos,
            candidate=candidate,
            unreachable=[entity for entity in neutral_junctions if entity.position != candidate.position],
            enemy_junctions=enemy_junctions,
            claimed_by_other=_h.is_claimed_by_other(
                claims=self._shared_claims,
                candidate=candidate.position,
                agent_id=self._agent_id,
                step=self._step_index,
            ),
            hub_position=hub_pos,
        )[0]
        if candidate.position != sticky.position and candidate_score + _TARGET_SWITCH_THRESHOLD < sticky_score:
            return candidate
        return sticky


class AlphaV65ReplicaAgentPolicy(SemanticCogAgentPolicy):
    """Replica of v65 behavior: base budgets, no network/hotspot penalties, retreat_margin=15."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_weight = 0.0
        self._hotspot_weight = 0.0
        self._retreat_margin = 15  # v65 era used 15, not 20

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        return 0

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = self._retreat_margin
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 10
        margin += int(state.self_state.inventory.get("heart", 0)) * 5
        margin += min(_h.resource_total(state), 12) // 2
        if not _h.has_role_gear(state, role):
            margin += 10
        if (state.step or 0) >= 2_500:
            margin += 10 if role in {"aligner", "scrambler"} else 5
        return hp <= safe_steps + margin


class AlphaV65PlusBiasAgentPolicy(AlphaV65ReplicaAgentPolicy):
    """V65-style targeting + resource bias."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


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


class AlphaV65ScrambleHeavyAgentPolicy(AlphaV65ReplicaAgentPolicy):
    """V65 targeting + 3 scramblers."""

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

        pressure_budget = 6
        if min_res < 1 and not can_hearts:
            pressure_budget = 3

        scrambler_budget = min(3, pressure_budget // 2) if step >= 100 else 0
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaTeamAwareAgentPolicy(AlphaV65ReplicaAgentPolicy):
    """V65 targeting + team-size-aware budgets for tournament variable team sizes."""

    def _should_deposit_resources(self, state: MettagridState) -> bool:
        """Lower deposit threshold (12) for faster economy turnover."""
        cargo = _h.resource_total(state)
        if cargo <= 0:
            return False
        threshold = 12 if _h.has_role_gear(state, "miner") else 4
        if cargo >= threshold:
            return True
        safe_target = self._nearest_friendly_depot(state)
        if safe_target is None:
            return cargo >= 4
        safe_distance = _h.manhattan(_h.absolute_position(state), safe_target.position)
        if cargo >= 12 and safe_distance > 18:
            return True
        if cargo >= 8 and self._should_retreat(state, "miner", safe_target):
            return True
        if cargo >= 8 and self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            return True
        return False

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        # 2 agents: 1 aligner + 1 miner, no scrambler
        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0  # Both mine until economy is established
            if objective == "economy_bootstrap":
                return 1, 0
            return 1, 0

        # 3-4 agents: 2 aligners + rest miners, scrambler at step 200+
        if num_agents <= 4:
            if step < 30:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: base aggressive budgets
        if step < 30:
            pressure_budget = 2
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(2, num_agents // 4)
            elif min_res < 3:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 100:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaV65RealignAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 targeting + re-alignment boost + team-aware budgets + lower deposit.

    Best known targeting (hub_penalty) + prioritize re-aligning scrambled
    junctions + adapt to variable team sizes.
    """

    def _nearest_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        """V65 targeting with hotspot re-alignment boost."""
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else None
        hubs = self._world_model.entities(entity_type="hub", predicate=lambda entity: entity.team == team_id)
        friendly_junctions = self._known_junctions(state, predicate=lambda entity: entity.owner == team_id)
        network_sources = [*hubs, *friendly_junctions]
        candidates = []
        for entity in self._known_junctions(state, predicate=lambda junction: junction.owner in {None, "neutral"}):
            if not _h.within_alignment_network(entity.position, network_sources):
                continue
            candidates.append(entity)
        if not candidates:
            return None
        directed_candidate = self._directive_target_candidate(candidates)
        if directed_candidate is not None:
            return directed_candidate
        enemy_junctions = self._known_junctions(
            state, predicate=lambda junction: junction.owner not in {None, "neutral", team_id},
        )
        unreachable = [
            entity
            for entity in self._known_junctions(state, predicate=lambda junction: junction.owner in {None, "neutral"})
            if entity not in candidates
        ]
        return min(
            candidates,
            key=lambda entity: (
                _h.v65_aligner_target_score(
                    current_position=current_pos,
                    candidate=entity,
                    unreachable=unreachable,
                    enemy_junctions=enemy_junctions,
                    claimed_by_other=_h.is_claimed_by_other(
                        claims=self._shared_claims,
                        candidate=entity.position,
                        agent_id=self._agent_id,
                        step=self._step_index,
                    ),
                    hub_position=hub_pos,
                    hotspot_count=self._junction_hotspot_count(entity, hub),
                    hotspot_weight=8.0,
                ),
                entity.position,
            ),
        )

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        """Negative count = re-alignment bonus for recently scrambled junctions."""
        if hub is None:
            return 0
        rel = (entity.global_x - hub.global_x, entity.global_y - hub.global_y)
        count = self._shared_hotspots.get(rel, 0)
        return -min(count, 3)

    def _should_deposit_resources(self, state: MettagridState) -> bool:
        """Lower deposit threshold (12)."""
        cargo = _h.resource_total(state)
        if cargo <= 0:
            return False
        threshold = 12 if _h.has_role_gear(state, "miner") else 4
        if cargo >= threshold:
            return True
        safe_target = self._nearest_friendly_depot(state)
        if safe_target is None:
            return cargo >= 4
        safe_distance = _h.manhattan(_h.absolute_position(state), safe_target.position)
        if cargo >= 12 and safe_distance > 18:
            return True
        if cargo >= 8 and self._should_retreat(state, "miner", safe_target):
            return True
        if cargo >= 8 and self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            return True
        return False

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 20:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: v65-style budgets
        if step < 30:
            pressure_budget = 2
        elif step < 3000:
            pressure_budget = 5
            if min_res < 1 and not can_hearts:
                pressure_budget = 2
            elif min_res < 3:
                pressure_budget = 4
        else:
            pressure_budget = 6
            if min_res < 1 and not can_hearts:
                pressure_budget = 3

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = 2
        elif step >= 100:
            scrambler_budget = 1
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaV65TeamAwareAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 true targeting (hub_penalty) + team-size-aware budgets."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return 1, 0

        if num_agents <= 4:
            if step < 30:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: aggressive with floor of 3 to prevent gear oscillation
        if step < 30:
            pressure_budget = 2
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)  # Floor: keep roles stable
            elif min_res < 3:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 100:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaCleanTeamAwareAgentPolicy(SemanticCogAgentPolicy):
    """Base targeting (network weight) + team-size-aware budgets + resource bias."""

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return 1, 0

        if num_agents <= 4:
            if step < 30:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: base aggressive budgets with oscillation floor
        if step < 30:
            pressure_budget = 2
        elif step < 3000:
            pressure_budget = 5
            if min_res < 1 and not can_hearts:
                pressure_budget = 3  # Floor prevents gear churn
            elif min_res < 3:
                pressure_budget = 4
        else:
            pressure_budget = 6
            if min_res < 1 and not can_hearts:
                pressure_budget = 3

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = 2
        elif step >= 100:
            scrambler_budget = 1
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaRealignBoostAgentPolicy(AlphaV65ReplicaAgentPolicy):
    """Re-alignment boost: prioritize re-aligning recently scrambled junctions.

    Key insight: hotspot penalty DISCOURAGES re-aligning junctions we lost.
    But re-aligning is cheap (junction is already in our network) and high-value
    (restores score immediately). Flip the penalty to a bonus.

    Also: faster ramp, team-aware budgets, lower deposit threshold.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # CRITICAL: V65Replica sets hotspot_weight=0.0, which nullifies our boost.
        # Re-enable it so negative hotspot counts create bonuses.
        self._hotspot_weight = 8.0

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        """Return negative hotspot count = BONUS for re-alignment targets.

        With hotspot_weight=8.0, a count of -3 gives a bonus of -24 points,
        strongly prioritizing recently scrambled junctions for re-alignment.
        """
        if hub is None:
            return 0
        rel = (entity.global_x - hub.global_x, entity.global_y - hub.global_y)
        count = self._shared_hotspots.get(rel, 0)
        # Flip: recently scrambled junctions get a BONUS (negative count)
        # Cap at -3 to avoid over-prioritizing highly contested junctions
        return -min(count, 3)

    def _should_deposit_resources(self, state: MettagridState) -> bool:
        """Lower deposit threshold (12) for faster economy turnover."""
        cargo = _h.resource_total(state)
        if cargo <= 0:
            return False
        threshold = 12 if _h.has_role_gear(state, "miner") else 4
        if cargo >= threshold:
            return True
        safe_target = self._nearest_friendly_depot(state)
        if safe_target is None:
            return cargo >= 4
        safe_distance = _h.manhattan(_h.absolute_position(state), safe_target.position)
        if cargo >= 12 and safe_distance > 18:
            return True
        if cargo >= 8 and self._should_retreat(state, "miner", safe_target):
            return True
        if cargo >= 8 and self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            return True
        return False

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        # 2 agents: 1 aligner + 1 miner, no scrambler
        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            return 1, 0

        # 3-4 agents: fast ramp to 2 aligners
        if num_agents <= 4:
            if step < 20:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 200 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: aggressive ramp, 5 aligners at peak
        if step < 10:
            pressure_budget = 2
        elif step < 50:
            pressure_budget = 3  # Fast ramp: 3 aligners from step 10
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)  # 5 pressure, 1 scrambler
            if min_res < 1 and not can_hearts:
                pressure_budget = max(2, num_agents // 4)
            elif min_res < 3:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 100:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaMaxAlignAgentPolicy(AlphaV65ReplicaAgentPolicy):
    """Maximum alignment: 6 aligners, 0 scramblers for 8 agents.
    Tests whether pure alignment focus beats mixed strategy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hotspot_weight = 8.0

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        """Re-alignment boost (same as RealignBoost)."""
        if hub is None:
            return 0
        rel = (entity.global_x - hub.global_x, entity.global_y - hub.global_y)
        count = self._shared_hotspots.get(rel, 0)
        return -min(count, 3)

    def _should_deposit_resources(self, state: MettagridState) -> bool:
        cargo = _h.resource_total(state)
        if cargo <= 0:
            return False
        threshold = 12 if _h.has_role_gear(state, "miner") else 4
        if cargo >= threshold:
            return True
        safe_target = self._nearest_friendly_depot(state)
        if safe_target is None:
            return cargo >= 4
        safe_distance = _h.manhattan(_h.absolute_position(state), safe_target.position)
        if cargo >= 12 and safe_distance > 18:
            return True
        if cargo >= 8 and self._should_retreat(state, "miner", safe_target):
            return True
        return False

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 20:
                return 1, 0
            aligner_budget = min(num_agents - 1, 3)
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, 0  # No scramblers

        # 5+ agents: ALL pressure goes to alignment
        if step < 10:
            pressure_budget = 2
        elif step < 50:
            pressure_budget = 3
        else:
            pressure_budget = min(6, num_agents - 2)  # 6 aligners, 2 miners
            if min_res < 1 and not can_hearts:
                pressure_budget = max(2, num_agents // 4)
            elif min_res < 3:
                pressure_budget = min(4, num_agents - 2)

        if objective == "economy_bootstrap":
            return min(pressure_budget, 2), 0
        return pressure_budget, 0  # NO scramblers


class AlphaV65NoScrambleBoostAgentPolicy(AlphaV65RealignAgentPolicy):
    """V65Realign but with NO scramblers — all hearts go to alignment.

    Inherits V65 targeting + re-alignment boost + lower deposit threshold.
    Overrides budgets to remove scramblers entirely.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Team-aware budgets with NO scramblers."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 30 or (min_res < 1 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 20:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, 0

        # 5+ agents: all pressure to alignment, keep 3 miners
        if step < 30:
            return 2, 0
        aligner_budget = min(5, num_agents - 3)
        if min_res < 1 and not can_hearts:
            aligner_budget = max(2, num_agents // 4)
        elif min_res < 3:
            aligner_budget = min(4, num_agents - 3)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, 0


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


class AlphaV65TrueReplicaPolicy(MettagridSemanticPolicy):
    """True v65: uses original hub_penalty targeting with tiered distance costs."""
    short_names = ["alpha-v65-true"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65TrueReplicaAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


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


class AlphaV65ScrambleHeavyPolicy(MettagridSemanticPolicy):
    """V65 targeting + 3 scramblers. Best targeting + best disruption."""
    short_names = ["alpha-v65-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65ScrambleHeavyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaTeamAwarePolicy(MettagridSemanticPolicy):
    """V65 targeting + team-size-aware budgets for 2/4/6/8 agents."""
    short_names = ["alpha-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65RealignPolicy(MettagridSemanticPolicy):
    """V65 targeting + re-alignment boost + team-aware budgets."""
    short_names = ["alpha-v65-realign"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65RealignAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65TeamAwarePolicy(MettagridSemanticPolicy):
    """V65 true targeting (hub_penalty) + team-size-aware budgets."""
    short_names = ["alpha-v65-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65TeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaRealignBoostPolicy(MettagridSemanticPolicy):
    """Re-alignment boost + team-aware budgets + faster ramp."""
    short_names = ["alpha-realign-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaRealignBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaMaxAlignPolicy(MettagridSemanticPolicy):
    """Maximum alignment: 6 aligners, 0 scramblers."""
    short_names = ["alpha-max-align"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxAlignAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaCleanTeamAwarePolicy(MettagridSemanticPolicy):
    """Base targeting (network weights) + team-size-aware budgets + resource bias."""
    short_names = ["alpha-clean-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCleanTeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65NoScrambleBoostPolicy(MettagridSemanticPolicy):
    """V65 targeting + re-alignment boost + no scramblers."""
    short_names = ["alpha-v65-noscramble-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65NoScrambleBoostAgentPolicy(
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
