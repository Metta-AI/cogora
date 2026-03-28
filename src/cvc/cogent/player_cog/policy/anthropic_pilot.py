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

        # 3-4 agents: 2 aligners + rest miners, NO scrambler (economy too tight)
        if num_agents <= 4:
            if step < 20:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, 0  # No scramblers for small teams

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


class AlphaStableBoostAgentPolicy(AlphaRealignBoostAgentPolicy):
    """RealignBoost with more stable budgets to prevent role oscillation.

    Key change: tighter economy thresholds and higher floors prevent
    agents from oscillating between aligner and miner roles, which wastes
    gear and kills performance on marginal-economy seeds.
    """

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

        # 5+ agents: stable budgets with higher floors
        if step < 10:
            pressure_budget = 2
        elif step < 50:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)  # Floor 3, not 2
            elif min_res < 2:  # Tighter threshold: only drop at <2, not <3
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


class AlphaZoneBoostAgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with zone-based aligner targeting.

    Each aligner prefers junctions in their assigned sector (N/E/S/W),
    reducing travel time, target conflicts, and enabling faster re-alignment
    of recently scrambled junctions in their patrol area.
    """

    # Zone assignment by agent_id (angles in degrees, 0=North, clockwise)
    _ZONE_ANGLES = {
        0: 0,    # N
        1: 90,   # E
        2: 180,  # S
        4: 270,  # W
        5: 45,   # NE (5th aligner)
    }
    _ZONE_BONUS = 6.0  # Score bonus for junctions in agent's zone

    def _zone_score_bonus(self, entity: KnownEntity, hub: KnownEntity | None) -> float:
        """Return negative bonus (lower score = better) for junctions in agent's zone."""
        if hub is None or self._agent_id not in self._ZONE_ANGLES:
            return 0.0
        import math
        dx = entity.global_x - hub.global_x
        dy = entity.global_y - hub.global_y
        if dx == 0 and dy == 0:
            return 0.0
        # Angle from hub to junction (0=North, clockwise)
        angle = math.degrees(math.atan2(dx, -dy)) % 360
        zone_angle = self._ZONE_ANGLES[self._agent_id]
        # Angular distance (0-180)
        diff = abs(angle - zone_angle)
        if diff > 180:
            diff = 360 - diff
        # Bonus scales with proximity to zone center: full bonus at 0°, none at 90°+
        if diff >= 90:
            return 0.0
        return -self._ZONE_BONUS * (1.0 - diff / 90.0)

    def _nearest_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        """Standard targeting + zone preference bonus."""
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
                _h.aligner_target_score(
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
                    friendly_junctions=friendly_junctions,
                    hotspot_count=self._junction_hotspot_count(entity, hub),
                    network_weight=self._network_weight,
                    hotspot_weight=self._hotspot_weight,
                    expansion_weight=self._expansion_weight,
                    expansion_cap=self._expansion_cap,
                )[0] + self._zone_score_bonus(entity, hub),
                entity.position,
            ),
        )


class AlphaAggroBoostAgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with more aggressive heart batching and faster ramp.

    Changes from StableBoost:
    - Heart batch target 4 from step 200 (not 500), 5 from step 500 (not 2000)
    - Even faster ramp: 3 aligners from step 5 (not 10)
    - 2 scramblers from step 200 for 5+ agents (not just step 3000)
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 20 or (min_res < 1 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 15:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 150 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: faster ramp, earlier scramblers
        if step < 5:
            pressure_budget = 2
        elif step < 30:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)
            elif min_res < 2:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)

        # Earlier scrambler: 1 from step 50, 2 from step 200
        scrambler_budget = 0
        if step >= 200:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 50:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


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
    """Optimized agent policy: re-alignment boost + stable budgets + scrambler defense."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_budget_change_step = 0
        self._last_bias_resource: str | None = None
        # Init budget adapts to team size, capped to leave 1 miner
        num_agents = self.policy_env_info.num_agents
        self._current_aligner_budget = min(4, max(num_agents - 1, 1))
        # Match StableBoost proven config
        self._hotspot_weight = 8.0   # Re-alignment boost (flip hotspot to bonus)
        self._network_weight = 0.0   # No network proximity penalty (allows expansion)

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        """Flip hotspot count to BONUS — prioritize re-aligning scrambled junctions."""
        if hub is None:
            return 0
        rel = (entity.global_x - hub.global_x, entity.global_y - hub.global_y)
        count = self._shared_hotspots.get(rel, 0)
        return -min(count, 3)

    def _preferred_miner_extractor(self, state: MettagridState) -> KnownEntity | None:
        """Clear sticky target when resource priority changes significantly.

        Fixes: miners get locked to wrong resources via sticky targets even when
        a critical resource hits 0. This wastes mining capacity.
        """
        resources = _shared_resources(state)
        least = _least_resource(resources)
        least_amount = resources[least]

        if (
            self._sticky_target_kind is not None
            and self._sticky_target_kind.endswith("_extractor")
        ):
            current_resource = self._sticky_target_kind.removesuffix("_extractor")
            if current_resource != least:
                if least_amount < 7:
                    self._clear_sticky_target()
                elif least_amount > 0:
                    max_amount = max(resources.values())
                    if resources[current_resource] > max_amount * 0.8 and least_amount < max_amount * 0.5:
                        self._clear_sticky_target()

        if self._last_bias_resource is not None and self._last_bias_resource != self._resource_bias:
            if least_amount < 14:
                self._clear_sticky_target()
        self._last_bias_resource = self._resource_bias

        return super()._preferred_miner_extractor(state)

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Less conservative retreat (margin=15) + miner hub-distance check."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 15  # Less conservative than default 20
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 10
        margin += int(state.self_state.inventory.get("heart", 0)) * 5
        margin += min(_h.resource_total(state), 12) // 2
        if not _h.has_role_gear(state, role):
            margin += 10
        if (state.step or 0) >= 2_500:
            margin += 10 if role in {"aligner", "scrambler"} else 5
        if hp <= safe_steps + margin:
            return True
        # Miners: retreat if too far from hub
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 20:
                return True
        return False

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
        if cargo >= 8 and self._should_retreat(state, "miner", safe_target):
            return True
        return cargo >= 4 and safe_distance <= 3

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Extended aligner: when no frontier, walk toward nearest unreachable junction."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # No frontier junctions — try to expand toward known unreachable junctions
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else current_pos
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            # Filter to junctions we can safely reach: distance < hp - safety margin
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 30
                and _h.manhattan(hub_pos, j.position) < 40  # Don't go too far from hub
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            # Only expand if target is reasonably close
            if dist < hp - 30 and _h.manhattan(hub_pos, nearest.position) < 40:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # No expansion target — help economy by mining (idle-mine >> idle-explore in practice)
        return self._miner_action(state, summary_prefix="idle_align_")

    def evaluate_state(self, state: MettagridState) -> Action:
        action = super().evaluate_state(state)
        step = state.step or self._step_index
        role = self._infos.get("role", "?")
        subtask = self._infos.get("subtask", "?")
        # Log every 100 steps for agent 0 (detailed), every 500 for all
        if step % 500 == 0 or step == 1 or (step % 100 == 0 and self._agent_id == 0):
            pos = _h.absolute_position(state)
            hp = int(state.self_state.inventory.get("hp", 0))
            hearts = int(state.self_state.inventory.get("heart", 0))
            cargo = _h.resource_total(state)
            aligner_b = self._infos.get("aligner_budget", "?")
            scrambler_b = self._infos.get("scrambler_budget", "?")
            frontier = self._infos.get("frontier_neutral_junctions", "?")
            team_id = _h.team_id(state)
            friendly = len(self._world_model.entities(
                entity_type="junction", predicate=lambda e: e.owner == team_id))
            enemy = len(self._world_model.entities(
                entity_type="junction", predicate=lambda e: e.owner not in {None, "neutral", team_id}))
            shared = _shared_resources(state)
            hub = self._nearest_hub(state)
            hub_pos = (hub.global_x, hub.global_y) if hub else None
            print(
                f"[COG] step={step} agent={self._agent_id} pos={pos} hub={hub_pos} role={role} "
                f"subtask={subtask} hp={hp} hearts={hearts} cargo={cargo} "
                f"aligners={aligner_b} scramblers={scrambler_b} "
                f"friendly_j={friendly} enemy_j={enemy} frontier={frontier} "
                f"hub_res={shared}",
                flush=True,
            )
        return action

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Stable role allocation with resource-responsive scaling."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            # 2 agents: mine first 200 steps, then 1 aligner if economy supports it
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0  # Both mine to build economy
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0  # Economy-first: 1 aligner, rest mine
            # Only ramp up when economy can support it
            if min_res < 7:
                return 1, 0  # Keep mining until we have hearts capacity
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 500 and num_agents >= 4 and min_res >= 14 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: economy-responsive with aggressive peak
        if step < 30:
            return 2, 0
        elif step < 100:
            pressure_budget = 3  # Ramp up slowly
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            elif min_res < 7:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)

        # Scramblers: delay until economy can support it
        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


# Keep these for backwards compatibility with tournament uploads
class AnthropicPilotAgentPolicy(PilotAgentPolicy):
    _LLM_ANALYSIS_INTERVAL = 500  # Run LLM analysis every N steps

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_budget_change_step = 0
        num_agents = self.policy_env_info.num_agents
        self._current_aligner_budget = min(4, max(num_agents - 1, 1))

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Use LLM directive when available, fall back to heuristic resource bias."""
        # Let the pilot session provide the directive (incorporates runtime reviews)
        try:
            llm_directive = self._pilot_session.directive_for_state(state, memory=self._memory)
            # Always override resource_bias with heuristic (LLM can't see economy)
            resources = _shared_resources(state)
            least = _least_resource(resources)
            llm_directive = MacroDirective(
                resource_bias=least,
                objective=llm_directive.objective,
                note=llm_directive.note,
            )
            step = state.step or self._step_index
            if step > 0 and step % self._LLM_ANALYSIS_INTERVAL == 0:
                print(
                    f"[LLM] step={step} agent={self._agent_id} "
                    f"objective={llm_directive.objective} "
                    f"note={llm_directive.note} "
                    f"bias={least}",
                    flush=True,
                )
            return llm_directive
        except Exception as e:
            resources = _shared_resources(state)
            least = _least_resource(resources)
            return MacroDirective(resource_bias=least)

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
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65TrueReplicaAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65ReplicaPolicy(MettagridSemanticPolicy):
    """Replica of v65: base budgets, no network/hotspot penalties."""
    short_names = ["alpha-v65-replica"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65ReplicaAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65PlusBiasPolicy(MettagridSemanticPolicy):
    """V65 targeting + resource bias."""
    short_names = ["alpha-v65-bias"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65PlusBiasAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaBiasOnlyPolicy(MettagridSemanticPolicy):
    """Base policy + resource bias. Uses base budgets (aggressive like v65)."""
    short_names = ["alpha-bias-only"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaBiasOnlyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaDoubleScramblePolicy(MettagridSemanticPolicy):
    """Base + resource bias + 2 scramblers from step 100."""
    short_names = ["alpha-double-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaDoubleScrambleAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaSuperAggroPolicy(MettagridSemanticPolicy):
    """Maximum aggression: 6 pressure from step 30."""
    short_names = ["alpha-super-aggro"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSuperAggroAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaScrambleHeavyPolicy(MettagridSemanticPolicy):
    """3 scramblers + 3 aligners. Heavy disruption."""
    short_names = ["alpha-scramble-heavy"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaScrambleHeavyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65ScrambleHeavyPolicy(MettagridSemanticPolicy):
    """V65 targeting + 3 scramblers. Best targeting + best disruption."""
    short_names = ["alpha-v65-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65ScrambleHeavyAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaTeamAwarePolicy(MettagridSemanticPolicy):
    """V65 targeting + team-size-aware budgets for 2/4/6/8 agents."""
    short_names = ["alpha-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65RealignPolicy(MettagridSemanticPolicy):
    """V65 targeting + re-alignment boost + team-aware budgets."""
    short_names = ["alpha-v65-realign"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65RealignAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65TeamAwarePolicy(MettagridSemanticPolicy):
    """V65 true targeting (hub_penalty) + team-size-aware budgets."""
    short_names = ["alpha-v65-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65TeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaRealignBoostPolicy(MettagridSemanticPolicy):
    """Re-alignment boost + team-aware budgets + faster ramp."""
    short_names = ["alpha-realign-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaRealignBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaMaxAlignPolicy(MettagridSemanticPolicy):
    """Maximum alignment: 6 aligners, 0 scramblers."""
    short_names = ["alpha-max-align"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxAlignAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCleanTeamAwarePolicy(MettagridSemanticPolicy):
    """Base targeting (network weights) + team-size-aware budgets + resource bias."""
    short_names = ["alpha-clean-team-aware"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCleanTeamAwareAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaStableBoostPolicy(MettagridSemanticPolicy):
    """RealignBoost with stable budgets to prevent role oscillation."""
    short_names = ["alpha-stable-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaStableBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaZoneBoostPolicy(MettagridSemanticPolicy):
    """StableBoost with zone-based aligner targeting."""
    short_names = ["alpha-zone-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaZoneBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaGentleZoneAgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with gentler zone preference (bonus=3 instead of 6)."""

    _ZONE_ANGLES = {
        0: 0,    # N
        1: 90,   # E
        2: 180,  # S
        4: 270,  # W
        5: 45,   # NE
    }
    _ZONE_BONUS = 3.0  # Half of ZoneBoost's 6.0

    def _zone_score_bonus(self, entity: KnownEntity, hub: KnownEntity | None) -> float:
        if hub is None or self._agent_id not in self._ZONE_ANGLES:
            return 0.0
        import math
        dx = entity.global_x - hub.global_x
        dy = entity.global_y - hub.global_y
        if dx == 0 and dy == 0:
            return 0.0
        angle = math.degrees(math.atan2(dx, -dy)) % 360
        zone_angle = self._ZONE_ANGLES[self._agent_id]
        diff = abs(angle - zone_angle)
        if diff > 180:
            diff = 360 - diff
        if diff >= 90:
            return 0.0
        return -self._ZONE_BONUS * (1.0 - diff / 90.0)

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
                _h.aligner_target_score(
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
                    friendly_junctions=friendly_junctions,
                    hotspot_count=self._junction_hotspot_count(entity, hub),
                    network_weight=self._network_weight,
                    hotspot_weight=self._hotspot_weight,
                    expansion_weight=self._expansion_weight,
                    expansion_cap=self._expansion_cap,
                )[0] + self._zone_score_bonus(entity, hub),
                entity.position,
            ),
        )


class AlphaGentleZonePolicy(MettagridSemanticPolicy):
    """StableBoost with gentler zone preference."""
    short_names = ["alpha-gentle-zone"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaGentleZoneAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAggroBoostPolicy(MettagridSemanticPolicy):
    """StableBoost with aggressive heart batching and faster ramp."""
    short_names = ["alpha-aggro-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAggroBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65NoScrambleBoostPolicy(MettagridSemanticPolicy):
    """V65 targeting + re-alignment boost + no scramblers."""
    short_names = ["alpha-v65-noscramble-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65NoScrambleBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaNoScramblePolicy(MettagridSemanticPolicy):
    """All aligners, no scramblers."""
    short_names = ["alpha-no-scramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaNoScrambleAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaClusterBoostAgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with cluster-near-hub targeting.

    Key changes:
    - expansion_weight=0: don't prioritize frontier expansion
    - Agents target closest junctions, staying near hub
    - Faster re-alignment when junctions are lost (shorter travel)
    - Stronger re-align bonus (hotspot_weight=12 instead of 8)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 0.0
        self._expansion_cap = 0.0
        self._hotspot_weight = 12.0  # Stronger re-align bonus


class AlphaClusterBoostPolicy(MettagridSemanticPolicy):
    """StableBoost with cluster-near-hub targeting."""
    short_names = ["alpha-cluster-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaClusterBoostAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaMidExpansionAgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with reduced expansion and stronger re-alignment.

    Balance between cluster (expansion=0) and full expansion (expansion=10).
    Reduced expansion keeps agents closer to hub while still allowing
    some frontier pushing. Stronger re-alignment ensures lost junctions
    are quickly recaptured.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 3.0  # Reduced from 10.0
        self._expansion_cap = 20.0    # Reduced from 60.0
        self._hotspot_weight = 12.0   # Stronger re-align bonus


class AlphaMidExpansionPolicy(MettagridSemanticPolicy):
    """StableBoost with reduced expansion and stronger re-alignment."""
    short_names = ["alpha-mid-expansion"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMidExpansionAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaDoubleScrambleMidAgentPolicy(AlphaMidExpansionAgentPolicy):
    """MidExpansion with 2 scramblers from step 100 (instead of 1).

    Hypothesis: more scrambling reduces junction losses, improving net score.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        aligner_budget, scrambler_budget = super()._pressure_budgets(state, objective=objective)
        step = state.step or self._step_index
        num_agents = self.policy_env_info.num_agents
        if num_agents >= 5 and step >= 100 and aligner_budget >= 2:
            # Use 2 scramblers instead of 1, taking from aligners
            scrambler_budget = 2
            aligner_budget = max(aligner_budget - 1, 2)
        return aligner_budget, scrambler_budget


class AlphaDoubleScrambleMidPolicy(MettagridSemanticPolicy):
    """MidExpansion with 2 scramblers."""
    short_names = ["alpha-double-scramble-mid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaDoubleScrambleMidAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaMidZoneAgentPolicy(AlphaZoneBoostAgentPolicy):
    """ZoneBoost with reduced expansion and stronger re-alignment."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 3.0
        self._expansion_cap = 20.0
        self._hotspot_weight = 12.0


class AlphaMidZonePolicy(MettagridSemanticPolicy):
    """ZoneBoost with reduced expansion and stronger re-alignment."""
    short_names = ["alpha-mid-zone"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMidZoneAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaExp5AgentPolicy(AlphaStableBoostAgentPolicy):
    """StableBoost with expansion_weight=5 and hotspot=12."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 5.0
        self._expansion_cap = 30.0
        self._hotspot_weight = 12.0


class AlphaExp5Policy(MettagridSemanticPolicy):
    """StableBoost with expansion_weight=5."""
    short_names = ["alpha-exp5"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaExp5AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaTurboMidAgentPolicy(AlphaMidExpansionAgentPolicy):
    """MidExpansion with faster early ramp and late-game double scrambler.

    Early game (steps 0-3000): faster ramp to max aligners
    Late game (steps 3000+): add second scrambler to protect gains
    """

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
            if step < 15:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 150 and num_agents >= 4 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return min(aligner_budget, 1), 0
            return aligner_budget, scrambler_budget

        # 5+ agents: faster early ramp
        if step < 5:
            pressure_budget = 2
        elif step < 30:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(3, num_agents // 3)
            elif min_res < 2:
                pressure_budget = min(4, num_agents - 2)
        else:
            # Late game: 6 pressure with 2 scramblers
            pressure_budget = min(6, num_agents - 1)
            if min_res < 1 and not can_hearts:
                pressure_budget = max(4, num_agents // 3)

        scrambler_budget = 0
        if step >= 3000:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 100:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaTurboMidPolicy(MettagridSemanticPolicy):
    """MidExpansion with faster ramp and late-game double scrambler."""
    short_names = ["alpha-turbo-mid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTurboMidAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaHybridAgentPolicy(AlphaCogAgentPolicy):
    """Hybrid: v65 hub-penalty targeting + AlphaCog economy/budgets + re-alignment bonus.

    Key insight: v65's hub_penalty keeps expansion tight (reduces death risk,
    travel time) while AlphaCog's economy management prevents starvation.
    Adding hotspot bonus helps reclaim scrambled territory faster.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hotspot_weight = 8.0  # Keep re-alignment bonus
        self._network_weight = 0.0  # Not used — hub_penalty replaces it

    def _nearest_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        """Use v65's hub_penalty targeting with hotspot bonus."""
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
                    hotspot_weight=self._hotspot_weight,
                ),
                entity.position,
            ),
        )

    def _preferred_alignable_neutral_junction(self, state: MettagridState) -> KnownEntity | None:
        """Sticky target with v65 scoring + hotspot bonus."""
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
            hotspot_count=self._junction_hotspot_count(sticky, hub),
            hotspot_weight=self._hotspot_weight,
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
            hotspot_count=self._junction_hotspot_count(candidate, hub),
            hotspot_weight=self._hotspot_weight,
        )[0]
        if candidate.position != sticky.position and candidate_score + _TARGET_SWITCH_THRESHOLD < sticky_score:
            return candidate
        return sticky

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Tuned for tournament: 75% of games are 2-4 agents. More conservative scrambling."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 80:
                return 1, 0  # Fast ramp: 1 aligner from step 0
            if min_res < 7:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            # No scramblers in small teams — all resources to alignment
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, 0

        # 5+ agents
        if step < 30:
            return 2, 0
        elif step < 100:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            elif min_res < 7:
                pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 500 and min_res >= 14:
            scrambler_budget = min(1, pressure_budget // 3)
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaHybridPolicy(MettagridSemanticPolicy):
    """Hybrid policy: v65 targeting + AlphaCog economy."""
    short_names = ["alpha-hybrid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaHybridAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaSoftHubAgentPolicy(AlphaCogAgentPolicy):
    """AlphaCog + mild hub proximity preference (network_weight=0.5).

    v65's hub_penalty was too harsh (kills self-play scores).
    network_weight=0.0 (AlphaCog) has no hub preference at all.
    This uses network_weight=0.5 as a soft middle ground.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._network_weight = 0.5  # Mild hub/network preference


class AlphaSoftHubPolicy(MettagridSemanticPolicy):
    """AlphaCog with mild hub proximity preference."""
    short_names = ["alpha-softhub"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSoftHubAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCyborgPolicy(MettagridSemanticPolicy):
    """Lightweight policy without LLM dependencies."""
    short_names = ["alpha-cyborg"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCogAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCyborgGlobalRolesPolicy(MettagridSemanticPolicy):
    """All AlphaCog improvements + global role assignment (like v65)."""
    short_names = ["alpha-cyborg-global"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # Do NOT pass shared_team_ids — use global role priorities like v65
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCogAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                # No shared_team_ids → global role priorities like v65
            )
        return self._agent_policies[agent_id]


class AlphaV65BuggyStationAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 replica with original station targeting bug (pre-fix behavior)."""

    def _acquire_role_gear(self, state: MettagridState, role: str) -> tuple[Action, str]:
        """Replicate pre-fix station targeting: use raw spawn-relative coords."""
        station_type = f"{role}_station"
        current_pos = _h.absolute_position(state)
        station = self._world_model.nearest(position=current_pos, entity_type=station_type)
        if station is not None:
            return self._move_to_known(state, station, summary=f"get_{role}_gear", vibe="change_vibe_gear")
        # OLD BUG: use spawn-relative coords as absolute (sends agents to wrong position)
        target = _h.spawn_relative_station_target(self._agent_id, role)
        if target is None:
            hub = self._nearest_hub(state)
            if hub is None:
                return self._explore_action(state, role=role, summary=f"find_{role}_station")
            from cvc.cogent.player_cog.policy.semantic_cog import _STATION_OFFSETS
            dx, dy = _STATION_OFFSETS[role]
            target = (hub.global_x + dx, hub.global_y + dy)
        return self._move_to_position(state, target, summary=f"search_{role}_station", vibe="change_vibe_gear")


class AlphaV65BuggyStationPolicy(MettagridSemanticPolicy):
    """V65 replica with station targeting bug + global roles."""
    short_names = ["alpha-v65-buggy-station"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65BuggyStationAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65OriginalPolicy(MettagridSemanticPolicy):
    """True v65 replica WITHOUT team-relative role assignment.

    v65 was uploaded before the shared_team_ids fix, so it uses global agent IDs
    for role assignment. This replicates that exact behavior.
    """
    short_names = ["alpha-v65-original"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # Do NOT pass shared_team_ids — v65 used global role assignment
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


class AlphaV65ExactAgentPolicy(SemanticCogAgentPolicy):
    """Exact v65 agent: original constants, budgets, priorities.

    Matches v65's original behavior:
    - pressure_budget=4 immediate, 5 when resources>=20
    - Scrambler at step 1500 (not 100)
    - No early-game survival logic overrides
    - No hotspot tracking (weight=0)
    - No network weight
    """

    # v65 original priorities
    _V65_ALIGNER_PRIORITY = (4, 5, 6, 7, 3)
    _V65_SCRAMBLER_PRIORITY = (7, 6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hotspot_weight = 0.0   # v65 had no hotspot tracking
        self._network_weight = 0.0   # v65 had no network penalty

    def _desired_role(self, state: MettagridState, *, objective: str | None = None) -> str:
        """v65 role assignment: agents 4,5,6,7 are aligners, 7,6 are scramblers."""
        aligner_budget, scrambler_budget = self._pressure_budgets(state, objective=objective)
        scrambler_ids = set(self._V65_SCRAMBLER_PRIORITY[:scrambler_budget])
        aligner_ids = []
        for agent_id in self._V65_ALIGNER_PRIORITY:
            if agent_id in scrambler_ids:
                continue
            if len(aligner_ids) == aligner_budget:
                break
            aligner_ids.append(agent_id)
        if self._agent_id in scrambler_ids:
            return "scrambler"
        if self._agent_id in aligner_ids:
            return "aligner"
        return "miner"

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """v65 original: simple 4-aligner budget, scrambler at step 1500."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)

        if objective == "resource_coverage":
            return 0, 0

        pressure_budget = 4
        if step >= 40 and min_res >= 20:
            pressure_budget = 5

        scrambler_budget = 0
        if step >= 1_500:
            scrambler_budget = 1
        aligner_budget = pressure_budget - scrambler_budget

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaV65ExactPolicy(MettagridSemanticPolicy):
    """Exact v65 replica: original constants, global role assignment, simple budgets."""
    short_names = ["alpha-v65-exact"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # No shared_team_ids — v65 used global role priorities
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65ExactAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaTournamentAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """Tournament-optimized: v65 targeting + idle-mine + team-aware budgets.

    Combines proven tournament elements:
    - v65 hub_penalty targeting (conservative, stays near hub — safer in PvP)
    - Idle aligners mine instead of exploring (biggest local improvement: +89%)
    - Team-size-aware budgets (handles 2v6, 4v4, 6v2 tournament formats)
    - Default retreat margin (20) for better survivability in PvP
    """

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Default retreat margin (20) — more conservative than v65's 15 for PvP safety."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 20  # More conservative for tournament PvP
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 10
        margin += int(state.self_state.inventory.get("heart", 0)) * 5
        margin += min(_h.resource_total(state), 12) // 2
        if not _h.has_role_gear(state, role):
            margin += 10
        if (state.step or 0) >= 2_500:
            margin += 10 if role in {"aligner", "scrambler"} else 5
        return hp <= safe_steps + margin

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting with idle-mine: when no frontier junctions, mine to boost economy."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # No frontier — explore to find new junctions (avoid _miner_action to prevent gear churn)
        return self._explore_action(state, role="aligner", summary="idle_explore")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy-first budgets for tournament — build economy before aggression."""
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
            if step < 100:
                return 1, 0  # Economy-first: 1 aligner, rest mine
            if min_res < 7:
                return 1, 0  # Keep mining until hearts capacity
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 500 and num_agents >= 4 and min_res >= 14 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: economy-responsive
        if step < 30:
            pressure_budget = 2
        elif step < 100:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = 5
            if min_res < 3 and not can_hearts:
                pressure_budget = 2
            elif min_res < 7:
                pressure_budget = 4
        else:
            pressure_budget = 6
            if min_res < 3 and not can_hearts:
                pressure_budget = 2

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = 2
        elif step >= 100:
            scrambler_budget = 1
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaTournamentPolicy(MettagridSemanticPolicy):
    """Tournament-optimized: v65 targeting + idle-mine + team-aware."""
    short_names = ["alpha-tournament"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65IdleMinePolicy(MettagridSemanticPolicy):
    """V65 targeting + global roles (like v65) + idle-mine improvement.

    Combines the proven v65 tournament formula (global role assignment,
    hub_penalty targeting) with the biggest local improvement (idle-mine).
    Does NOT use shared_team_ids to match v65's behavior.
    """
    short_names = ["alpha-v65-idle-mine"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # Do NOT pass shared_team_ids — match v65's global role assignment
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                # No shared_team_ids → global role priorities like v65
            )
        return self._agent_policies[agent_id]


class AlphaV65HybridAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 budgets + team-relative roles + idle-mine.

    The key insight: v65's tournament success comes from its aggressive
    budget (4 aligners from step 0). Previous "improvements" delayed
    aligners with economy-first budgets, which loses territory in PvP.

    This hybrid keeps v65's proven budgets and targeting, adds:
    - Team-relative role assignment (works for any team size)
    - Idle-mine for aligners when no frontier (biggest local gain)
    - Logging for tournament debugging
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable network/hotspot weights like v65
        self._network_weight = 0.0
        self._hotspot_weight = 0.0

    def _choose_action(self, state: MettagridState, role: str) -> tuple[Action, str]:
        """Override to skip early-game survival code (hub_camp_heal, wipeout_hub_hold).

        V65 doesn't have these — agents play immediately. The survival code
        wastes early steps and causes permanent stalls at hp=0.
        """
        if role not in {"aligner", "miner"}:
            self._clear_target_claim()
            self._clear_sticky_target()
        elif role == "aligner" and self._sticky_target_kind not in {None, "junction"}:
            self._clear_sticky_target()
        elif role == "miner" and (
            self._sticky_target_kind is not None and not self._sticky_target_kind.endswith("_extractor")
        ):
            self._clear_sticky_target()

        safe_target = self._nearest_hub(state)

        # Skip early-game survival code — go straight to retreat like v65
        if self._should_retreat(state, role, safe_target):
            self._clear_target_claim()
            self._clear_sticky_target()
            if safe_target is not None:
                safe_distance = _h.manhattan(_h.absolute_position(state), safe_target.position)
                if safe_distance > 2:
                    return self._move_to_known(state, safe_target, summary="retreat_to_hub")
            if _h.has_role_gear(state, role):
                return self._hold(summary="retreat_hold", vibe="change_vibe_default")

        if self._oscillation_steps >= 4:
            return self._unstick_action(state, role)

        if self._stalled_steps >= 12:
            return self._unstick_action(state, role)

        if role != "miner" and _h.needs_emergency_mining(state):
            return self._miner_action(state, summary_prefix="emergency_")

        if self._should_deposit_resources(state):
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_resources")

        if not _h.has_role_gear(state, role):
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_afford_gear(state, role):
                return self._miner_action(state, summary_prefix=f"fund_{role}_gear_")
            return self._acquire_role_gear(state, role)

        if role == "aligner":
            return self._aligner_action(state)
        elif role == "scrambler":
            return self._scrambler_action(state)
        else:
            return self._miner_action(state)

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting with idle-mine fallback."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # No frontier — mine to help economy instead of wandering
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """V65-style aggressive budgets, adapted for variable team sizes.

        V65 original: pressure=4 from step 0, ramp to 5 when rich, scrambler at 1500+.
        This adapts that for smaller teams while keeping the same philosophy:
        get aligners out ASAP, don't delay for economy.
        """
        step = state.step or self._step_index
        num_agents = self.policy_env_info.num_agents
        min_res = _h.team_min_resource(state)

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            # 2 agents: mine first to build economy, then 1 aligner
            if step < 200 or (min_res < 7 and not _h.team_can_refill_hearts(state)):
                return 0, 0  # Both mine
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            # 4 agents: 2 aligners + 2 miners (v65 ratio: half align, half mine)
            pressure = min(2, num_agents - 1)
            if step >= 40 and min_res >= 14:
                pressure = min(3, num_agents - 1)
            scrambler = 1 if step >= 1500 else 0
            aligner = max(pressure - scrambler, 1)
            if objective == "economy_bootstrap":
                return min(aligner, 2), 0
            return aligner, scrambler

        # 5+ agents: v65 original budgets
        pressure = 4
        if step >= 40 and min_res >= 20:
            pressure = 5

        scrambler = 0
        if step >= 1500:
            scrambler = 1
        if step >= 5000 and _h.team_can_refill_hearts(state):
            scrambler = 2
        aligner = pressure - scrambler
        if objective == "economy_bootstrap":
            return min(aligner, 2), 0
        return aligner, scrambler

    def evaluate_state(self, state: MettagridState) -> Action:
        action = super().evaluate_state(state)
        step = state.step or self._step_index
        if step % 500 == 0 or step == 1:
            pos = _h.absolute_position(state)
            hp = int(state.self_state.inventory.get("hp", 0))
            hearts = int(state.self_state.inventory.get("heart", 0))
            cargo = _h.resource_total(state)
            role = self._infos.get("role", "?")
            subtask = self._infos.get("subtask", "?")
            aligner_b = self._infos.get("aligner_budget", "?")
            scrambler_b = self._infos.get("scrambler_budget", "?")
            team_id = _h.team_id(state)
            friendly = len(self._world_model.entities(
                entity_type="junction", predicate=lambda e: e.owner == team_id))
            print(
                f"[COG] step={step} agent={self._agent_id} pos={pos} role={role} "
                f"subtask={subtask} hp={hp} hearts={hearts} cargo={cargo} "
                f"aligners={aligner_b} scramblers={scrambler_b} friendly_j={friendly}",
                flush=True,
            )
        return action

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaV65HybridPolicy(MettagridSemanticPolicy):
    """V65 hybrid: v65 budgets + team-aware roles + idle-mine."""
    short_names = ["alpha-v65-hybrid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65HybridAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaV65HybridGlobalPolicy(MettagridSemanticPolicy):
    """V65 hybrid with global roles (no team-relative) — closer to original v65."""
    short_names = ["alpha-v65-hybrid-global"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65HybridAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                # No shared_team_ids → global role priorities like v65
            )
        return self._agent_policies[agent_id]


class AlphaWaveAgentPolicy(AlphaV65HybridAgentPolicy):
    """Wave strategy: economy-first, then mass alignment.

    Phase 1 (step 0-199): ALL mine — build massive resource stockpile
    Phase 2 (step 200-499): 6 aligners + 2 miners — rapid territory grab
    Phase 3 (step 500+): 5 aligners + 1 scrambler + 2 miners — hold territory
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 100:
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 150:
                return 0, 0  # All mine
            if step < 400:
                return min(3, num_agents - 1), 0  # Mass align
            return min(2, num_agents - 1), 1  # Hold + scramble

        # 5+ agents
        if step < 150:
            return 0, 0  # Phase 1: ALL MINE
        if step < 500:
            return min(6, num_agents - 2), 0  # Phase 2: MASS ALIGN
        # Phase 3: Hold + scramble
        scrambler = min(2, num_agents // 4)
        aligner = min(5, num_agents - 2 - scrambler)
        if objective == "economy_bootstrap":
            return min(aligner, 2), 0
        return aligner, scrambler


class AlphaWavePolicy(MettagridSemanticPolicy):
    """Wave strategy: economy-first, then mass alignment."""
    short_names = ["alpha-wave"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaWaveAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaMaxPressureAgentPolicy(AlphaV65HybridAgentPolicy):
    """Maximum pressure from step 0: 6 aligners + 2 miners.

    Skip economy buildup entirely. The starting resources (24 each)
    give 3 hearts. Use them immediately and mine to sustain.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            return 1, 0

        if num_agents <= 4:
            aligner = num_agents - 1  # All but 1 align
            scrambler = 1 if step >= 1000 else 0
            aligner = max(aligner - scrambler, 1)
            return aligner, scrambler

        # 5+ agents: maximum alignment pressure
        aligner = max(num_agents - 2, 4)  # 6 aligners for 8 agents
        scrambler = 0
        if step >= 2000:
            scrambler = 1
            aligner -= 1
        if objective == "economy_bootstrap":
            return min(aligner, 3), 0
        return aligner, scrambler


class AlphaMaxPressurePolicy(MettagridSemanticPolicy):
    """Maximum pressure: 6 aligners from step 0."""
    short_names = ["alpha-max-pressure"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxPressureAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaFlashRushAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """Flash Rush: all-mine first 50 steps, then mass-align with 6 aligners + 1 scrambler.

    Theory: front-load economy to sustain maximum territorial pressure.
    Instead of gradual scaling, we burst with maximum force after building reserves.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 50 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 50:
                return 0, 0  # All mine
            if min_res < 3 and not can_hearts:
                return 1, 0
            return min(3, num_agents - 1), 0

        # 5+ agents: ALL mine for 50 steps, then flash rush
        if step < 50:
            return 0, 0  # ALL mine — build economy reserves

        # After step 50: maximum pressure
        if min_res < 3 and not can_hearts:
            # Economy emergency — pull back
            return 2, 0

        # Normal: 6 aligners + 1 scrambler (1 miner)
        if step < 200:
            # Pure alignment rush — no scramblers yet
            aligner_budget = min(num_agents - 1, 7)  # Leave just 1 miner
            if objective == "economy_bootstrap":
                return min(aligner_budget, 3), 0
            return aligner_budget, 0

        # After step 200: add scrambler
        scrambler_budget = 1
        aligner_budget = min(num_agents - 2, 6)  # 6 aligners + 1 scrambler + 1 miner
        if step >= 3000:
            scrambler_budget = 2
            aligner_budget = min(num_agents - 3, 5)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 3), 0
        return aligner_budget, scrambler_budget

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting with idle-explore (avoid gear churn)."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # No frontier — explore to find new junctions (avoid gear churn)
        return self._explore_action(state, role="aligner", summary="idle_explore")

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaFlashRushPolicy(MettagridSemanticPolicy):
    """Flash Rush: all-mine 50 steps, then mass-align."""
    short_names = ["alpha-flash-rush"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaFlashRushAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaEconDominanceAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """Economic Dominance: keep 5 miners throughout, but use 2 very efficient aligners.

    Theory: with massive economy, aligners always have hearts and can work non-stop.
    Fewer aligners but they never idle waiting for hearts.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 100:
                return 0, 0  # Both mine
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 0, 0  # All mine first
            return 1, 1 if step >= 500 else 0  # Just 1 aligner + maybe 1 scrambler

        # 5+ agents: economy-heavy — only 2 aligners, 1 scrambler, 5 miners
        if step < 100:
            return 1, 0  # 1 aligner to start exploring while miners build economy
        if step < 500:
            return 2, 0  # 2 aligners, 6 miners

        # After 500: 2 aligners + 1 scrambler + 5 miners
        scrambler_budget = 1
        if min_res < 3 and not can_hearts:
            return 1, 0  # Economy crisis
        if objective == "economy_bootstrap":
            return 1, 0
        return 2, scrambler_budget

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Idle-explore for aligners."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        return self._explore_action(state, role="aligner", summary="idle_explore")

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaEconDominancePolicy(MettagridSemanticPolicy):
    """Economic Dominance: heavy mining, few but efficient aligners."""
    short_names = ["alpha-econ-dominance"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconDominanceAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaScrambleDominanceAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """Scramble Dominance: 4-5 scramblers + 2 aligners + 1-2 miners.

    Theory: overwhelm enemy with scramblers to keep them at 0 junctions.
    Even 3-4 friendly junctions = huge score advantage if enemy holds 0.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            return 0, 1 if step >= 200 else (1, 0)

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            return 1, min(2, num_agents - 2)

        # 5+ agents: scramble-heavy
        if step < 50:
            return 2, 0  # Quick territory grab
        if step < 200:
            return 2, 2  # 2 aligners + 2 scramblers + 4 miners

        if min_res < 3 and not can_hearts:
            return 1, 1

        # 2 aligners + 4 scramblers + 2 miners
        scrambler_budget = min(4, num_agents - 3)
        aligner_budget = 2
        if objective == "economy_bootstrap":
            return 1, 1
        return aligner_budget, scrambler_budget

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Idle-explore for aligners."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        return self._explore_action(state, role="aligner", summary="idle_explore")

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaScrambleDominancePolicy(MettagridSemanticPolicy):
    """Scramble Dominance: overwhelm with scramblers, hold few junctions."""
    short_names = ["alpha-scramble-dominance"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaScrambleDominanceAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaHybridAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """Hybrid: v65 conservative targeting + re-alignment boost + idle-mine + AT budgets.

    Combines:
    - v65 hub_penalty targeting (conservative, proven in tournament)
    - Re-alignment boost from AlphaCyborg (hotspot flip)
    - Idle-mine for economy boost when no junctions to align
    - AlphaTournament's economy-first budgets
    - Retreat margin 20 (conservative for PvP)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hotspot_weight = 8.0  # Re-alignment boost (flip hotspot to bonus)

    def _junction_hotspot_count(self, entity: KnownEntity, hub: KnownEntity | None) -> int:
        """Flip hotspot count to BONUS — prioritize re-aligning scrambled junctions."""
        if hub is None:
            return 0
        rel = (entity.global_x - hub.global_x, entity.global_y - hub.global_y)
        count = self._shared_hotspots.get(rel, 0)
        return -min(count, 3)

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting + idle-mine (when no frontier junctions, mine for economy)."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # No frontier — mine for economy (idle-mine >> idle-explore)
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """AlphaTournament economy-first budgets."""
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
            if step < 100:
                return 1, 0
            if min_res < 7:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 500 and num_agents >= 4 and min_res >= 14 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 30:
            pressure_budget = 2
        elif step < 100:
            pressure_budget = 3
        elif step < 3000:
            pressure_budget = 5
            if min_res < 3 and not can_hearts:
                pressure_budget = 2
            elif min_res < 7:
                pressure_budget = 4
        else:
            pressure_budget = 6
            if min_res < 3 and not can_hearts:
                pressure_budget = 2

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = 2
        elif step >= 100:
            scrambler_budget = 1
        aligner_budget = max(pressure_budget - scrambler_budget, 0)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)


class AlphaHybridPolicy(MettagridSemanticPolicy):
    """Hybrid: v65 targeting + re-alignment boost + idle-mine + AT budgets."""
    short_names = ["alpha-hybrid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaHybridAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


# Re-export the ORIGINAL pre-rewrite semantic_cog for pure v65 testing
from cvc.cogent.player_cog.policy.semantic_cog_v65 import (
    MettagridSemanticPolicy as _V65BasePolicy,
)


class AlphaV65PurePolicy(_V65BasePolicy):
    """Pure v65: uses the ORIGINAL semantic_cog.py from before any modifications.

    This bypasses ALL changes made in the rewrite (b882dbf) and later commits.
    If this matches v65's 3.59, the rewrite itself is the problem.
    """
    short_names = ["alpha-v65-pure"]


class AlphaSmallTeamAgentPolicy(AlphaCogAgentPolicy):
    """Optimized for tournament's 4-agent games with 1-3 agent team sizes.

    Key changes from AlphaCog:
    - 1-2 agents: Rush alignment immediately (hub has 5 free hearts)
    - No mining phase for tiny teams — hearts are free, align first
    - After hearts spent, mine to replenish then align again
    - Better economy: mine least resource specifically
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Small-team-optimized budgets: align first, mine later.

        KEY INSIGHT: Hub starts with 5 hearts regardless of team size.
        Small teams should rush alignment with free hearts before mining.
        state.team_summary may be None early (hub not yet observed), so
        we assume starting resources are available.
        """
        step = state.step or self._step_index
        num_agents = self.policy_env_info.num_agents

        # Check actual hub state, but assume positive for early steps
        has_team_summary = state.team_summary is not None
        min_res = _h.team_min_resource(state) if has_team_summary else (num_agents * 3)
        can_hearts = _h.team_can_refill_hearts(state) if has_team_summary else True

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 1:
            # Solo agent: ALWAYS be aligner (mine as idle activity when no hearts)
            # Hub has 5 free hearts at start — use them immediately
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0  # Always try to align

        if num_agents <= 2:
            # 2 agents: 1 aligner from step 0 (free hearts!)
            if objective == "economy_bootstrap" and not can_hearts:
                return 0, 0
            return 1, 0  # One aligns, one mines

        if num_agents <= 4:
            # 3-4 agents: aggressive alignment from start
            if step < 50:
                return min(2, num_agents - 1), 0  # Align with free hearts
            if min_res < 3 and not can_hearts:
                return 1, 0  # Keep 1 aligner, rest mine
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 500 and num_agents >= 4 and min_res >= 14 else 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: use parent's logic
        return super()._pressure_budgets(state, objective=objective)


class AlphaSmallTeamPolicy(MettagridSemanticPolicy):
    """Tournament-optimized policy for small team games (1-4 agents)."""
    short_names = ["alpha-small-team"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSmallTeamAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaExpanderAgentPolicy(AlphaCogAgentPolicy):
    """Better network expansion when frontier stalls (frontier=0).

    Key change: more aggressive expansion toward unreachable junctions.
    When no frontier exists, walk toward unreachable junctions to bring them
    into alignment range, rather than idle-mining.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Extended aligner with aggressive expansion when frontier stalls."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # AGGRESSIVE EXPANSION: walk toward unreachable junctions to bring them into range
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub_pos = hub.position if hub is not None else current_pos
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable and hp > 20:
            # Find the closest unreachable junction that's between us and the frontier edge
            # More aggressive: allow expansion up to 50 tiles from hub (was 40)
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20  # Less safety margin (was 30)
                and _h.manhattan(hub_pos, j.position) < 50  # Wider range (was 40)
            ]
            if safe_unreachable:
                # Prefer junctions that are closest to an existing friendly junction
                # (most likely to become alignable when we walk near them)
                team_id = _h.team_id(state)
                friendly = self._known_junctions(state, predicate=lambda j: j.owner == team_id)
                if friendly:
                    nearest = min(safe_unreachable, key=lambda j: min(
                        _h.manhattan(j.position, f.position) for f in friendly
                    ))
                else:
                    nearest = min(safe_unreachable, key=lambda j: _h.manhattan(current_pos, j.position))
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

            # If no safe targets, try the nearest unreachable anyway if HP allows
            nearest = min(unreachable, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_risky", vibe="change_vibe_aligner")

        # Fallback: mine while waiting
        return self._miner_action(state, summary_prefix="idle_align_")


class AlphaExpanderPolicy(MettagridSemanticPolicy):
    """AlphaCyborg + aggressive network expansion."""
    short_names = ["alpha-expander"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaExpanderAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptivePolicy(MettagridSemanticPolicy):
    """Adaptive policy: AlphaCyborg for small teams, Expander for large teams.

    Tournament is 75% 4-agent (where AlphaCyborg excels) and 25% 8-agent
    (where Expander excels). This policy adapts to team size for best overall.
    """
    short_names = ["alpha-adaptive"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        num_agents = self.policy_env_info.num_agents
        if agent_id not in self._agent_policies:
            # Use Expander for 5+ agents, AlphaCog for small teams
            policy_cls = AlphaExpanderAgentPolicy if num_agents >= 5 else AlphaCogAgentPolicy
            self._agent_policies[agent_id] = policy_cls(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaEconFixAgentPolicy(AlphaCogAgentPolicy):
    """Fix miner resource-switching: clear sticky target when resource priority shifts.

    Key insight: miners get locked to wrong resources via sticky targets even when
    a critical resource (like carbon) hits 0. This wastes mining capacity.

    Also uses v65-style budgets (4 aligners early) with earlier scramblers.
    Disables hotspot weight (hurts in tournament per prior testing).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_bias_resource: str | None = None
        # Disable hotspot weight — confirmed to hurt tournament performance
        self._hotspot_weight = 0.0

    def _preferred_miner_extractor(self, state: MettagridState) -> KnownEntity | None:
        """Override: clear sticky target when resource priority changes significantly."""
        resources = _shared_resources(state)
        least = _least_resource(resources)
        least_amount = resources[least]

        if (
            self._sticky_target_kind is not None
            and self._sticky_target_kind.endswith("_extractor")
        ):
            current_resource = self._sticky_target_kind.removesuffix("_extractor")
            if current_resource != least:
                # Critical shortage: switch immediately
                if least_amount < 7:
                    self._clear_sticky_target()
                # Resource imbalance: mining the most abundant while least is < 50% of max
                elif least_amount > 0:
                    max_amount = max(resources.values())
                    if resources[current_resource] > max_amount * 0.8 and least_amount < max_amount * 0.5:
                        self._clear_sticky_target()

        # Also clear if bias changed (different resource became most needed)
        if self._last_bias_resource is not None and self._last_bias_resource != self._resource_bias:
            if least_amount < 14:
                self._clear_sticky_target()
        self._last_bias_resource = self._resource_bias

        return super()._preferred_miner_extractor(state)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """V65-style aggressive budgets: 4 aligners from the start.

        The key insight from tournament data: v65's aggressive alignment wins territory
        early, which compounds over the game. Economy-first approaches lose territory
        that's hard to recapture.
        """
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            # 4-agent: 2 aligners + 2 miners (balanced)
            if step < 30:
                return 1, 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 300 and min_res >= 7 else 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: v65-aggressive — territory wins compound
        if step < 30:
            pressure_budget = 2
        else:
            pressure_budget = min(4, num_agents - 2)  # 4 aligners like v65
            if min_res < 1 and not can_hearts:
                pressure_budget = 2
            elif min_res < 3:
                pressure_budget = 3

        # Scramblers: earlier than v65 (step 100 not 1500) for disruption
        scrambler_budget = 0
        if step >= 100 and min_res >= 7:
            scrambler_budget = 1
        if step >= 2000 and min_res >= 14:
            scrambler_budget = 2
        aligner_budget = max(pressure_budget - scrambler_budget, 0)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaLateGameAgentPolicy(AlphaEconFixAgentPolicy):
    """EconFix + late-game sustainability.

    Key changes for 10k step games:
    - After step 5000, shift to more scramblers (disrupt clips)
    - Resource-gated budget: fewer aligners when economy is weak
    - More conservative with hearts in late game
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 30:
                return 1, 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if step >= 300 and min_res >= 7 else 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: phase-based strategy
        if step < 30:
            pressure_budget = 2
        elif step < 5000:
            # Early/mid: aggressive alignment
            pressure_budget = min(4, num_agents - 2)
            if min_res < 1 and not can_hearts:
                pressure_budget = 2
            elif min_res < 3:
                pressure_budget = 3
        else:
            # Late game (5000+): shift to defense/economy
            pressure_budget = min(4, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = 2  # Emergency: mass mine
            elif min_res < 7:
                pressure_budget = 3  # Reduced pressure, more mining

        # Scramblers: ramp up in late game to disrupt clips
        scrambler_budget = 0
        if step >= 5000 and min_res >= 7:
            scrambler_budget = min(2, pressure_budget // 2)  # 2 scramblers in late game
        elif step >= 100 and min_res >= 7:
            scrambler_budget = 1
        aligner_budget = max(pressure_budget - scrambler_budget, 0)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaLateGamePolicy(MettagridSemanticPolicy):
    """EconFix + late-game sustainability + team-relative roles."""
    short_names = ["alpha-late-game"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaLateGameAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaEconFixPolicy(MettagridSemanticPolicy):
    """Economy fix: resource-aware miners + v65 aggressive budgets + team-relative roles."""
    short_names = ["alpha-econ-fix"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconFixAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaEconFixGlobalPolicy(MettagridSemanticPolicy):
    """Economy fix + global role assignment (like v65)."""
    short_names = ["alpha-econ-fix-global"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # No shared_team_ids — match v65's global role assignment
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconFixAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


class AlphaV65PlusFixAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 exact behavior + resource fix + idle-mine.

    Minimal changes to v65 that are known to help:
    1. Resource-aware miner switching (fix carbon bottleneck)
    2. Idle-mine for aligners when no frontier (biggest local improvement)
    3. V65 budgets and targeting (proven in tournament)
    4. No hotspot/network weights (v65 had 0)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_bias_resource: str | None = None
        # Match v65: no hotspot/network weights
        self._hotspot_weight = 0.0
        self._network_weight = 0.0

    def _preferred_miner_extractor(self, state: MettagridState) -> KnownEntity | None:
        """Clear sticky target when resource priority changes significantly."""
        resources = _shared_resources(state)
        least = _least_resource(resources)
        least_amount = resources[least]

        if (
            self._sticky_target_kind is not None
            and self._sticky_target_kind.endswith("_extractor")
        ):
            current_resource = self._sticky_target_kind.removesuffix("_extractor")
            if current_resource != least:
                if least_amount < 7:
                    self._clear_sticky_target()
                elif least_amount > 0:
                    max_amount = max(resources.values())
                    if resources[current_resource] > max_amount * 0.8 and least_amount < max_amount * 0.5:
                        self._clear_sticky_target()

        if self._last_bias_resource is not None and self._last_bias_resource != self._resource_bias:
            if least_amount < 14:
                self._clear_sticky_target()
        self._last_bias_resource = self._resource_bias

        return super()._preferred_miner_extractor(state)

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting with idle-mine: mine when no frontier junctions available."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")
        if _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # Idle-mine instead of explore (proven +89% local improvement)
        return self._miner_action(state, summary_prefix="idle_mine_")

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """V65 original budgets: 4 aligners from step 0, scrambler at 1500."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)

        if objective == "resource_coverage":
            return 0, 0

        pressure_budget = 4
        if step >= 40 and min_res >= 20:
            pressure_budget = 5

        scrambler_budget = 0
        if step >= 1_500:
            scrambler_budget = 1
        aligner_budget = pressure_budget - scrambler_budget

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def evaluate_state(self, state: MettagridState) -> Action:
        action = super().evaluate_state(state)
        step = state.step or self._step_index
        role = self._infos.get("role", "?")
        subtask = self._infos.get("subtask", "?")
        if step % 500 == 0 or step == 1 or (step % 100 == 0 and self._agent_id == 0):
            pos = _h.absolute_position(state)
            hp = int(state.self_state.inventory.get("hp", 0))
            hearts = int(state.self_state.inventory.get("heart", 0))
            cargo = _h.resource_total(state)
            aligner_b = self._infos.get("aligner_budget", "?")
            scrambler_b = self._infos.get("scrambler_budget", "?")
            frontier = self._infos.get("frontier_neutral_junctions", "?")
            team_id = _h.team_id(state)
            friendly = len(self._world_model.entities(
                entity_type="junction", predicate=lambda e: e.owner == team_id))
            enemy = len(self._world_model.entities(
                entity_type="junction", predicate=lambda e: e.owner not in {None, "neutral", team_id}))
            shared = _shared_resources(state)
            hub = self._nearest_hub(state)
            hub_pos = (hub.global_x, hub.global_y) if hub else None
            print(
                f"[COG] step={step} agent={self._agent_id} pos={pos} hub={hub_pos} role={role} "
                f"subtask={subtask} hp={hp} hearts={hearts} cargo={cargo} "
                f"aligners={aligner_b} scramblers={scrambler_b} "
                f"friendly_j={friendly} enemy_j={enemy} frontier={frontier} "
                f"hub_res={shared}",
                flush=True,
            )
        return action


class AlphaV65PlusFixPolicy(MettagridSemanticPolicy):
    """V65 + resource fix + idle-mine. Global role assignment."""
    short_names = ["alpha-v65-plus-fix"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        # No shared_team_ids — match v65's global role assignment
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaV65PlusFixAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
            )
        return self._agent_policies[agent_id]


# ---------------------------------------------------------------------------
# AlphaAlignMax: maximize aligner count, minimize scramblers.
# Hypothesis: extra aligner > extra scrambler since alignment rate is the
# bottleneck (each alignment = 0.03/tick, each scramble = 0.01/tick).
# ---------------------------------------------------------------------------

class AlphaAlignMaxAgentPolicy(AlphaCogAgentPolicy):
    """More aligners, fewer scramblers. Aggressive re-alignment."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7:
                return 1, 0
            # 4 agents: 3 aligners, 0 scramblers, 1 miner
            aligner_budget = min(3, num_agents - 1)
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, 0

        # 5+ agents: maximize aligners
        if step < 30:
            return 2, 0
        elif step < 100:
            return 3, 0
        elif step < 500:
            # Ramp up: 4 aligners, 0 scramblers, rest mine
            pressure_budget = min(4, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            return pressure_budget, 0
        elif step < 5000:
            # Peak: 5 aligners, 1 scrambler for clips defense
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            elif min_res < 7:
                pressure_budget = min(5, num_agents - 2)
            scrambler_budget = 1 if min_res >= 7 else 0
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget
        else:
            # Late game: 4 aligners, 2 scramblers
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            scrambler_budget = min(2, pressure_budget // 3)
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget


class AlphaAlignMaxPolicy(MettagridSemanticPolicy):
    """Maximum aligners, minimal scramblers."""
    short_names = ["alpha-align-max"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAlignMaxAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


# ---------------------------------------------------------------------------
# AlphaDefenseWall: Heavy scramblers to suppress clips early, then shift to alignment.
# Counter-hypothesis: scramblers reduce clips pressure, freeing aligners.
# ---------------------------------------------------------------------------

class AlphaDefenseWallAgentPolicy(AlphaCogAgentPolicy):
    """Early scramblers to fight clips, then ramp up aligners."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if num_agents >= 4 and step >= 200 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: early scramblers
        if step < 30:
            return 2, 0
        elif step < 200:
            return 3, 0  # Economy first
        elif step < 500:
            # 3 aligners + 2 scramblers: aggressively fight clips
            pressure_budget = min(5, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            scrambler_budget = min(2, pressure_budget // 2)
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget
        else:
            # Settled: 4 aligners, 2 scramblers
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            scrambler_budget = min(2, pressure_budget // 3)
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget


class AlphaDefenseWallPolicy(MettagridSemanticPolicy):
    """Heavy early scramblers to suppress clips."""
    short_names = ["alpha-defense-wall"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaDefenseWallAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


# ---------------------------------------------------------------------------
# AlphaBlitz: All-in on alignment in early game (all agents align with free hearts),
# then transition to normal economy.
# ---------------------------------------------------------------------------

class AlphaBlitzAgentPolicy(AlphaCogAgentPolicy):
    """Early blitz: all agents try to align using the 5 free hearts, then economy."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        # Early blitz: ALL agents try to align with free hearts
        # Hub starts with 5 hearts. Use them before mining.
        if step < 50:
            # All aligners to use free hearts (hub starts with 5 hearts)
            return min(num_agents, 5), 0  # Up to 5 aligners (1 heart each)

        if num_agents <= 4:
            if step < 200:
                return min(2, num_agents - 1), 0
            if min_res < 7:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 1 if num_agents >= 4 and step >= 500 and min_res >= 14 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: standard after blitz
        if step < 100:
            return 3, 0
        elif step < 3000:
            pressure_budget = min(5, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            elif min_res < 7:
                pressure_budget = min(4, num_agents - 2)
            scrambler_budget = 1 if step >= 200 and min_res >= 7 else 0
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget
        else:
            pressure_budget = min(6, num_agents - 2)
            if min_res < 3 and not can_hearts:
                pressure_budget = max(2, num_agents // 3)
            scrambler_budget = min(2, pressure_budget // 3)
            aligner_budget = max(pressure_budget - scrambler_budget, 0)
            if objective == "economy_bootstrap":
                return min(aligner_budget, 2), 0
            return aligner_budget, scrambler_budget


class AlphaBlitzPolicy(MettagridSemanticPolicy):
    """Early blitz alignment with free hearts."""
    short_names = ["alpha-blitz"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaBlitzAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]
