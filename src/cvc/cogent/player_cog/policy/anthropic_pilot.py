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

        Also: if the bottleneck resource has no known extractors and is critically
        low, return None to force exploration (discover missing extractor types).
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

        # If bottleneck resource is critically low (< 7, can't make hearts)
        # while other resources are abundant (10x imbalance), and we have no
        # known extractors for the bottleneck, explore to discover them.
        # This prevents miners from ignoring undiscovered extractor types.
        max_amount = max(resources.values())
        if least_amount < 7 and max_amount >= least_amount * 10 + 20:
            step = state.step or self._step_index
            least_extractors = self._world_model.entities(
                entity_type=f"{least}_extractor",
                predicate=lambda entity: _h.is_usable_recent_extractor(entity, step=step),
            )
            if not least_extractors:
                self._clear_sticky_target()
                return None

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


class AlphaAggressiveAgentPolicy(AlphaCogAgentPolicy):
    """Aggressive variant: faster early game, idle aligners scramble, more pressure.

    Key changes from AlphaCog:
    1. Lower early heart batch target (1 for steps 0-200) → faster first alignments
    2. Idle aligners become scramblers instead of miners → deny opponent score
    3. More aligners + earlier scramblers → economy surplus is wasted on mining
    4. Economy-aware: only 1 miner needed once hub has 100+ of each resource
    5. Less conservative retreat: lower margins → more productive time
    """

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Tighter retreat margins — agents spend more time being productive."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 10  # Tighter than parent's 15
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 8
        margin += int(state.self_state.inventory.get("heart", 0)) * 3  # 3 per heart vs 5
        margin += min(_h.resource_total(state), 12) // 3  # Less cargo penalty
        if not _h.has_role_gear(state, role):
            margin += 8
        if (state.step or 0) >= 2_500:
            margin += 5 if role in {"aligner", "scrambler"} else 3
        if hp <= safe_steps + margin:
            return True
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 15:
                return True
        return False

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner with idle-scramble instead of idle-mine."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Early game: don't batch, go align immediately with whatever hearts we have
        if step < 200:
            pass  # Skip batching check entirely
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # No frontier junctions — expand toward known unreachable junctions
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else current_pos
        # Check both neutral AND enemy junctions as expansion targets
        # (enemy junctions near our network can be scrambled then re-aligned)
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20  # Less conservative
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle aligners: scramble if economy healthy, mine if economy tight, explore if both fail
        min_res = _h.team_min_resource(state)
        if int(state.self_state.inventory.get("heart", 0)) > 0 and min_res >= 14:
            # Economy healthy: scramble to deny opponent score
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 14:
            # Economy needs help: mine to rebuild
            return self._miner_action(state, summary_prefix="idle_align_")

        # Explore to discover new junction clusters
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """More aggressive: more aligners, earlier scramblers, fewer miners."""
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
            if step < 100:
                return 1, 0  # Economy-first: 1 aligner, rest mine
            if min_res < 7 and not can_hearts:
                return 1, 0
            # 4 agents: max alignment pressure. Scrambler only with massive surplus.
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                # Economy healthy: 3 aligners + 1 miner
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 200 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents: match AlphaCog budgets + economy surplus boost
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            # Surplus: shift to max pressure, only 1-2 miners needed
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        # Scramblers: start at step 200 like AlphaCog
        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaAggressivePolicy(MettagridSemanticPolicy):
    """Aggressive scoring: fast early game, idle-scramble, economy-aware budgets."""
    short_names = ["alpha-aggressive"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAggressiveAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


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


class AlphaNoScrambleCogAgentPolicy(AlphaCogAgentPolicy):
    """AlphaCog but zero scramblers — all pressure budget goes to alignment.

    Hypothesis: in tournament, hearts spent on scrambling could be better
    used for alignment. More aligners = more territory = higher score.
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
            if objective == "economy_bootstrap":
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7:
                return 1, 0
            aligner_budget = min(num_agents - 1, 3)  # Max aligners, keep 1 miner
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, 0  # No scramblers ever

        # 5+ agents
        if step < 30:
            return 2, 0
        elif step < 100:
            return 3, 0
        else:
            aligner_budget = min(num_agents - 2, 6)
            if min_res < 3 and not can_hearts:
                aligner_budget = max(2, num_agents // 3)
            elif min_res < 7:
                aligner_budget = min(4, num_agents - 2)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, 0  # No scramblers ever


class AlphaNoScramblePolicy(MettagridSemanticPolicy):
    """AlphaCog with zero scramblers."""
    short_names = ["alpha-noscramble"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaNoScrambleCogAgentPolicy(
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


# ---------------------------------------------------------------------------
# AlphaOptimal: V65 hub-centric targeting + team-aware budgets + idle-mine +
# resource bias + re-alignment bonus. Best of all worlds.
# ---------------------------------------------------------------------------

class AlphaOptimalAgentPolicy(AlphaV65TrueReplicaAgentPolicy):
    """V65 targeting (hub_penalty) + AlphaCog improvements (idle-mine, resource bias, team budgets)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_budget_change_step = 0
        num_agents = self.policy_env_info.num_agents
        self._current_aligner_budget = min(4, max(num_agents - 1, 1))

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V65 targeting with idle-mine (proven 89% better than idle-explore)."""
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

        # Idle-mine: proven better than idle-explore (8.05 vs 3.54 in A/B tests)
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Team-size-aware budgets (critical for 2v6/6v2 tournament matches)."""
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
            scrambler_budget = 1 if step >= 500 and num_agents >= 4 and min_res >= 14 else 0
            if min_res < 1 and not can_hearts:
                return 1, 0
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents: v65-like budgets with team awareness
        if step < 30:
            return 2, 0
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

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        resources = _shared_resources(state)
        least = _least_resource(resources)
        return MacroDirective(resource_bias=least)

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


class AlphaOptimalPolicy(MettagridSemanticPolicy):
    """V65 targeting + idle-mine + team-aware budgets + resource bias."""
    short_names = ["alpha-optimal"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaOptimalAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


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


class AlphaSustainAgentPolicy(AlphaCogAgentPolicy):
    """Sustain variant: maximize score per heart by conserving silicon.

    Key changes from AlphaCog:
    1. Silicon-first mining: always bias toward silicon (scarcest extractor, 45 vs 50-58).
    2. No scrambling at all: save every heart for alignment.
    3. Late-game conservation: when silicon < 14, reduce aligners to prevent heart waste.
    4. No early heart skip: go align immediately in first 200 steps.
    5. Smarter expansion: prefer junction clusters (more junctions unlocked per heart).
    """

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Always bias toward silicon — the bottleneck resource."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        others_min = min(resources[r] for r in _ELEMENTS if r != "silicon")
        if silicon > others_min * 2 and others_min < 7:
            least = _least_resource(resources)
            return MacroDirective(resource_bias=least)
        return MacroDirective(resource_bias="silicon")

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner that never scrambles — all hearts go to alignment."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Early game: go align immediately (no batching for first 200 steps)
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions — prefer clusters
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else current_pos
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable

            def cluster_score(j):
                nearby = sum(
                    1 for other in unreachable
                    if other is not j and _h.manhattan(j.position, other.position) <= 15
                )
                dist = _h.manhattan(current_pos, j.position)
                return dist - nearby * 5
            best = min(targets, key=cluster_score)
            dist = _h.manhattan(current_pos, best.position)
            if dist < hp - 20:
                return self._move_to_known(state, best, summary="expand_cluster_junction", vibe="change_vibe_aligner")

        # No expansion target — help economy by mining
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """No scramblers ever. Late-game conservation when silicon depletes."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)

        if objective == "resource_coverage":
            return 0, 0

        # Late-game conservation: when silicon critically low, reduce pressure
        if silicon < 14 and step > 2000:
            if num_agents <= 2:
                return 0, 0
            if num_agents <= 4:
                return 1, 0
            return 2, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, 0  # Never scramble

        # 5+ agents
        if step < 30:
            return 2, 0
        if step < 100:
            return 3, 0

        if min_res < 3 and not can_hearts:
            pressure = max(2, num_agents // 3)
        elif min_res < 7:
            pressure = min(4, num_agents - 2)
        else:
            pressure = min(5, num_agents - 2)

        if objective == "economy_bootstrap":
            return min(2, pressure), 0
        return pressure, 0  # Never scramble


class AlphaAdaptiveV2AgentPolicy(AlphaCogAgentPolicy):
    """Adaptive v2: aggressive early, sustain late. Best of both worlds.

    Phase 1 (step 0-2500): AlphaAggressive behavior — fast alignment, idle scramble
    Phase 2 (step 2500+ or silicon < 30): Conservation — no scramble, silicon mining, fewer aligners
    """

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-first bias when silicon is the bottleneck."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        step = state.step or self._step_index
        # After step 1500 or when silicon is low, bias toward silicon
        if step > 1500 or silicon < 30:
            others_min = min(resources[r] for r in _ELEMENTS if r != "silicon")
            if silicon > others_min * 2 and others_min < 7:
                return MacroDirective(resource_bias=_least_resource(resources))
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=_least_resource(resources))

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: scramble in early game, pure alignment in late game."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Early game: go align immediately
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junction clusters
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable

            def cluster_score(j):
                nearby = sum(
                    1 for other in unreachable
                    if other is not j and _h.manhattan(j.position, other.position) <= 15
                )
                dist = _h.manhattan(current_pos, j.position)
                return dist - nearby * 5
            best = min(targets, key=cluster_score)
            dist = _h.manhattan(current_pos, best.position)
            if dist < hp - 20:
                return self._move_to_known(state, best, summary="expand_cluster_junction", vibe="change_vibe_aligner")

        # Early game: idle-scramble when economy healthy
        in_conservation = step > 2500 or silicon < 30
        min_res = _h.team_min_resource(state)
        if not in_conservation and hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 14:
            return self._miner_action(state, summary_prefix="idle_align_")

        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive early, conservative late. No dedicated scramblers."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)

        if objective == "resource_coverage":
            return 0, 0

        in_conservation = step > 2500 or silicon < 30

        # Conservation mode: fewer aligners, no scramblers
        if in_conservation and silicon < 14:
            if num_agents <= 2:
                return 0, 0
            if num_agents <= 4:
                return 1, 0
            return 2, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            # Early game: allow 1 scrambler with surplus
            scrambler_budget = 0
            if not in_conservation and min_res >= 200 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            if objective == "economy_bootstrap":
                return 1, 0
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 30:
            return 2, 0
        if step < 100:
            return 3, 0

        economy_surplus = min_res >= 100

        if economy_surplus and not in_conservation:
            pressure = min(num_agents - 1, 7)
        elif min_res < 3 and not can_hearts:
            pressure = max(2, num_agents // 3)
        elif min_res < 7:
            pressure = min(4, num_agents - 2)
        else:
            pressure = min(5, num_agents - 2)

        # Scramblers only in early/aggressive phase
        scrambler_budget = 0
        if not in_conservation:
            if step >= 200 and min_res >= 7:
                scrambler_budget = min(1, pressure // 3)

        aligner_budget = max(pressure - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaAdaptiveV2Policy(MettagridSemanticPolicy):
    """Adaptive v2: aggressive early, sustain late. Silicon-first bias."""
    short_names = ["alpha-adaptive-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveV2AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaSustainPolicy(MettagridSemanticPolicy):
    """Sustain scoring: silicon-first mining, no scrambling, late-game conservation."""
    short_names = ["alpha-sustain"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSustainAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


# Wider explore offsets for full map coverage (88x88 map)
_WIDE_ALIGNER_EXPLORE_OFFSETS = (
    (0, -35),
    (25, -25),
    (35, 0),
    (25, 25),
    (0, 35),
    (-25, 25),
    (-35, 0),
    (-25, -25),
    (0, -15),
    (15, 0),
    (0, 15),
    (-15, 0),
)


class AlphaExplorerAgentPolicy(AlphaAggressiveAgentPolicy):
    """Explorer variant: better junction discovery through wider exploration.

    Key changes from AlphaAggressive:
    1. Wider explore offsets (35 vs 22) to cover full 88x88 map.
    2. No hub distance limit on expansion (was 40, now unlimited).
    3. Idle aligners explore before mining — discover junctions is priority.
    4. Bridge expansion: prefer junctions that extend network toward unexplored areas.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner with aggressive exploration and no hub-distance limits."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Early game: go align immediately (no batching for first 200 steps)
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions — NO hub distance limit
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            # Prefer junctions that bridge to more unreachable junctions
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 15  # Less conservative
            ]
            targets = safe_unreachable if safe_unreachable else unreachable

            def bridge_score(j):
                # How many other unreachable junctions would become reachable
                # if we aligned this one (within alignment distance 15)?
                bridged = sum(
                    1 for other in unreachable
                    if other is not j and _h.manhattan(j.position, other.position) <= 15
                )
                dist = _h.manhattan(current_pos, j.position)
                return dist - bridged * 8  # Strong bonus for bridging
            best = min(targets, key=bridge_score)
            dist = _h.manhattan(current_pos, best.position)
            if dist < hp - 15:
                return self._move_to_known(state, best, summary="expand_bridge_junction", vibe="change_vibe_aligner")

        # Idle aligners: scramble if economy healthy
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Explore with wider offsets to discover distant junctions
        return self._wide_explore_action(state, role="aligner", summary="wide_explore_junctions")

    def _wide_explore_action(self, state: MettagridState, *, role: str, summary: str) -> tuple[Action, str]:
        """Explore with wider offsets to cover the full map."""
        current_pos = _h.absolute_position(state)
        hub = self._nearest_hub(state)
        center = (hub.global_x, hub.global_y) if hub is not None else current_pos
        offsets = _WIDE_ALIGNER_EXPLORE_OFFSETS
        offset_index = (self._explore_index + self._agent_id) % len(offsets)
        target = offsets[offset_index]
        absolute_target = (center[0] + target[0], center[1] + target[1])
        if _h.manhattan(current_pos, absolute_target) <= 2:
            self._explore_index += 1
            offset_index = (self._explore_index + self._agent_id) % len(offsets)
            target = offsets[offset_index]
            absolute_target = (center[0] + target[0], center[1] + target[1])
        return self._move_to_position(state, absolute_target, summary=summary, vibe=_h.role_vibe(role))


class AlphaExplorerPolicy(MettagridSemanticPolicy):
    """Explorer: wider exploration, no hub-distance limits, bridge expansion."""
    short_names = ["alpha-explorer"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaExplorerAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaBalancedAgentPolicy(AlphaAggressiveAgentPolicy):
    """Economy-balanced variant: sustains aligners through the whole game.

    Key insight: AlphaAggressive collapses after step 2000 because 6 aligners
    consume hearts faster than 1-2 miners can produce silicon. This policy:
    1. Keeps 3-4 miners always (never fewer than 3 for 8-agent games)
    2. Limits aligners to 3 early, 4 mid-game, based on silicon reserves
    3. No scrambling until economy stable (min_res >= 50)
    4. Silicon-priority mining when silicon is scarce
    5. Earlier economy pullback (min_res < 30 triggers miner shift)
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner that only idle-scrambles when economy is very healthy."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Early game: don't batch, go align immediately
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else current_pos
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: ONLY scramble if economy very healthy, otherwise mine to sustain economy
        min_res = _h.team_min_resource(state)
        if int(state.self_state.inventory.get("heart", 0)) > 0 and min_res >= 50:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Always mine when idle — economy sustain is critical
        return self._miner_action(state, summary_prefix="idle_align_")

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-priority mining when silicon is scarce."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        least = _least_resource(resources)
        # If silicon is within 20 of the lowest resource, prioritize silicon
        least_amount = resources[least]
        if silicon <= least_amount + 20:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=least)

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Conservative budgets: sustain economy through the whole game."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # 4 agents: max 2 aligners, keep 2 miners always
            aligner_budget = 2
            scrambler_budget = 0
            if min_res < 30:
                aligner_budget = 1  # Economy struggling: pull back to 1 aligner
            return aligner_budget, scrambler_budget

        # 5+ agents: always keep at least 3-4 miners for sustainable economy
        min_miners = max(3, num_agents // 2 - 1)  # 3 miners for 8 agents
        max_pressure = num_agents - min_miners

        if step < 30:
            return 2, 0

        # Economy-gated aligner count
        if min_res < 10 and not can_hearts:
            # Crisis: almost all mine
            return 1, 0
        elif min_res < 30:
            # Struggling: limit to 2 aligners
            return min(2, max_pressure), 0
        elif min_res < 50:
            # Moderate: 3 aligners
            return min(3, max_pressure), 0
        else:
            # Healthy: full pressure but capped
            aligner_budget = min(4, max_pressure)
            # Only scramble when very healthy
            scrambler_budget = 0
            if step >= 500 and min_res >= 80:
                scrambler_budget = 1
                aligner_budget = min(3, max_pressure - 1)
            return aligner_budget, scrambler_budget


class AlphaBalancedPolicy(MettagridSemanticPolicy):
    """Economy-balanced: sustains aligners through whole game, silicon-priority mining."""
    short_names = ["alpha-balanced"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaBalancedAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptiveV3AgentPolicy(AlphaBalancedAgentPolicy):
    """Adaptive economy v3: ramps aligners when resources permit.

    Fixes AlphaBalanced's over-hoarding (1000+ resources with only 3 aligners).
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Dynamic budgets: scale aligners proportional to resource health."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res < 30:
                return 1, 0
            aligner_budget = 2
            if min_res >= 100 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            return aligner_budget, 0

        # 5+ agents: dynamic scaling, always keep >= 2 miners
        if step < 30:
            return 2, 0

        if min_res < 10 and not can_hearts:
            return 1, 0
        elif min_res < 30:
            return 2, 0
        elif min_res < 80:
            return 3, 0
        elif min_res < 200:
            scrambler = 1 if step >= 500 else 0
            return 4, scrambler
        else:
            # Rich: max pressure, keep 2 miners
            scrambler = 1 if step >= 500 else 0
            aligner = min(5, num_agents - 2 - scrambler)
            return aligner, scrambler


class AlphaAdaptiveV3Policy(MettagridSemanticPolicy):
    """Adaptive economy v3: dynamic aligner scaling based on resource health."""
    short_names = ["alpha-adaptive-v3"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveV3AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaChainExpandAgentPolicy(AlphaAdaptiveV3AgentPolicy):
    """AdaptiveV3 + aggressive chain expansion + better frontier exploration.

    Improvements:
    1. Higher expansion_weight (20 vs 10) to strongly prefer chain-building junctions
    2. Higher expansion_cap (120 vs 60) to distinguish junctions that unlock many others
    3. When idle: alternate between exploring new areas and mining (50/50)
       instead of only idle-scrambling, to discover more junctions
    4. Wider explore offsets for idle aligners to find distant junction clusters
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 20.0  # 2x: strongly prefer chain-building junctions
        self._expansion_cap = 120.0    # 2x: distinguish 6-unlock from 12-unlock junctions

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner with exploration-heavy idle behavior to discover more junctions."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions (walk there to extend network)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        hub = self._nearest_hub(state)
        hub_pos = hub.position if hub is not None else current_pos
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: alternate between exploring (odd agent_id) and other actions (even)
        # This ensures some agents always explore to discover new junction clusters
        min_res = _h.team_min_resource(state)
        if self._agent_id % 2 == 0:
            # Even agents: explore to discover new junctions
            return self._explore_action(state, role="aligner", summary="find_neutral_junction")
        else:
            # Odd agents: scramble if economy healthy, mine if not
            if hearts > 0 and min_res >= 50:
                scramble_target = self._preferred_scramble_target(state)
                if scramble_target is not None:
                    return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")
            return self._miner_action(state, summary_prefix="idle_align_")


class AlphaChainExpandPolicy(MettagridSemanticPolicy):
    """Chain expansion: high expansion weight + exploration-heavy idle behavior."""
    short_names = ["alpha-chain-expand"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaChainExpandAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaChainDefenseAgentPolicy(AlphaChainExpandAgentPolicy):
    """ChainExpand + late-game defense: more scramblers when losing.

    When enemy junctions exceed ours, shift to scrambling to deny their score.
    Score = avg aligned junctions per tick (both teams same), so denying
    enemy junctions is as valuable as gaining our own.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Add late-game scramble defense when enemy is winning."""
        aligner_budget, scrambler_budget = super()._pressure_budgets(state, objective=objective)
        if objective in {"resource_coverage", "economy_bootstrap"}:
            return aligner_budget, scrambler_budget

        step = state.step or self._step_index
        if step < 1000:
            return aligner_budget, scrambler_budget

        num_agents = self.policy_env_info.num_agents
        # Small teams: no defense shift (scramblers too expensive)
        if num_agents <= 4:
            return aligner_budget, scrambler_budget

        # Count friendly vs enemy junctions
        team_id = _h.team_id(state)
        friendly = len(self._world_model.entities(
            entity_type="junction", predicate=lambda e: e.owner == team_id))
        enemy = len(self._world_model.entities(
            entity_type="junction", predicate=lambda e: e.owner not in {None, "neutral", team_id}))

        min_res = _h.team_min_resource(state)

        # When losing: shift aligners to scramblers
        if enemy > friendly + 3 and min_res >= 14:
            extra_scramblers = min(2, max(0, aligner_budget - 1))
            scrambler_budget += extra_scramblers
            aligner_budget -= extra_scramblers
        elif enemy > friendly and min_res >= 14:
            if aligner_budget > 1:
                scrambler_budget += 1
                aligner_budget -= 1

        return aligner_budget, scrambler_budget


class AlphaChainDefensePolicy(MettagridSemanticPolicy):
    """Chain expansion + late-game defense scrambling."""
    short_names = ["alpha-chain-defense"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaChainDefenseAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaMaxChainAgentPolicy(AlphaChainDefenseAgentPolicy):
    """Maximum chain expansion: higher weights + all-explore idle.

    Push expansion_weight to 30 and cap to 180 for maximum chain-building.
    ALL idle aligners explore to maximize junction discovery.
    Defense scrambling still active via budget shifts when losing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 30.0
        self._expansion_cap = 180.0

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """ALL idle aligners explore — maximum junction discovery."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe = [j for j in unreachable if _h.manhattan(current_pos, j.position) < hp - 20]
            targets = safe if safe else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            if _h.manhattan(current_pos, nearest.position) < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # ALL idle aligners explore — maximum junction discovery
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaMaxChainPolicy(MettagridSemanticPolicy):
    """Maximum chain expansion + defense scrambling."""
    short_names = ["alpha-max-chain"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxChainAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAggroChainAgentPolicy(AlphaAggressiveAgentPolicy):
    """Aggressive + silicon-priority mining.

    Takes the tournament-proven Aggressive base and adds silicon-priority mining
    to delay the economy collapse that typically starts around step 2000.
    """

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-priority mining when silicon is scarce."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        least = _least_resource(resources)
        least_amount = resources[least]
        if silicon <= least_amount + 20:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=least)


class AlphaAggroChainPolicy(MettagridSemanticPolicy):
    """Aggressive base + chain expansion weights + silicon mining."""
    short_names = ["alpha-aggro-chain"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAggroChainAgentPolicy(
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
# AlphaPureAlign — zero scrambling, chain expansion, fast start, pure alignment
# ---------------------------------------------------------------------------

class AlphaPureAlignAgentPolicy(AlphaChainExpandAgentPolicy):
    """Pure alignment: zero scrambling, chain expansion, aggressive early game.

    Combines:
    - ChainExpand's expansion_weight=20 and expansion_cap=120
    - Aggressive's fast early game (no heart batching before step 200)
    - Aggressive's tighter retreat margins
    - Zero scrambling (all hearts for alignment)
    - Idle aligners: always explore to find more junctions
    - Silicon-priority mining to delay resource bottleneck
    """

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Tighter retreat margins (from Aggressive) — more productive time."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 10
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 8
        margin += int(state.self_state.inventory.get("heart", 0)) * 3
        margin += min(_h.resource_total(state), 12) // 3
        if not _h.has_role_gear(state, role):
            margin += 8
        if (state.step or 0) >= 2_500:
            margin += 5 if role == "aligner" else 3
        if hp <= safe_steps + margin:
            return True
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 15:
                return True
        return False

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Pure aligner: align, expand, explore. Never scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Fast early game: no batching before step 200 (from Aggressive)
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 15  # Even less conservative
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 15:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: always explore to find more junctions (never scramble)
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Zero scrambling. All pressure goes to alignment."""
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
            # 4-agent: aggressive alignment ramp
            if step < 50:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # With even modest economy, go 2 aligners immediately
            if min_res < 20:
                return min(2, num_agents - 1), 0
            # Strong economy: 3 aligners, 1 miner
            return min(3, num_agents - 1), 0

        # 5+ agents: aggressive alignment, zero scramblers
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            # Max pressure: only 1 miner needed
            return min(num_agents - 1, 7), 0
        elif step < 100:
            return 3, 0
        elif economy_crisis:
            return max(2, num_agents // 3), 0
        elif min_res < 7:
            return min(4, num_agents - 2), 0
        elif min_res < 30:
            return min(5, num_agents - 2), 0
        else:
            return min(6, num_agents - 1), 0

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-priority mining to delay depletion bottleneck."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        least = _least_resource(resources)
        least_amount = resources[least]
        # Prioritize silicon when it's within 20 of bottleneck
        if silicon <= least_amount + 20:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=least)


class AlphaPureAlignPolicy(MettagridSemanticPolicy):
    """Pure alignment: zero scrambling, chain expansion, fast start."""
    short_names = ["alpha-pure-align"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaPureAlignAgentPolicy(
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
# AlphaFortress — sustained scoring via defense + economy management
# ---------------------------------------------------------------------------

class AlphaFortressAgentPolicy(AlphaChainExpandAgentPolicy):
    """Fortress: sustained scoring via early defense, economy conservation, chain expansion.

    Key insight: 10000-step games mean sustained scoring beats peak scoring.
    Maintaining 10 junctions for 10000 steps beats 13 for 3000 then 5 for 7000.

    Strategy:
    1. Heavy early scrambling to prevent Clips from building a lead
    2. More miners mid-game to build resource reserves for late game
    3. Chain expansion for efficient network building
    4. Silicon-priority mining to delay depletion
    5. Economy-responsive: ramp down pressure when resources low
    """

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Tighter retreat for scramblers (they need to be aggressive), conservative for miners."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role)
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 12 if role == "scrambler" else 15
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 8
        margin += int(state.self_state.inventory.get("heart", 0)) * 4
        margin += min(_h.resource_total(state), 12) // 3
        if not _h.has_role_gear(state, role):
            margin += 8
        if (state.step or 0) >= 2_500:
            margin += 5 if role in {"aligner", "scrambler"} else 3
        if hp <= safe_steps + margin:
            return True
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 15:
                return True
        return False

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner with idle-scramble when economy is healthy."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # No batching before step 200
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble if we have hearts and economy is healthy
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Economy needs help or nothing to scramble: explore
        if min_res < 14:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Sustained pressure: more scramblers early, more miners for economy."""
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
            # 4-agent: balanced alignment + defense
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # 2 aligners + 1 scrambler when economy supports it
            if min_res >= 50 and step >= 300:
                return 2, 1
            if min_res >= 20:
                return 2, 0
            return 1, 0

        # 5+ agents: strong defense early, sustained economy
        if step < 30:
            return 2, 0

        economy_crisis = min_res < 3 and not can_hearts

        if economy_crisis:
            # Economy collapsed: minimal pressure, rebuild
            return max(1, num_agents // 4), 0

        if step < 200:
            # Early: ramp up with 1 scrambler from step 100
            if step >= 100 and min_res >= 7:
                return 3, 1
            return 2, 0

        # Mid-to-late game: sustained pressure with heavy defense
        if min_res >= 100:
            # Rich: max pressure, 2 scramblers
            return min(num_agents - 3, 5), 2
        elif min_res >= 30:
            # Healthy: balanced
            return min(num_agents - 3, 4), 1
        elif min_res >= 7:
            # Tight: fewer aligners, keep scrambler
            return min(num_agents - 3, 3), 1
        else:
            # Very tight: minimal pressure
            return 2, 0

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-priority mining."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        least = _least_resource(resources)
        least_amount = resources[least]
        if silicon <= least_amount + 20:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=least)


class AlphaFortressPolicy(MettagridSemanticPolicy):
    """Fortress: sustained scoring via defense + economy management."""
    short_names = ["alpha-fortress"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaFortressAgentPolicy(
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
# AlphaEconSurge — max miners early, then surge aligners when economy peaks
# ---------------------------------------------------------------------------

class AlphaEconSurgeAgentPolicy(AlphaFortressAgentPolicy):
    """Econ Surge: heavy mining first 1000 steps, then surge to max alignment.

    Insight: the Aggressive policy runs out of resources mid-game.
    By mining heavily early, we build reserves that sustain alignment for the
    full 10000 steps. Clips take junctions early but we catch up and sustain.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy-first: mine heavily early, surge alignment mid-game."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 300 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 200:
                return 1, 0  # Economy-first
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res >= 100:
                return min(3, num_agents - 1), 0
            if min_res >= 30:
                return 2, 0
            return 1, 0

        # 5+ agents: heavy mining first 500 steps
        economy_crisis = min_res < 3 and not can_hearts

        if economy_crisis:
            return max(1, num_agents // 4), 0

        if step < 100:
            return 1, 0  # Almost all mine
        if step < 500:
            # Building reserves: 2 aligners, 1 scrambler, rest mine
            if min_res >= 7:
                return 2, 1
            return 1, 0

        # Post-500: surge based on accumulated resources
        if min_res >= 200:
            # Massive reserves: go all-out
            return min(num_agents - 2, 6), 2
        elif min_res >= 100:
            return min(num_agents - 2, 5), 2
        elif min_res >= 50:
            return min(num_agents - 3, 4), 1
        elif min_res >= 20:
            return 3, 1
        elif min_res >= 7:
            return 2, 1
        else:
            return 1, 0


class AlphaEconSurgePolicy(MettagridSemanticPolicy):
    """Econ Surge: mine heavily early, then surge alignment with reserves."""
    short_names = ["alpha-econ-surge"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconSurgeAgentPolicy(
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
# AlphaUltra — optimized for tournament (weak opponents): max align, zero scramble,
# chain expansion, aggressive economy scaling, exploration-heavy idle
# ---------------------------------------------------------------------------

class AlphaUltraAgentPolicy(AlphaAggressiveAgentPolicy):
    """Ultra: tournament-optimized for weak opponents.

    Combines best elements:
    - Aggressive: fast start, tight retreat margins, no early batching
    - ChainExpand: expansion_weight=20 for efficient network building
    - Zero scramblers: opponents are weak, hearts better spent on alignment
    - All idle aligners explore: discover more junction clusters
    - Economy-responsive: scale aligners with resources, never starve
    - Re-alignment hotspot bonus from AlphaCog
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 20.0
        self._expansion_cap = 120.0

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > explore. Never scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # No batching first 200 steps — go align immediately
        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions — braver than parent (hp - 15)
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 15
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 15:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: always explore to discover more junctions (never scramble)
        min_res = _h.team_min_resource(state)
        if min_res < 10:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Tournament-optimized: zero scramblers, max aligners, economy-responsive."""
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
            if step < 50:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # 4 agents: scale aggressively, no scramblers
            if min_res >= 100:
                return min(3, num_agents - 1), 0
            if min_res >= 30:
                return 2, 0
            return 1, 0

        # 5+ agents: max alignment, zero scramblers
        if step < 20:
            return 2, 0

        economy_crisis = min_res < 3 and not can_hearts

        if economy_crisis:
            return max(1, num_agents // 4), 0

        # Aggressive scaling based on economy
        if min_res >= 200:
            return min(num_agents - 1, 7), 0  # Nearly all align
        elif min_res >= 100:
            return min(num_agents - 1, 6), 0
        elif min_res >= 50:
            return min(num_agents - 2, 5), 0
        elif min_res >= 20:
            return min(num_agents - 2, 4), 0
        elif min_res >= 7:
            return 3, 0
        else:
            return 2, 0

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-priority mining."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        least = _least_resource(resources)
        least_amount = resources[least]
        if silicon <= least_amount + 20:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=least)


class AlphaUltraPolicy(MettagridSemanticPolicy):
    """Ultra: tournament-optimized for weak opponents. Max align, zero scramble, chain expand."""
    short_names = ["alpha-ultra"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaUltraAgentPolicy(
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
# AlphaUltraV2 — Ultra chain expansion + light defense (1 scrambler)
# Insight: Ultra peaks at 20j but collapses to 0. Adding 1 scrambler
# should slow Clips' scrambling enough to sustain high junction counts.
# ---------------------------------------------------------------------------

class AlphaUltraV2AgentPolicy(AlphaUltraAgentPolicy):
    """Ultra V2: chain expansion + light defense.

    Ultra peaks at 20 junctions but collapses because Clips scrambles
    everything. V2 adds 1 scrambler to slow Clips' advance while keeping
    near-max alignment pressure and chain expansion.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > idle-scramble-if-rich > explore."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 15
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 15:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble if economy healthy (hearts + resources), else explore
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 20:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")
        if min_res < 10:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Chain expansion + light defense: 1 scrambler after step 200."""
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
            if step < 50:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # 4 agents: scale with economy, add scrambler when rich
            if min_res >= 100:
                return 2, 1  # 2 align + 1 scramble + 1 mine
            if min_res >= 30:
                return 2, 0
            return 1, 0

        # 5+ agents: max alignment + 1 scrambler
        if step < 20:
            return 2, 0

        economy_crisis = min_res < 3 and not can_hearts
        if economy_crisis:
            return max(1, num_agents // 4), 0

        # 1 scrambler once economy supports it (step 200+)
        scrambler = 1 if step >= 200 and min_res >= 7 else 0

        if min_res >= 200:
            return min(num_agents - 1 - scrambler, 6), scrambler
        elif min_res >= 100:
            return min(num_agents - 2 - scrambler, 5), scrambler
        elif min_res >= 50:
            return min(num_agents - 2 - scrambler, 4), scrambler
        elif min_res >= 20:
            return 3, scrambler
        elif min_res >= 7:
            return 2, scrambler
        else:
            return 2, 0


class AlphaUltraV2Policy(MettagridSemanticPolicy):
    """Ultra V2: chain expansion + light defense (1 scrambler)."""
    short_names = ["alpha-ultra-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaUltraV2AgentPolicy(
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
# AlphaUltraV3 — Ultra chain expansion + aggressive idle-scramble by ALL aligners
# Insight: Aggressive sustains 8-9j through idle-scramble. Ultra peaks at 20j
# but collapses. V3: chain expansion + idle-scramble to sustain high junctions.
# ---------------------------------------------------------------------------

class AlphaUltraV3AgentPolicy(AlphaUltraAgentPolicy):
    """Ultra V3: chain expansion + Aggressive-style idle-scramble.

    Keeps Ultra's chain expansion and fast start but uses Aggressive's
    idle behavior: when no junctions to align, scramble enemy junctions
    to slow Clips. This should sustain the 20j peak much longer.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner with Aggressive-style idle-scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 15
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 15:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble if economy healthy (like Aggressive), mine if tight, explore if neither
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")
        if min_res < 14:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Max aligners + early scrambler like Aggressive, but with chain expansion."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res >= 50 and step >= 500:
                return min(3, num_agents - 1), 0
            return 2, 0

        # 5+ agents: match Aggressive budgets (which get 6.54 in tournament)
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        return aligner_budget, scrambler_budget


class AlphaUltraV3Policy(MettagridSemanticPolicy):
    """Ultra V3: chain expansion + Aggressive budgets + idle-scramble."""
    short_names = ["alpha-ultra-v3"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaUltraV3AgentPolicy(
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
# AlphaUltraV4 — V3 with expansion_weight=25 (5% higher than V3's 20)
# ---------------------------------------------------------------------------

class AlphaUltraV4AgentPolicy(AlphaUltraV3AgentPolicy):
    """V4: expansion_weight=25 to push chain expansion harder."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_weight = 25.0
        self._expansion_cap = 150.0


class AlphaUltraV4Policy(MettagridSemanticPolicy):
    """Ultra V4: expansion_weight=25."""
    short_names = ["alpha-ultra-v4"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaUltraV4AgentPolicy(
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
# AlphaUltraV5 — V3 + economy surge: heavier mining first 500 steps,
# then surge to max aligners when reserves are high
# ---------------------------------------------------------------------------

class AlphaUltraV5AgentPolicy(AlphaUltraV3AgentPolicy):
    """V5: V3 base + economy surge. Mine hard early, then max align when reserves peak."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy surge: mine first 300 steps, then scale aggressively."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 300 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 150:
                return 1, 0  # Economy-first
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res >= 100:
                return min(3, num_agents - 1), 0
            if min_res >= 30:
                return 2, 0
            return 1, 0

        # 5+ agents: economy surge
        if step < 30:
            return 1, 0  # All mine at start

        economy_crisis = min_res < 3 and not can_hearts
        if economy_crisis:
            return max(1, num_agents // 4), 0

        if step < 200:
            # Light pressure, heavy mining
            return 2, 0

        # Post-200: scale based on reserves (like Aggressive but with chain expansion)
        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, num_agents // 4)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = 1

        if min_res >= 200:
            return min(num_agents - 1 - scrambler_budget, 6), scrambler_budget
        elif min_res >= 100:
            return min(num_agents - 1 - scrambler_budget, 5), scrambler_budget
        elif min_res >= 50:
            return min(num_agents - 2 - scrambler_budget, 4), scrambler_budget
        elif min_res >= 20:
            return 3, scrambler_budget
        elif min_res >= 7:
            return 2, scrambler_budget
        else:
            return 2, 0


class AlphaUltraV5Policy(MettagridSemanticPolicy):
    """Ultra V5: chain expansion + economy surge + Aggressive idle-scramble."""
    short_names = ["alpha-ultra-v5"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaUltraV5AgentPolicy(
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
# AlphaCoopPolicy — Aggressive but cooperative-friendly: zero scrambling,
# idle aligners mine to sustain economy. For cooperative tournament scoring.
# ---------------------------------------------------------------------------

class AlphaCoopAgentPolicy(AlphaAggressiveAgentPolicy):
    """Cooperative variant: Aggressive play but NEVER scramble.

    Since tournament scoring is cooperative (both teams get same score),
    scrambling opponent junctions HURTS our score. Instead:
    1. Zero scramblers in budgets
    2. Idle aligners mine (sustain economy longer)
    3. Everything else same as Aggressive
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > mine. Never scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: NEVER scramble (cooperative scoring). Mine to sustain economy.
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive budgets but zero scramblers for cooperative scoring."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res >= 50 and step >= 500:
                return min(3, num_agents - 1), 0
            return min(2, num_agents - 1), 0

        # 5+ agents: same as Aggressive but zero scramblers
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            return min(num_agents - 1, 7), 0
        elif step < 100:
            return 3, 0
        elif economy_crisis:
            return max(2, num_agents // 3), 0
        elif min_res < 7:
            return min(4, num_agents - 2), 0
        else:
            return min(5, num_agents - 2), 0


class AlphaCoopPolicy(MettagridSemanticPolicy):
    """Cooperative: Aggressive play, zero scrambling, idle-mine for economy."""
    short_names = ["alpha-coop"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCoopAgentPolicy(
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
# AlphaEconMaxPolicy — More miners, fewer aligners, sustain economy longest.
# Hypothesis: if we sustain alignment for more ticks, total score increases.
# ---------------------------------------------------------------------------

class AlphaEconMaxAgentPolicy(AlphaCoopAgentPolicy):
    """Economy-maximizing: keep more miners to sustain alignment through full 10k steps."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Conservative budgets: keep 50%+ agents as miners to sustain economy."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # Max 2 aligners to keep at least 2 miners
            return min(2, num_agents - 2), 0

        # 5+ agents: keep at least half as miners
        min_miners = max(num_agents // 2, 3)
        max_aligners = num_agents - min_miners

        if step < 30:
            return min(2, max_aligners), 0

        if min_res < 3 and not can_hearts:
            return 1, 0
        elif min_res < 20:
            return min(2, max_aligners), 0
        elif min_res < 50:
            return min(3, max_aligners), 0
        else:
            return min(max_aligners, 4), 0


class AlphaEconMaxPolicy(MettagridSemanticPolicy):
    """EconMax: conservative alignment, maximum economy sustainability."""
    short_names = ["alpha-econ-max"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconMaxAgentPolicy(
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
# AlphaFocusedPolicy — Hub-proximal junctions + economy sustain + fast ramp
# Hypothesis: concentrate alignment near hub for defensibility and fast re-align.
# Sustain economy longer by keeping miners focused on carbon bottleneck.
# ---------------------------------------------------------------------------

class AlphaFocusedAgentPolicy(AlphaAggressiveAgentPolicy):
    """Focused variant: hub-proximal junctions, carbon-biased mining, sustained economy.

    Key changes from Aggressive:
    1. Network weight 0.5 — prefer junctions near hub/network (shorter trips, easier re-align)
    2. More aligners from step 0 (3 instead of 2) for faster initial coverage
    3. Carbon-biased mining: more miners prioritize carbon (3x consumed by aligner gear)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefer hub-proximal junctions
        self._network_weight = 0.5
        # Force carbon bias for even-numbered agents (50% carbon miners)
        if self._agent_id % 2 == 0:
            self._default_resource_bias = "carbon"
            self._resource_bias = "carbon"

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Faster ramp: 3 aligners from step 0, otherwise same as Aggressive."""
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
            if step < 50:
                return 2, 0  # Faster: 2 aligners from step 0 (was 1)
            if min_res < 7 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 200 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents: same as Aggressive (2 at step 0 — 3 burns too much carbon)
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaFocusedPolicy(MettagridSemanticPolicy):
    """Focused: hub-proximal junctions, carbon mining, sustained economy."""
    short_names = ["alpha-focused"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaFocusedAgentPolicy(
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
# AlphaSustainV2Policy — Maximum economy sustain with Aggressive base.
# Key idea: keep 3+ miners always, scale alignment to economy health.
# Late-game idle aligners mine instead of scramble.
# ---------------------------------------------------------------------------

class AlphaSustainV2AgentPolicy(AlphaAggressiveAgentPolicy):
    """Sustain V2: tighter economy-responsive alignment that never over-extends.

    Key changes from Aggressive:
    1. Aligner budget STRICTLY capped by economy health
    2. More miners at all times — never fewer than 3 (for 8-agent)
    3. Idle aligners mine (not scramble) in late game to sustain economy
    4. Carbon-biased mining for all agents
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All agents carbon-biased (carbon is the bottleneck)
        self._default_resource_bias = "carbon"
        self._resource_bias = "carbon"

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > mine. In late game, idle mine instead of scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Late game: idle mine to sustain economy (don't scramble)
        min_res = _h.team_min_resource(state)
        if step >= 3000 or min_res < 20:
            return self._miner_action(state, summary_prefix="idle_align_")

        # Early game: scramble if economy healthy
        if int(state.self_state.inventory.get("heart", 0)) > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy-gated alignment: never more aligners than economy can sustain."""
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

        # Minimum 2 miners always
        min_miners = max(2, num_agents // 3)

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            max_aligners = num_agents - min_miners
            if min_res >= 50:
                return min(max_aligners, 2), 0
            return min(max_aligners, 1), 0

        # 5+ agents: economy-gated
        if step < 30:
            return 2, 0

        max_pressure = num_agents - min_miners

        if min_res < 3 and not can_hearts:
            return 1, 0
        elif min_res < 7:
            aligner_budget = min(2, max_pressure)
        elif min_res < 20:
            aligner_budget = min(3, max_pressure)
        elif min_res < 50:
            aligner_budget = min(4, max_pressure)
        elif min_res < 100:
            aligner_budget = min(5, max_pressure)
        else:
            aligner_budget = max_pressure

        # Scramblers only with surplus economy, early game only
        scrambler_budget = 0
        if step < 3000 and step >= 200 and min_res >= 14:
            scrambler_budget = min(1, aligner_budget // 3)
            aligner_budget = max(aligner_budget - scrambler_budget, 1)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaSustainV2Policy(MettagridSemanticPolicy):
    """SustainV2: economy-gated alignment, carbon-biased mining, late-game mining."""
    short_names = ["alpha-sustain-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSustainV2AgentPolicy(
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
# AlphaCarbonBoostPolicy — Aggressive + carbon-biased mining.
# Simplest possible fix for carbon depletion bottleneck.
# ---------------------------------------------------------------------------

class AlphaCarbonBoostAgentPolicy(AlphaAggressiveAgentPolicy):
    """Aggressive but 50% of miners prioritize carbon (the #1 bottleneck).

    Carbon is consumed 3x by aligner gear. Default bias only gives 25% carbon miners.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Even-numbered agents: carbon bias (50% vs default 25%)
        if self._agent_id % 2 == 0:
            self._default_resource_bias = "carbon"
            self._resource_bias = "carbon"


class AlphaAllCarbonAgentPolicy(AlphaAggressiveAgentPolicy):
    """100% carbon bias: ALL miners default to carbon.

    Carbon is 3x consumed. Resource_priority still sorts by lowest inventory,
    so miners will switch to other resources when carbon is abundant.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_resource_bias = "carbon"
        self._resource_bias = "carbon"


class AlphaAllCarbonPolicy(MettagridSemanticPolicy):
    """AllCarbon: Aggressive + 100% carbon-biased miners."""
    short_names = ["alpha-all-carbon"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAllCarbonAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCarbonBoostPolicy(MettagridSemanticPolicy):
    """CarbonBoost: Aggressive + 50% carbon-biased miners."""
    short_names = ["alpha-carbon-boost"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCarbonBoostAgentPolicy(
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
# AlphaTeamFixPolicy — Aggressive but uses actual team size for budgets.
# The bug: policy_env_info.num_agents=8 (total) in 4v4, causing budget overflow.
# Fix: use len(shared_team_ids) for per-team agent count.
# ---------------------------------------------------------------------------

class AlphaTeamFixAgentPolicy(AlphaAggressiveAgentPolicy):
    """Aggressive with proper per-team budget allocation.

    Fixes the num_agents bug where total (8) is used instead of per-team (4).
    This means budget calculations correctly leave miners when team is small.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive budgets using actual team size."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        # Use actual team size, not total agents
        num_agents = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            # Keep at least 1 miner
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 200 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents: Aggressive scaling with proper team size
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        return aligner_budget, scrambler_budget


class AlphaTeamFixPolicy(MettagridSemanticPolicy):
    """TeamFix: Aggressive + proper per-team budget allocation."""
    short_names = ["alpha-team-fix"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTeamFixAgentPolicy(
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
# AlphaSmartHybridPolicy — TeamFix budgets + carbon bias for 5+ agents
# Best of both worlds: proper budgets for 4a, carbon fix for 8a.
# ---------------------------------------------------------------------------

class AlphaSmartHybridAgentPolicy(AlphaTeamFixAgentPolicy):
    """Smart hybrid: TeamFix budgets + adaptive carbon bias.

    - 4 agents: balanced bias (all resources needed equally, can't afford carbon focus)
    - 5+ agents: carbon bias for even agents (carbon bottleneck with many agents)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._carbon_bias_applied = False

    def _preferred_miner_extractor(self, state: MettagridState) -> KnownEntity | None:
        """Apply carbon bias lazily once team size is known."""
        if not self._carbon_bias_applied:
            self._carbon_bias_applied = True
            team_size = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents
            if team_size >= 5 and self._agent_id % 2 == 0:
                self._default_resource_bias = "carbon"
                self._resource_bias = "carbon"
        return super()._preferred_miner_extractor(state)


class AlphaSmartHybridPolicy(MettagridSemanticPolicy):
    """SmartHybrid: TeamFix + carbon bias for large teams."""
    short_names = ["alpha-smart-hybrid"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSmartHybridAgentPolicy(
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
# AlphaHighEffAgentPolicy — Aggressive + efficient mining (high deposit threshold)
# + no scrambling (idle mine instead) + carbon bias
# Combines best elements from testing.
# ---------------------------------------------------------------------------

class AlphaTeamCarbonAgentPolicy(AlphaTeamFixAgentPolicy):
    """TeamFix + CarbonBoost: proper team-size budgets + carbon bias.

    Combines the two most impactful fixes:
    1. TeamFix: correct per-team agent count for budgets
    2. CarbonBoost: 50% carbon-biased miners for the #1 bottleneck
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._agent_id % 2 == 0:
            self._default_resource_bias = "carbon"
            self._resource_bias = "carbon"


class AlphaTeamCarbonPolicy(MettagridSemanticPolicy):
    """TeamCarbon: proper team-size budgets + carbon-biased mining."""
    short_names = ["alpha-team-carbon"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTeamCarbonAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaHighEffAgentPolicy(AlphaAggressiveAgentPolicy):
    """High efficiency: optimized mining + no scrambling waste + carbon bias.

    Key changes from Aggressive:
    1. Higher deposit threshold (20) — fewer trips to hub, more mining per trip
    2. Idle aligners mine instead of scramble — sustain economy, don't waste hearts
    3. Carbon bias for even agents — address carbon bottleneck
    4. No scramblers in early game — pure economy + alignment focus
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._agent_id % 2 == 0:
            self._default_resource_bias = "carbon"
            self._resource_bias = "carbon"

    def _should_deposit_resources(self, state: MettagridState) -> bool:
        """Higher deposit threshold (20) for more efficient mining trips."""
        cargo = _h.resource_total(state)
        if cargo <= 0:
            return False
        # Miners: batch to 20 before depositing
        threshold = 20 if _h.has_role_gear(state, "miner") else 4
        if cargo >= threshold:
            return True
        # Near hub, deposit anything
        hub = self._nearest_hub(state)
        if hub is not None:
            dist = _h.manhattan(_h.absolute_position(state), hub.position)
            if dist <= 2 and cargo >= 4:
                return True
        # If retreating with cargo, deposit
        hp = int(state.self_state.inventory.get("hp", 0))
        if hp < 30 and cargo >= 8:
            return True
        return False

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > mine. Never scramble (saves hearts)."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: ALWAYS mine to sustain economy (never scramble — saves hearts for alignment)
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Same as Aggressive but fewer scramblers — pure economy + alignment."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            if min_res >= 50 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            return aligner_budget, 0  # Zero scramblers

        # 5+ agents
        if step < 30:
            return 2, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        # Only 1 scrambler late game with surplus — pure alignment focus
        scrambler_budget = 0
        if step >= 5000 and min_res >= 50:
            scrambler_budget = 1

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaHighEffPolicy(MettagridSemanticPolicy):
    """HighEff: efficient mining, no scramble, carbon bias, pure alignment focus."""
    short_names = ["alpha-high-eff"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaHighEffAgentPolicy(
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
# AlphaRushPolicy — Optimized for tournament score >10
#
# Combines: TeamFix budgets + Aggressive idle-scramble + silicon-priority
# mining + faster alignment start + reduced deaths
# ---------------------------------------------------------------------------

class AlphaRushAgentPolicy(AlphaAggressiveAgentPolicy):
    """Rush: fast alignment with silicon-aware economy and smart scrambling.

    Key changes from Aggressive:
    1. TeamFix: use actual team size for budgets (not total agents)
    2. Silicon priority: 50% of miners always target silicon (the #1 bottleneck)
    3. Smarter budgets: more aligners earlier, fewer when economy is weak
    4. Faster first alignment start
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 50% of agents get silicon bias (the bottleneck resource)
        if self._agent_id % 2 == 1:
            self._default_resource_bias = "silicon"
            self._resource_bias = "silicon"

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """TeamFix budgets with aggressive alignment pressure."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        # Use actual team size
        num_agents = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 150 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 80:
                return 1, 0
            if min_res < 5 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 30 and step >= 400:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 100 and step >= 800:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 25:
            return 2, 0

        economy_surplus = min_res >= 80
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 80:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 2000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 150 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Prioritize silicon when it's low relative to others."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        others_min = min(v for k, v in resources.items() if k != "silicon")
        # If silicon is significantly lower, bias toward it
        if silicon < others_min * 0.7 and silicon < 50:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=_least_resource(resources))


class AlphaRushPolicy(MettagridSemanticPolicy):
    """Rush: fast alignment + silicon economy + TeamFix budgets."""
    short_names = ["alpha-rush"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaRushAgentPolicy(
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
# AlphaEconRushPolicy — Rush variant with economy-first strategy
# ---------------------------------------------------------------------------

class AlphaEconRushAgentPolicy(AlphaRushAgentPolicy):
    """EconRush: build strong economy first, then overwhelm with alignment."""

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Economy-first: delay alignment pressure until resources are strong."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 10 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 150 or (min_res < 10 and not can_hearts):
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 150 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 50:
            return 1, 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 5 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 150:
            pressure_budget = 2
        elif economy_crisis:
            pressure_budget = max(1, num_agents // 4)
        elif min_res < 10:
            pressure_budget = min(3, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 20:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 300 and min_res >= 10:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget


class AlphaEconRushPolicy(MettagridSemanticPolicy):
    """EconRush: economy-first then overwhelm with alignment."""
    short_names = ["alpha-econ-rush"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaEconRushAgentPolicy(
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
# AlphaTurboPolicy — Aggressive base (keep the num_agents "bug" since it
# accidentally creates better tournament budgets) + silicon-aware macro
# directive + earlier scrambling for network expansion
# ---------------------------------------------------------------------------

class AlphaTurboAgentPolicy(AlphaAggressiveAgentPolicy):
    """Turbo: Aggressive base + silicon-aware economy + faster scramble start.

    The num_agents bug actually HELPS in tournament because it makes
    small-team budgets more aggressive. Keep it.

    Changes from Aggressive:
    1. Silicon macro directive: bias all miners toward silicon when low
    2. Earlier scrambler start: step 100 instead of 200
    3. More scramblers in surplus: clear enemy junctions faster
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive budgets with earlier/more scramblers."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents  # Keep the bug!

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 80:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 400:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 100 and step >= 600:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 25:
            return 2, 0

        economy_surplus = min_res >= 80
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 80:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        # Earlier scramblers: start at step 100 (vs 200 in Aggressive)
        scrambler_budget = 0
        if step >= 2000 and min_res >= 14:
            scrambler_budget = min(3, pressure_budget // 3)
        elif step >= 100 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)
        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _macro_directive(self, state: MettagridState) -> MacroDirective:
        """Silicon-aware: bias miners toward silicon when it's the bottleneck."""
        resources = _shared_resources(state)
        silicon = resources.get("silicon", 0)
        others = [v for k, v in resources.items() if k != "silicon"]
        others_min = min(others) if others else 0
        # Strong silicon bias when it's clearly the bottleneck
        if silicon < others_min * 0.6:
            return MacroDirective(resource_bias="silicon")
        return MacroDirective(resource_bias=_least_resource(resources))


class AlphaTurboPolicy(MettagridSemanticPolicy):
    """Turbo: Aggressive + silicon-aware economy + earlier scramblers."""
    short_names = ["alpha-turbo"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTurboAgentPolicy(
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
# AlphaMaxAlignV2Policy — Pure alignment pressure.
# Maximum aligners, minimal scramblers, no idle-mine for aligners.
# Hypothesis: in cooperative scoring, more alignment = higher score for both.
# ---------------------------------------------------------------------------

class AlphaMaxAlignV2AgentPolicy(AlphaAggressiveAgentPolicy):
    """MaxAlignV2: Maximum alignment pressure. Keep num_agents bug.

    Changes from Aggressive:
    1. Even more aligners: 1 more aligner in each bracket
    2. Idle aligners: explore for new junctions instead of scrambling
    3. Reduced scrambler budget: only 1 scrambler, only when surplus
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > explore. Minimal scrambling."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble only if economy is very healthy, otherwise mine
        min_res = _h.team_min_resource(state)
        if int(state.self_state.inventory.get("heart", 0)) > 0 and min_res >= 30:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Help economy by mining
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Maximum alignment pressure, minimal scramblers."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 150 or (min_res < 7 and not can_hearts):
                return 0, 0
            return 1, 0

        if num_agents <= 4:
            if step < 80:
                return 1, 0
            if min_res < 5 and not can_hearts:
                return 1, 0
            aligner_budget = min(3, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                aligner_budget = num_agents - 1  # All but 1
            return aligner_budget, scrambler_budget

        # 5+ agents: max alignment
        if step < 25:
            return 2, 0

        economy_surplus = min_res >= 80
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            aligner_budget = min(num_agents - 1, 7)
            scrambler_budget = 1 if step >= 500 else 0
            return aligner_budget - scrambler_budget, scrambler_budget
        elif step < 80:
            return 3, 0
        elif economy_crisis:
            return max(2, num_agents // 3), 0
        elif min_res < 7:
            return min(5, num_agents - 2), 0
        else:
            return min(6, num_agents - 2), 0


class AlphaMaxAlignV2Policy(MettagridSemanticPolicy):
    """MaxAlignV2: maximum alignment pressure, minimal scramblers."""
    short_names = ["alpha-max-align-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxAlignV2AgentPolicy(
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
# AlphaSustainablePolicy — KEY POLICY
#
# The core problem: Aggressive's budget bug causes 0 miners in small teams.
# Economy collapses after step 2000-3000, junctions lost, score drops.
# In 10000-step games, the second half (5000-10000) has near-zero junctions.
#
# Fix: Aggressive alignment pressure but GUARANTEE at least 1 miner.
# Use shared_team_ids for team sizing (accurate), but keep aggressive budgets.
# ---------------------------------------------------------------------------

class AlphaSustainableAgentPolicy(AlphaAggressiveAgentPolicy):
    """Sustainable: Aggressive alignment with guaranteed economy.

    Key insight: In 10000-step tournament games, economy sustainability
    matters more than front-loading alignment. Average junctions in the
    second half can drop to ~0 without miners.

    Changes from Aggressive:
    1. Budget caps ensure at least 1 miner per team at all times
    2. Uses actual team size for the MINER FLOOR only (keep aggressive num_agents for pressure)
    3. More aggressive idle-mine when economy is struggling
    4. Adaptive resource bias based on actual bottleneck
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive pressure but never exceed (team_size - 1) total roles."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        can_hearts = _h.team_can_refill_hearts(state)
        # Use big num_agents for aggressive budgets
        num_agents = self.policy_env_info.num_agents
        # But use actual team size to cap roles (guarantee 1 miner)
        team_size = len(self._shared_team_ids) if self._shared_team_ids else num_agents
        max_roles = max(team_size - 1, 1)  # Always leave 1 miner

        if objective == "resource_coverage":
            return 0, 0

        if num_agents <= 2:
            if step < 200 or (min_res < 7 and not can_hearts):
                return 0, 0
            return min(1, max_roles), 0

        if num_agents <= 4:
            if step < 100:
                return min(1, max_roles), 0
            if min_res < 7 and not can_hearts:
                return min(1, max_roles), 0
            aligner_budget = min(2, num_agents - 1)
            scrambler_budget = 0
            if min_res >= 50 and step >= 500:
                aligner_budget = min(3, num_agents - 1)
            if min_res >= 200 and step >= 1000:
                scrambler_budget = 1
                aligner_budget = min(2, num_agents - 1 - scrambler_budget)
            # Cap to team_size - 1 (guarantee miner)
            total = aligner_budget + scrambler_budget
            if total > max_roles:
                scrambler_budget = min(scrambler_budget, max(0, max_roles - 1))
                aligner_budget = min(aligner_budget, max_roles - scrambler_budget)
            return aligner_budget, scrambler_budget

        # 5+ agents
        if step < 30:
            return min(2, max_roles), 0

        economy_surplus = min_res >= 100
        economy_crisis = min_res < 3 and not can_hearts

        if economy_surplus:
            pressure_budget = min(num_agents - 1, 7)
        elif step < 100:
            pressure_budget = 3
        elif economy_crisis:
            pressure_budget = max(2, num_agents // 3)
        elif min_res < 7:
            pressure_budget = min(4, num_agents - 2)
        else:
            pressure_budget = min(5, num_agents - 2)

        scrambler_budget = 0
        if step >= 3000 and min_res >= 14:
            scrambler_budget = min(2, pressure_budget // 3)
        elif step >= 200 and min_res >= 7:
            scrambler_budget = min(1, pressure_budget // 3)

        aligner_budget = max(pressure_budget - scrambler_budget, 1)

        # Cap to team_size - 1
        total = aligner_budget + scrambler_budget
        if total > max_roles:
            scrambler_budget = min(scrambler_budget, max(0, max_roles - 1))
            aligner_budget = min(aligner_budget, max_roles - scrambler_budget)

        if objective == "economy_bootstrap":
            return min(aligner_budget, 2), 0
        return aligner_budget, scrambler_budget

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: idle-mine when economy is weak instead of scrambling."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble ONLY if economy very healthy; otherwise MINE
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 20:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Economy needs help: mine
        return self._miner_action(state, summary_prefix="idle_align_")


class AlphaSustainablePolicy(MettagridSemanticPolicy):
    """Sustainable: Aggressive alignment with guaranteed economy sustainability."""
    short_names = ["alpha-sustainable"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSustainableAgentPolicy(
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
# AlphaSustainV3Policy — Sustainable + no scrambling + higher idle-mine threshold
#
# Hypothesis: in cooperative scoring, scrambling hurts BOTH teams.
# Save all hearts for alignment. Mine when not aligning.
# ---------------------------------------------------------------------------

class AlphaSustainV3AgentPolicy(AlphaSustainableAgentPolicy):
    """SustainV3: no scrambling, pure alignment + mining economy.

    Changes from Sustainable:
    1. Zero scramblers always (save hearts for alignment)
    2. Idle aligners ALWAYS mine (never scramble)
    3. Higher economy threshold for alignment pressure
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Same as Sustainable but zero scramblers."""
        aligner, _ = super()._pressure_budgets(state, objective=objective)
        return aligner, 0  # Never assign scramblers

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Aligner: align > expand > MINE. No scrambling ever."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Always mine when idle (never scramble — save hearts for alignment)
        return self._miner_action(state, summary_prefix="idle_align_")


class AlphaSustainV3Policy(MettagridSemanticPolicy):
    """SustainV3: no scrambling, pure alignment + mining."""
    short_names = ["alpha-sustain-v3"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaSustainV3AgentPolicy(
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
# AlphaAdaptiveTeamPolicy — THE KEY POLICY
#
# Adapts strategy based on actual team size:
# - Large teams (4+): Use Aggressive (with bug) for max alignment pressure
# - Small teams (2-3): Use Sustainable (miner guarantee) for economy
# - 1 agent: Pure mining→alignment cycle
#
# Aggressive 8a 10k: 15.73 (amazing!)
# Sustainable 4a 10k: 8.63 (good, beats Aggressive's 6.45)
# ---------------------------------------------------------------------------

class AlphaAdaptiveTeamAgentPolicy(AlphaAggressiveAgentPolicy):
    """AdaptiveTeam: Aggressive base but caps budget for small teams.

    For large teams (4+): pure Aggressive (no cap, bug helps)
    For small teams (2-3): cap budget to team_size-1 (guarantee miner)
    Also: idle aligners mine instead of scramble when economy < 20
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Aggressive budgets, capped for small teams."""
        # Get base Aggressive budgets
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)

        # Always cap to ensure at least 1 miner per team
        team_size = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents
        max_roles = max(team_size - 1, 1)
        total = aligner + scrambler
        if total > max_roles:
            scrambler = min(scrambler, max(0, max_roles - 1))
            aligner = min(aligner, max_roles - scrambler)

        return aligner, scrambler

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """For small teams, idle-mine instead of idle-scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble when economy healthy, mine otherwise
        min_res = _h.team_min_resource(state)
        # Higher threshold for scrambling = more conservative economy
        scramble_threshold = 20  # Only scramble with healthy economy

        if hearts > 0 and min_res >= scramble_threshold:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < scramble_threshold:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaAdaptiveTeamPolicy(MettagridSemanticPolicy):
    """AdaptiveTeam: Aggressive for large teams, Sustainable for small teams."""
    short_names = ["alpha-adaptive-team"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveTeamAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptiveTeamV2AgentPolicy(AlphaAdaptiveTeamAgentPolicy):
    """AdaptiveTeamV2: Safer retreat + gentle late-game economy scaling.

    Key improvements over AdaptiveTeam:
    1. Slightly more conservative retreat for all roles (reduce deaths)
    2. Very late game (>7000): if economy truly dead, cap aligners at 1
    3. Keep aggressive alignment in early-mid game (DON'T cut on temp dips)
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Standard budgets but reduce late-game when economy is truly dead."""
        step = state.step or self._step_index
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)

        # Only intervene in very late game when economy is genuinely collapsed
        if step >= 7000:
            resources = _shared_resources(state)
            min_res = min(resources.values())
            total_res = sum(resources.values())
            # Economy truly dead: can't make hearts (need 7 of each = 28 total)
            if min_res == 0 and total_res < 50:
                return min(aligner, 1), 0

        return aligner, scrambler

    def _should_retreat(self, state: MettagridState, role: str, safe_target: KnownEntity | None) -> bool:
        """Slightly more conservative retreat to reduce deaths."""
        hp = int(state.self_state.inventory.get("hp", 0))
        if safe_target is None:
            return hp <= _h.retreat_threshold(state, role) + 5
        safe_steps = max(0, _h.manhattan(_h.absolute_position(state), safe_target.position) - _h._JUNCTION_AOE_RANGE)
        margin = 12  # vs 10 in Aggressive
        if self._in_enemy_aoe(state, _h.absolute_position(state), team_id=_h.team_id(state)):
            margin += 10
        margin += int(state.self_state.inventory.get("heart", 0)) * 3
        margin += min(_h.resource_total(state), 12) // 3
        if not _h.has_role_gear(state, role):
            margin += 10
        step = state.step or self._step_index
        if step >= 2_500:
            margin += 7 if role in {"aligner", "scrambler"} else 5
        if hp <= safe_steps + margin:
            return True
        if role == "miner" and safe_target is not None:
            pos = _h.absolute_position(state)
            dist = _h.manhattan(pos, safe_target.position)
            if dist > _MINER_MAX_HUB_DISTANCE and hp < dist + 20:
                return True
        return False


class AlphaAdaptiveTeamV2Policy(MettagridSemanticPolicy):
    """AdaptiveTeamV2: Late-game economy fixes."""
    short_names = ["alpha-adaptive-team-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveTeamV2AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptiveTeamV3AgentPolicy(AlphaAdaptiveTeamAgentPolicy):
    """AdaptiveTeamV3: Tournament-optimized with slower early ramp.

    Key insight from tournament analysis: in 4v4 matches, both policies
    independently allocate 3 aligners each = 6 aligners + 2 miners for
    8 total agents. This crashes the economy by step 500 (carbon drops to 0).

    Fix: slower early-game ramp to ensure mining builds economy before
    alignment ramps up. This trades some early alignment speed for
    much better economy sustainability in tournament.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Slower early ramp for tournament compatibility."""
        step = state.step or self._step_index
        min_res = _h.team_min_resource(state)
        team_size = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents
        num_agents = self.policy_env_info.num_agents

        if objective == "resource_coverage":
            return 0, 0

        # Detect tournament: team_size < num_agents means partner policy exists
        in_tournament = team_size < num_agents

        if in_tournament:
            # Tournament mode: conservative early game, proportional allocation
            if step < 200:
                return 1, 0  # 1 aligner, rest mine — build economy first
            if step < 500:
                if min_res < 20:
                    return 1, 0  # Economy still building
                return min(2, team_size - 1), 0
            if step < 1000:
                if min_res < 10:
                    return 1, 0
                return min(2, team_size - 1), 0

            # After step 1000: standard AdaptiveTeam budgets
            aligner, scrambler = super()._pressure_budgets(state, objective=objective)
            # Extra economy check: if resources very low, pull back
            if min_res < 5:
                return min(aligner, 1), 0
            return aligner, scrambler
        else:
            # Self-play mode: use standard AdaptiveTeam budgets
            return super()._pressure_budgets(state, objective=objective)


class AlphaAdaptiveTeamV3Policy(MettagridSemanticPolicy):
    """AdaptiveTeamV3: Tournament-optimized with slower early ramp."""
    short_names = ["alpha-adaptive-team-v3"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveTeamV3AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaTournamentV2AgentPolicy(AlphaAdaptiveV3AgentPolicy):
    """TournamentV2: Best tournament strategy.

    Based on AdaptiveV3 (best tournament scorer at 5.5) with improvements:
    1. Budget cap to guarantee miners in sub-team
    2. Lower idle-scramble threshold (opponents are weak in tournament)
    3. Keep silicon-priority mining from Balanced base
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """AdaptiveV3 budgets + team cap for tournament safety."""
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)

        # Cap by actual sub-team size to guarantee miners
        team_size = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents
        max_roles = max(team_size - 1, 1)
        total = aligner + scrambler
        if total > max_roles:
            scrambler = min(scrambler, max(0, max_roles - 1))
            aligner = min(aligner, max_roles - scrambler)

        return aligner, scrambler

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Lower scramble threshold since tournament opponents are weak."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble more aggressively (opponents are weak)
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Mine when economy tight
        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaTournamentV2Policy(MettagridSemanticPolicy):
    """TournamentV2: AdaptiveV3 base + team cap + aggressive idle scramble."""
    short_names = ["alpha-tournament-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentV2AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptiveV4AgentPolicy(AlphaAdaptiveV3AgentPolicy):
    """AdaptiveV4: Faster ramp + lower idle-scramble threshold.

    Based on AdaptiveV3 (best tournament scorer) with tweaks:
    1. Lower resource thresholds for aligner ramp (20% faster scaling)
    2. Lower idle-scramble threshold (30 vs 50 in Balanced)
    3. No dedicated scramblers in budget (save hearts for aligners)
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Slightly faster ramp than AdaptiveV3, no dedicated scramblers."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res < 20:
                return 1, 0
            aligner_budget = 2
            if min_res >= 70 and step >= 400:
                aligner_budget = min(3, num_agents - 1)
            return aligner_budget, 0

        # 5+ agents: faster scaling, no dedicated scramblers
        if step < 30:
            return 2, 0

        if min_res < 7 and not can_hearts:
            return 1, 0
        elif min_res < 20:
            return 2, 0
        elif min_res < 60:
            return 3, 0
        elif min_res < 150:
            return 4, 0
        else:
            return min(5, num_agents - 2), 0

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Lower idle-scramble threshold (30 vs 50 in Balanced)."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 30:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        return self._miner_action(state, summary_prefix="idle_align_")


class AlphaAdaptiveV4Policy(MettagridSemanticPolicy):
    """AdaptiveV4: Faster ramp + lower idle-scramble threshold."""
    short_names = ["alpha-adaptive-v4"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveV4AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaAdaptiveV5AgentPolicy(AlphaAdaptiveV3AgentPolicy):
    """AdaptiveV5: AdaptiveV3 with NO idle scrambling. Pure align + mine.

    Hypothesis: scrambling wastes hearts that could be used for alignment.
    Against weak opponents, pure alignment might score better.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Never idle-scramble — always mine when idle."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Always mine when idle — no scrambling
        return self._miner_action(state, summary_prefix="idle_align_")

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """No dedicated scramblers — save all hearts for alignment."""
        aligner, _ = super()._pressure_budgets(state, objective=objective)
        return aligner, 0  # Zero scramblers always


class AlphaAdaptiveV5Policy(MettagridSemanticPolicy):
    """AdaptiveV5: Pure align + mine, no scrambling."""
    short_names = ["alpha-adaptive-v5"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaAdaptiveV5AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaTournamentV3AgentPolicy(AlphaTournamentV2AgentPolicy):
    """TournamentV3: v348 but with more aggressive scrambling.

    Lowers idle-mine threshold from 30 to 15, meaning aligners scramble
    more often when idle. Also adds very aggressive economy scaling.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Even more aggressive idle scramble."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble even more aggressively
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 10:  # Was 14 in V2
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # Only mine when economy truly struggling
        if min_res < 15:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaTournamentV3Policy(MettagridSemanticPolicy):
    """TournamentV3: More aggressive scrambling variant of TournamentV2."""
    short_names = ["alpha-tournament-v3"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentV3AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaTournamentV4AgentPolicy(AlphaAdaptiveV4AgentPolicy):
    """TournamentV4: V4 faster ramp + V2 team cap + V2 idle scramble.

    Combines: AdaptiveV4 faster scaling + team-size cap + aggressive scramble.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """V4 budgets + team cap."""
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)

        # Cap by actual sub-team size
        team_size = len(self._shared_team_ids) if self._shared_team_ids else self.policy_env_info.num_agents
        max_roles = max(team_size - 1, 1)
        total = aligner + scrambler
        if total > max_roles:
            scrambler = min(scrambler, max(0, max_roles - 1))
            aligner = min(aligner, max_roles - scrambler)

        return aligner, scrambler

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """V2's aggressive idle scramble at min_res>=14."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaTournamentV4Policy(MettagridSemanticPolicy):
    """TournamentV4: V4 faster ramp + V2 team cap + V2 idle scramble."""
    short_names = ["alpha-tournament-v4"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentV4AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


# Wide exploration offsets for discovering junctions far from hub (covers 88x88 map)
_WIDE_EXPLORE_OFFSETS = (
    (0, -36), (25, -25), (36, 0), (25, 25),
    (0, 36), (-25, 25), (-36, 0), (-25, -25),
    (0, -28), (20, -20), (28, 0), (20, 20),
    (0, 28), (-20, 20), (-28, 0), (-20, -20),
)


class AlphaExplorerV2AgentPolicy(AlphaTournamentV2AgentPolicy):
    """TournamentV2 + wide exploration when frontier is empty.

    Key insight: agents only discover ~14 of ~65 junctions because exploration
    radius is too small (~22). When frontier=0, this policy sends idle aligners
    on wide exploration patterns (radius 36) to discover new junction clusters
    that can extend the network chain.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._wide_explore_index = 0
        self._frontier_empty_steps = 0

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """TournamentV2 aligner + wide exploration when frontier empty."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            self._frontier_empty_steps = 0
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
            self._clear_target_claim()
            self._clear_sticky_target()
            self._frontier_empty_steps = 0
            assert hub is not None
            return self._move_to_known(state, hub, summary="batch_hearts", vibe="change_vibe_heart")

        target = self._preferred_alignable_neutral_junction(state)
        if target is not None:
            self._frontier_empty_steps = 0
            self._claim_target(target.position)
            self._set_sticky_target(target.position, target.entity_type)
            return self._move_to_known(state, target, summary="align_junction", vibe="change_vibe_aligner")

        self._clear_target_claim()
        self._clear_sticky_target()
        if _h.resource_total(state) > 0:
            depot = self._nearest_friendly_depot(state)
            if depot is not None:
                return self._move_to_known(state, depot, summary="deposit_cargo", vibe="change_vibe_aligner")

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                self._frontier_empty_steps = 0
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # FRONTIER EMPTY — track how long we've been idle
        self._frontier_empty_steps += 1

        # Scramble if we have hearts and economy is OK (like TournamentV2)
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                # Alternate: 2/3 scramble + 1/3 explore to maintain pressure while discovering
                if self._frontier_empty_steps % 3 != 0:
                    return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        # WIDE EXPLORATION: explore far from hub to discover new junction clusters
        if hub is not None and hp > 60:
            hub_pos = hub.position
            offset_idx = (self._wide_explore_index + self._agent_id * 3) % len(_WIDE_EXPLORE_OFFSETS)
            ox, oy = _WIDE_EXPLORE_OFFSETS[offset_idx]
            explore_target = (hub_pos[0] + ox, hub_pos[1] + oy)
            if _h.manhattan(current_pos, explore_target) <= 3:
                self._wide_explore_index += 1
                offset_idx = (self._wide_explore_index + self._agent_id * 3) % len(_WIDE_EXPLORE_OFFSETS)
                ox, oy = _WIDE_EXPLORE_OFFSETS[offset_idx]
                explore_target = (hub_pos[0] + ox, hub_pos[1] + oy)
            return self._move_to_position(state, explore_target, summary="wide_explore", vibe="change_vibe_aligner")

        # Low HP or no hub: mine to stay alive
        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaExplorerV2Policy(MettagridSemanticPolicy):
    """TournamentV2 + wide exploration when frontier is empty."""
    short_names = ["alpha-explorer-v2"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaExplorerV2AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCaptureAgentPolicy(AlphaTournamentV2AgentPolicy):
    """TournamentV2 + capture-optimized scramble targeting.

    Key insight: idle-scrambling is 72% of aligner time, but many scrambled
    junctions can't be immediately re-aligned (too far from network).
    This policy prioritizes scrambling enemy junctions within alignment range
    of our network, creating immediate capture (scramble→realign) cycles.
    """

    def _preferred_scramble_target(self, state: MettagridState) -> KnownEntity | None:
        """Override: strongly prefer enemy junctions we can realign after scrambling."""
        team_id = _h.team_id(state)
        current_pos = _h.absolute_position(state)
        hub = self._nearest_hub(state)

        enemy_junctions = self._known_junctions(
            state, predicate=lambda j: j.owner not in {None, "neutral", team_id}
        )
        if not enemy_junctions:
            return None

        hubs = self._world_model.entities(entity_type="hub", predicate=lambda e: e.team == team_id)
        friendly_junctions = self._known_junctions(state, predicate=lambda j: j.owner == team_id)
        network_sources = [*hubs, *friendly_junctions]

        # Partition: capturable (within alignment range) vs non-capturable
        capturable = []
        non_capturable = []
        for ej in enemy_junctions:
            if _h.within_alignment_network(ej.position, network_sources):
                capturable.append(ej)
            else:
                non_capturable.append(ej)

        # Strongly prefer capturable targets (add -50 bonus)
        hub_pos = hub.position if hub else current_pos
        neutral_junctions = self._world_model.entities(
            entity_type="junction",
            predicate=lambda e: e.owner in {None, "neutral"},
        )

        best = None
        best_score = float("inf")
        for ej in enemy_junctions:
            base_score = _h.scramble_target_score(
                current_position=current_pos,
                hub_position=hub_pos,
                candidate=ej,
                neutral_junctions=neutral_junctions,
                friendly_junctions=friendly_junctions,
            )[0]
            # Massive bonus for capturable junctions (within our alignment range)
            if ej in capturable:
                base_score -= 50.0
            if base_score < best_score:
                best_score = base_score
                best = ej

        return best


class AlphaCapturePolicy(MettagridSemanticPolicy):
    """TournamentV2 + capture-optimized scramble targeting."""
    short_names = ["alpha-capture"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCaptureAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaCapturePlusAgentPolicy(AlphaCaptureAgentPolicy):
    """Capture + faster heart cycle + lower batch target.

    Reduces heart batch target to 2 (from 3) so aligners spend less time
    at hub and more time in the scramble→realign cycle. With 10000 steps,
    every trip to hub costs ~30-60 steps of lost alignment time.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Lower batch threshold: go align with 2 hearts instead of waiting for 3."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        # Skip batching entirely in early game
        if step < 200:
            pass
        elif hearts < 2 and hub is not None:
            # Only batch to 2 hearts (not 3-6 like default)
            hub_dist = _h.manhattan(_h.absolute_position(state), hub.position)
            if hub_dist <= 1 and _h.team_can_refill_hearts(state):
                return self._move_to_known(state, hub, summary="quick_batch_hearts", vibe="change_vibe_heart")

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

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble (capture-optimized) at lower threshold
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 10:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaCapturePlusPolicy(MettagridSemanticPolicy):
    """Capture-optimized + faster heart cycle."""
    short_names = ["alpha-capture-plus"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaCapturePlusAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaTournamentV5AgentPolicy(AlphaCaptureAgentPolicy):
    """TournamentV5: Capture targeting + faster 4a ramp + lower scramble threshold.

    Optimized for tournament where opponents are weaker than self-play:
    1. Capture-optimized scramble targeting (from AlphaCapture)
    2. For 4a: start 2 aligners at step 50 (not 100), 3 at min_res >= 50
    3. Lower idle-scramble threshold: min_res >= 10 (from 14)
    4. Budget: all-mine phase only until can_hearts (step ~80), then max pressure
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """Faster ramp for 4a, otherwise same as TournamentV2."""
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
            # Faster ramp: 2 aligners as soon as hearts available
            if step < 50:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res < 15:
                return 1, 0
            aligner_budget = 2
            # More aggressive 3-aligner threshold
            if min_res >= 50 and step >= 300:
                aligner_budget = min(3, num_agents - 1)
            return aligner_budget, 0

        # 5+ agents: delegate to parent (AdaptiveV3 + team cap)
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)
        return aligner, scrambler

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Lower scramble threshold + capture targeting (inherited)."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # Idle: scramble at lower threshold (10 vs 14) — opponents are weak in tournament
        min_res = _h.team_min_resource(state)
        if hearts > 0 and min_res >= 10:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaTournamentV5Policy(MettagridSemanticPolicy):
    """TournamentV5: Capture + faster 4a ramp + lower scramble threshold."""
    short_names = ["alpha-tournament-v5"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaTournamentV5AgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaPatrolAgentPolicy(AlphaCaptureAgentPolicy):
    """TournamentV2 + patrol mode: idle aligners stay near network edges.

    Instead of scrambling when idle, 1-2 agents patrol near the outermost
    friendly junctions to re-align quickly when enemy scrambles them.
    Other agents still idle-scramble for offensive pressure.
    """

    def _aligner_action(self, state: MettagridState) -> tuple[Action, str]:
        """Mix of patrol (defense) and scramble (offense) when idle."""
        hearts = int(state.self_state.inventory.get("heart", 0))
        hub = self._nearest_hub(state)
        step = state.step or self._step_index

        if hearts <= 0:
            self._clear_target_claim()
            self._clear_sticky_target()
            if not _h.team_can_refill_hearts(state):
                return self._miner_action(state, summary_prefix="rebuild_hearts_")
            if hub is not None:
                return self._move_to_known(state, hub, summary="acquire_heart", vibe="change_vibe_heart")
            return self._explore_action(state, role="aligner", summary="find_hub_for_heart")

        if step < 200:
            pass
        elif _h.should_batch_hearts(state, role="aligner", hub_position=hub.position if hub else None):
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

        # Expand toward known unreachable junctions
        current_pos = _h.absolute_position(state)
        hp = int(state.self_state.inventory.get("hp", 0))
        unreachable = self._known_junctions(
            state, predicate=lambda j: j.owner in {None, "neutral"}
        )
        if unreachable:
            safe_unreachable = [
                j for j in unreachable
                if _h.manhattan(current_pos, j.position) < hp - 20
            ]
            targets = safe_unreachable if safe_unreachable else unreachable
            nearest = min(targets, key=lambda j: _h.manhattan(current_pos, j.position))
            dist = _h.manhattan(current_pos, nearest.position)
            if dist < hp - 20:
                return self._move_to_known(state, nearest, summary="expand_toward_junction", vibe="change_vibe_aligner")

        # IDLE: mix patrol and scramble based on agent ID
        # Even agents: patrol (defensive), Odd agents: scramble (offensive)
        min_res = _h.team_min_resource(state)
        team_id = _h.team_id(state)
        is_patrol_agent = (self._agent_id % 2 == 0)

        if is_patrol_agent and hearts > 0:
            # Patrol near outermost friendly junctions
            friendly = self._known_junctions(state, predicate=lambda j: j.owner == team_id)
            if friendly and hub is not None:
                hub_pos = hub.position
                # Find the outermost friendly junction (farthest from hub)
                outermost = max(friendly, key=lambda j: _h.manhattan(hub_pos, j.position))
                dist_to_patrol = _h.manhattan(current_pos, outermost.position)
                if dist_to_patrol > 5:
                    return self._move_to_known(state, outermost, summary="patrol_junction", vibe="change_vibe_aligner")
                # Already near patrol point: try scramble nearby enemy junctions
                if min_res >= 14:
                    scramble_target = self._preferred_scramble_target(state)
                    if scramble_target is not None:
                        # Only scramble nearby targets (within 20)
                        if _h.manhattan(current_pos, scramble_target.position) <= 20:
                            return self._move_to_known(state, scramble_target, summary="patrol_scramble", vibe="change_vibe_scrambler")
                return self._explore_action(state, role="aligner", summary="patrol_explore")

        # Odd agents or no hearts: standard idle scramble (like TournamentV2)
        if hearts > 0 and min_res >= 14:
            scramble_target = self._preferred_scramble_target(state)
            if scramble_target is not None:
                return self._move_to_known(state, scramble_target, summary="idle_align_scramble", vibe="change_vibe_scrambler")

        if min_res < 30:
            return self._miner_action(state, summary_prefix="idle_align_")
        return self._explore_action(state, role="aligner", summary="find_neutral_junction")


class AlphaPatrolPolicy(MettagridSemanticPolicy):
    """TournamentV2 + patrol mode for defensive junction holding."""
    short_names = ["alpha-patrol"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaPatrolAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]


class AlphaMaxPressure4aAgentPolicy(AlphaCaptureAgentPolicy):
    """Maximum pressure for 4a: 4 aligners + 0 miners when economy allows.

    With 4 agents, keeping 1 miner means only 3 aligners scramble/align.
    If economy is healthy (min_res > 50), switch to 4 aligners for max throughput.
    The idle-mine fallback in aligner_action handles economy maintenance.
    """

    def _pressure_budgets(self, state: MettagridState, *, objective: str | None = None) -> tuple[int, int]:
        """4a: go to 4 aligners when economy healthy."""
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
            if step < 100:
                return 1, 0
            if min_res < 7 and not can_hearts:
                return 1, 0
            if min_res < 30:
                return 1, 0
            # More aggressive: 3 aligners at min_res >= 30
            aligner_budget = min(3, num_agents - 1)
            # At min_res >= 100 AND step >= 500: ALL aligners (0 dedicated miners)
            if min_res >= 100 and step >= 500:
                aligner_budget = num_agents  # All 4 agents = aligners
            return aligner_budget, 0

        # 5+ agents: delegate to parent (TournamentV2 + capture)
        aligner, scrambler = super()._pressure_budgets(state, objective=objective)
        return aligner, scrambler


class AlphaMaxPressure4aPolicy(MettagridSemanticPolicy):
    """Max pressure 4a: 4 aligners when economy allows."""
    short_names = ["alpha-max-pressure-4a"]

    def agent_policy(self, agent_id: int) -> AgentPolicy:
        self._shared_team_ids.add(agent_id)
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = AlphaMaxPressure4aAgentPolicy(
                self.policy_env_info,
                agent_id=agent_id,
                world_model=SharedWorldModel(),
                shared_claims=self._shared_claims,
                shared_junctions=self._shared_junctions,
                shared_hotspots=self._shared_hotspots,
                shared_team_ids=self._shared_team_ids,
            )
        return self._agent_policies[agent_id]
