"""Alpha policy - economy-first approach.

Critical insight: Hub needs resources to fund gear. Without deposits,
only a few agents can get gear from starting resources.

Strategy:
1. EVERYONE starts as miner to fund the economy
2. After depositing resources, agents switch to their assigned role
3. Aligners grab hearts and align junctions
4. Scramblers disrupt enemy junctions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mettagrid.policy.policy import MultiAgentPolicy, StatefulAgentPolicy, StatefulPolicyImpl
from mettagrid.policy.policy_env_interface import PolicyEnvInterface
from mettagrid.simulator import Action
from mettagrid.simulator.interface import AgentObservation

GEAR = ("aligner", "scrambler", "miner", "scout")
ELEMENTS = ("carbon", "oxygen", "germanium", "silicon")
WANDER_DIRECTIONS = ("east", "south", "west", "north")
WANDER_STEPS = 8


@dataclass
class CogState:
    wander_dir_idx: int = 0
    wander_remaining: int = WANDER_STEPS
    has_deposited: bool = False
    mining_phase_done: bool = False


class AlphaCogImpl(StatefulPolicyImpl[CogState]):
    def __init__(self, policy_env_info: PolicyEnvInterface, agent_id: int):
        self._id = agent_id
        self._pei = policy_env_info
        self._action_set = set(policy_env_info.action_names)
        self._vibe_set = set(policy_env_info.vibe_action_names)
        self._fallback = "noop" if "noop" in self._action_set else policy_env_info.action_names[0]
        self._center = (policy_env_info.obs_height // 2, policy_env_info.obs_width // 2)
        self._tag_map = {name: idx for idx, name in enumerate(policy_env_info.tags)}
        self._step = 0

        self._tag_ids: dict[str, set[int]] = {}
        for name in ["hub", "junction", "wall",
                      "carbon_extractor", "oxygen_extractor", "germanium_extractor", "silicon_extractor",
                      "c:aligner", "c:scrambler", "c:miner", "c:scout",
                      "team:cogs", "team:clips", "net:cogs", "net:clips",
                      "chest"]:
            ids = set()
            if name in self._tag_map:
                ids.add(self._tag_map[name])
            if f"type:{name}" in self._tag_map:
                ids.add(self._tag_map[f"type:{name}"])
            self._tag_ids[name] = ids

        self._extractor_tags = set()
        for e in ELEMENTS:
            self._extractor_tags |= self._tag_ids.get(f"{e}_extractor", set())

        self._any_station_tags = set()
        for g in GEAR:
            self._any_station_tags |= self._tag_ids.get(f"c:{g}", set())

        self._hub_heart_tags = self._tag_ids.get("hub", set()) | self._tag_ids.get("chest", set())

        # Role: 2 permanent miners, rest start mining then switch
        if agent_id <= 1:
            self._final_role = "miner"
        elif agent_id <= 6:
            self._final_role = "aligner"
        else:
            self._final_role = "scrambler"

    def _closest(self, obs: AgentObservation, tag_ids: set[int]) -> Optional[tuple[int, int]]:
        if not tag_ids:
            return None
        best, best_d = None, 999
        for token in obs.tokens:
            if token.feature.name != "tag" or int(token.value) not in tag_ids:
                continue
            loc = token.location
            if loc is None:
                continue
            d = abs(loc.row - self._center[0]) + abs(loc.col - self._center[1])
            if d < best_d:
                best_d = d
                best = (loc.row, loc.col)
        return best

    def _inv(self, obs: AgentObservation) -> dict[str, int]:
        items: dict[str, int] = {}
        for token in obs.tokens:
            loc = token.location
            if loc is None or (loc.row, loc.col) != self._center:
                continue
            fn = token.feature.name
            if not fn.startswith("inv:"):
                continue
            suffix = fn[4:]
            nm, sep, pstr = suffix.rpartition(":p")
            if not sep or not nm or not pstr.isdigit():
                nm, power = suffix, 0
            else:
                power = int(pstr)
            val = int(token.value)
            if val > 0:
                base = max(int(token.feature.normalization), 1)
                items[nm] = items.get(nm, 0) + val * (base ** power)
        return items

    def _cell_tags(self, obs: AgentObservation) -> dict[tuple[int, int], set[int]]:
        """Build tag sets per cell."""
        ct: dict[tuple[int, int], set[int]] = {}
        for token in obs.tokens:
            if token.feature.name != "tag":
                continue
            loc = token.location
            if loc is None:
                continue
            ct.setdefault((loc.row, loc.col), set()).add(int(token.value))
        return ct

    def _neutral_junction(self, obs: AgentObservation) -> Optional[tuple[int, int]]:
        junc_tags = self._tag_ids.get("junction", set())
        cogs_tags = self._tag_ids.get("team:cogs", set())
        clips_tags = self._tag_ids.get("team:clips", set())
        if not junc_tags:
            return None
        ct = self._cell_tags(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            if not (tags & junc_tags):
                continue
            if tags & cogs_tags:
                continue
            if tags & clips_tags:
                continue
            d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
            if d < best_d:
                best_d = d
                best = pos
        return best

    def _enemy_junction(self, obs: AgentObservation) -> Optional[tuple[int, int]]:
        junc_tags = self._tag_ids.get("junction", set())
        clips_tags = self._tag_ids.get("team:clips", set())
        if not junc_tags or not clips_tags:
            return None
        ct = self._cell_tags(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            if (tags & junc_tags) and (tags & clips_tags):
                d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
                if d < best_d:
                    best_d = d
                    best = pos
        return best

    def _deposit_target(self, obs: AgentObservation) -> Optional[tuple[int, int]]:
        hub_tags = self._tag_ids.get("hub", set())
        junc_tags = self._tag_ids.get("junction", set())
        cogs_tags = self._tag_ids.get("team:cogs", set())
        ct = self._cell_tags(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            ok = False
            if (tags & hub_tags) and (not cogs_tags or (tags & cogs_tags)):
                ok = True
            if (tags & junc_tags) and cogs_tags and (tags & cogs_tags):
                ok = True
            if ok:
                d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
                if d < best_d:
                    best_d = d
                    best = pos
        return best

    def _action(self, name: str, vibe: str | None = None) -> Action:
        an = name if name in self._action_set else self._fallback
        vn = vibe if vibe and vibe in self._vibe_set else None
        return Action(name=an, vibe=vn)

    def _wander(self, state: CogState, vibe: str | None = None) -> tuple[Action, CogState]:
        if state.wander_remaining <= 0:
            state.wander_dir_idx = (state.wander_dir_idx + 1) % 4
            state.wander_remaining = WANDER_STEPS + (self._id * 2)  # Stagger wander lengths
        d = WANDER_DIRECTIONS[(state.wander_dir_idx + self._id) % 4]  # Stagger starting direction
        state.wander_remaining -= 1
        return self._action(f"move_{d}", vibe), state

    def _move_toward(self, state: CogState, target: tuple[int, int], vibe: str | None = None) -> tuple[Action, CogState]:
        dr = target[0] - self._center[0]
        dc = target[1] - self._center[1]
        if dr == 0 and dc == 0:
            return self._action(self._fallback, vibe), state
        if abs(dr) >= abs(dc):
            d = "south" if dr > 0 else "north"
        else:
            d = "east" if dc > 0 else "west"
        return self._action(f"move_{d}", vibe), state

    def initial_agent_state(self) -> CogState:
        return CogState(wander_dir_idx=self._id % 4)

    def step_with_state(self, obs: AgentObservation, state: CogState) -> tuple[Action, CogState]:
        self._step += 1
        items = self._inv(obs)
        res_total = sum(items.get(e, 0) for e in ELEMENTS)

        # What gear do we have?
        gear = None
        for g in GEAR:
            if items.get(g, 0) > 0:
                gear = g
                break

        has_heart = items.get("heart", 0) > 0

        # Phase 1: Early game - everyone mines and deposits
        if not state.mining_phase_done:
            if self._final_role == "miner":
                # Permanent miners skip mining phase
                state.mining_phase_done = True
            elif gear is None:
                # Get miner gear first (go to ANY station for now)
                target = self._closest(obs, self._any_station_tags)
                if target:
                    return self._move_toward(state, target, "change_vibe_gear")
                return self._wander(state, "change_vibe_gear")
            elif gear == "miner":
                # Mine and deposit
                if res_total >= 6 or (state.has_deposited and res_total >= 3):
                    dep = self._deposit_target(obs)
                    if dep:
                        return self._move_toward(state, dep, "change_vibe_miner")
                    # Can't see deposit, wander toward hub area
                    hub = self._closest(obs, self._tag_ids.get("hub", set()))
                    if hub:
                        return self._move_toward(state, hub, "change_vibe_miner")

                if res_total > 0 and state.has_deposited:
                    # Already deposited once, deposit remainder
                    dep = self._deposit_target(obs)
                    if dep:
                        return self._move_toward(state, dep, "change_vibe_miner")

                if res_total == 0 and state.has_deposited:
                    # Done depositing, switch to final role
                    state.mining_phase_done = True
                else:
                    # Mine
                    ext = self._closest(obs, self._extractor_tags)
                    if ext:
                        return self._move_toward(state, ext, "change_vibe_miner")
                    return self._wander(state, "change_vibe_miner")
            else:
                # Got non-miner gear accidentally, just use it
                state.mining_phase_done = True

        # Check if resource total hit deposit threshold (for handling the deposit transition)
        if res_total == 0 and gear == "miner" and state.has_deposited:
            state.mining_phase_done = True

        # Phase 2: Play assigned role
        if state.mining_phase_done:
            desired_gear = self._final_role

            if gear is None or (gear != desired_gear and desired_gear != "miner"):
                # Get the right gear
                target_tags = self._tag_ids.get(f"c:{desired_gear}", set())
                target = self._closest(obs, target_tags)
                if target:
                    return self._move_toward(state, target, "change_vibe_gear")
                # Any station as fallback
                target = self._closest(obs, self._any_station_tags)
                if target:
                    return self._move_toward(state, target, "change_vibe_gear")
                return self._wander(state, "change_vibe_gear")

            # We have our gear, execute role
            actual_role = gear

            if actual_role == "miner":
                if res_total >= 4:
                    dep = self._deposit_target(obs)
                    if dep:
                        return self._move_toward(state, dep, "change_vibe_miner")
                ext = self._closest(obs, self._extractor_tags)
                if ext:
                    return self._move_toward(state, ext, "change_vibe_miner")
                return self._wander(state, "change_vibe_miner")

            if actual_role == "aligner":
                if not has_heart:
                    hub = self._closest(obs, self._tag_ids.get("hub", set()))
                    if hub:
                        return self._move_toward(state, hub, "change_vibe_heart")
                    return self._wander(state, "change_vibe_heart")
                junc = self._neutral_junction(obs)
                if junc:
                    return self._move_toward(state, junc, "change_vibe_aligner")
                if res_total > 0:
                    dep = self._deposit_target(obs)
                    if dep:
                        return self._move_toward(state, dep, "change_vibe_aligner")
                return self._wander(state, "change_vibe_aligner")

            if actual_role == "scrambler":
                if not has_heart:
                    hub = self._closest(obs, self._tag_ids.get("hub", set()))
                    if hub:
                        return self._move_toward(state, hub, "change_vibe_heart")
                    return self._wander(state, "change_vibe_heart")
                enemy = self._enemy_junction(obs)
                if enemy:
                    return self._move_toward(state, enemy, "change_vibe_scrambler")
                return self._wander(state, "change_vibe_scrambler")

        return self._wander(state)


class AlphaPolicy(MultiAgentPolicy):
    short_names = ["alpha-cog"]

    def __init__(self, policy_env_info: PolicyEnvInterface, device: str = "cpu", **kwargs):
        super().__init__(policy_env_info, device=device, **kwargs)
        self._agents: dict[int, StatefulAgentPolicy[CogState]] = {}

    def agent_policy(self, agent_id: int) -> StatefulAgentPolicy[CogState]:
        if agent_id not in self._agents:
            self._agents[agent_id] = StatefulAgentPolicy(
                AlphaCogImpl(self._policy_env_info, agent_id),
                self._policy_env_info,
                agent_id=agent_id,
            )
        return self._agents[agent_id]
