"""Alpha policy - adaptive role approach.

Agents grab whatever gear they find and play that role.
Focus on reliable resource gathering, depositing, and junction alignment.
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
DIRECTIONS = ("north", "east", "south", "west")


@dataclass
class CogState:
    wander_idx: int = 0
    wander_remaining: int = 8
    last_action: str = ""
    consecutive_fails: int = 0


class AlphaCogImpl(StatefulPolicyImpl[CogState]):
    def __init__(self, policy_env_info: PolicyEnvInterface, agent_id: int):
        self._id = agent_id
        self._pei = policy_env_info
        self._actions = set(policy_env_info.action_names)
        self._vibes = set(policy_env_info.vibe_action_names)
        self._noop = "noop" if "noop" in self._actions else policy_env_info.action_names[0]
        self._center = (policy_env_info.obs_height // 2, policy_env_info.obs_width // 2)
        self._tags = {name: idx for idx, name in enumerate(policy_env_info.tags)}
        self._step = 0

        # Pre-resolve all tag IDs
        self._tid_cache: dict[str, int | None] = {}
        for name in policy_env_info.tags:
            self._tid_cache[name] = self._tags[name]

        # Build tag sets for each entity type
        self._hub_tags = self._resolve_tags(["hub"])
        self._junction_tags = self._resolve_tags(["junction"])
        self._cogs_tags = self._resolve_tags(["team:cogs"])
        self._clips_tags = self._resolve_tags(["team:clips"])
        self._extractor_tags = self._resolve_tags([f"{e}_extractor" for e in ELEMENTS])
        self._station_tags: dict[str, set[int]] = {}
        self._all_station_tags: set[int] = set()
        for g in GEAR:
            ids = self._resolve_tags([f"c:{g}"])
            self._station_tags[g] = ids
            self._all_station_tags |= ids
        self._heart_source_tags = self._resolve_tags(["hub", "chest"])

    def _resolve_tags(self, names: list[str]) -> set[int]:
        ids: set[int] = set()
        for name in names:
            if name in self._tags:
                ids.add(self._tags[name])
            t = f"type:{name}"
            if t in self._tags:
                ids.add(self._tags[t])
        return ids

    def _closest_tag(self, obs, tag_ids: set[int]) -> Optional[tuple[int, int]]:
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

    def _inv(self, obs) -> dict[str, int]:
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

    def _cell_tag_sets(self, obs) -> dict[tuple[int, int], set[int]]:
        ct: dict[tuple[int, int], set[int]] = {}
        for token in obs.tokens:
            if token.feature.name != "tag":
                continue
            loc = token.location
            if loc is None:
                continue
            ct.setdefault((loc.row, loc.col), set()).add(int(token.value))
        return ct

    def _find_neutral_junction(self, obs) -> Optional[tuple[int, int]]:
        ct = self._cell_tag_sets(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            if not (tags & self._junction_tags):
                continue
            if tags & self._cogs_tags:
                continue
            if tags & self._clips_tags:
                continue
            d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
            if d < best_d:
                best_d = d
                best = pos
        return best

    def _find_enemy_junction(self, obs) -> Optional[tuple[int, int]]:
        ct = self._cell_tag_sets(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            if (tags & self._junction_tags) and (tags & self._clips_tags):
                d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
                if d < best_d:
                    best_d = d
                    best = pos
        return best

    def _find_deposit(self, obs) -> Optional[tuple[int, int]]:
        ct = self._cell_tag_sets(obs)
        best, best_d = None, 999
        for pos, tags in ct.items():
            ok = False
            if (tags & self._hub_tags) and (not self._cogs_tags or (tags & self._cogs_tags)):
                ok = True
            if (tags & self._junction_tags) and self._cogs_tags and (tags & self._cogs_tags):
                ok = True
            if ok:
                d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
                if d < best_d:
                    best_d = d
                    best = pos
        return best

    def _action(self, name: str, vibe: str | None = None) -> Action:
        an = name if name in self._actions else self._noop
        vn = vibe if vibe and vibe in self._vibes else None
        return Action(name=an, vibe=vn)

    def _move_toward(self, state, target, vibe=None):
        if target is None:
            return self._wander(state, vibe)
        dr = target[0] - self._center[0]
        dc = target[1] - self._center[1]
        if dr == 0 and dc == 0:
            state.last_action = self._noop
            return self._action(self._noop, vibe), state

        # If we've been failing to move, try perpendicular direction
        if state.consecutive_fails >= 2:
            # Try perpendicular to get around obstacle
            if abs(dr) >= abs(dc):
                d = "east" if (self._id + self._step) % 2 == 0 else "west"
            else:
                d = "south" if (self._id + self._step) % 2 == 0 else "north"
            state.last_action = f"move_{d}"
            return self._action(f"move_{d}", vibe), state

        if abs(dr) >= abs(dc):
            d = "south" if dr > 0 else "north"
        else:
            d = "east" if dc > 0 else "west"
        state.last_action = f"move_{d}"
        return self._action(f"move_{d}", vibe), state

    def _wander(self, state, vibe=None):
        if state.wander_remaining <= 0:
            state.wander_idx = (state.wander_idx + 1) % 4
            state.wander_remaining = 6 + self._id * 2
        d = DIRECTIONS[(state.wander_idx + self._id) % 4]
        state.wander_remaining -= 1
        state.last_action = f"move_{d}"
        return self._action(f"move_{d}", vibe), state

    def initial_agent_state(self):
        return CogState(wander_idx=self._id % 4, wander_remaining=8 + self._id)

    def step_with_state(self, obs, state):
        self._step += 1

        # Check move result
        move_succeeded = None
        for token in obs.tokens:
            fn = token.feature.name
            if fn == "last_action_move":
                move_succeeded = int(token.value) > 0
                break

        if state.last_action.startswith("move_"):
            if move_succeeded is False or move_succeeded is None:
                state.consecutive_fails += 1
            else:
                state.consecutive_fails = 0

        if state.consecutive_fails >= 3:
            state.wander_idx = (state.wander_idx + 1) % 4
            state.wander_remaining = max(3, state.wander_remaining)

        items = self._inv(obs)

        if self._step % 500 == 0:
            gear = None
            for g in GEAR:
                if items.get(g, 0) > 0:
                    gear = g
                    break
            ct = self._cell_tag_sets(obs)
            n_junc = 0
            n_neutral = 0
            for pos, tags in ct.items():
                if tags & self._junction_tags:
                    n_junc += 1
                    if not (tags & self._cogs_tags) and not (tags & self._clips_tags):
                        n_neutral += 1
            with open("/tmp/cogames/debug.txt", "a") as f:
                f.write(f"[A{self._id}] step={self._step} gear={gear} heart={items.get('heart',0)} fails={state.consecutive_fails} junc={n_junc} neutral={n_neutral}\n")
        res = sum(items.get(e, 0) for e in ELEMENTS)

        # What gear do we have?
        gear = None
        for g in GEAR:
            if items.get(g, 0) > 0:
                gear = g
                break

        has_heart = items.get("heart", 0) > 0

        # No gear - go to nearest station
        if gear is None:
            target = self._closest_tag(obs, self._all_station_tags)
            if target:
                return self._move_toward(state, target, "change_vibe_gear")
            return self._wander(state, "change_vibe_gear")

        # MINER
        if gear == "miner":
            if res >= 4:
                dep = self._find_deposit(obs)
                if dep:
                    return self._move_toward(state, dep, "change_vibe_miner")
            ext = self._closest_tag(obs, self._extractor_tags)
            if ext:
                return self._move_toward(state, ext, "change_vibe_miner")
            return self._wander(state, "change_vibe_miner")

        # ALIGNER
        if gear == "aligner":
            if not has_heart:
                hub = self._closest_tag(obs, self._heart_source_tags)
                if hub:
                    return self._move_toward(state, hub, "change_vibe_heart")
                return self._wander(state, "change_vibe_heart")
            junc = self._find_neutral_junction(obs)
            if junc:
                return self._move_toward(state, junc, "change_vibe_aligner")
            if res > 0:
                dep = self._find_deposit(obs)
                if dep:
                    return self._move_toward(state, dep, "change_vibe_aligner")
            return self._wander(state, "change_vibe_aligner")

        # SCRAMBLER
        if gear == "scrambler":
            if not has_heart:
                hub = self._closest_tag(obs, self._heart_source_tags)
                if hub:
                    return self._move_toward(state, hub, "change_vibe_heart")
                return self._wander(state, "change_vibe_heart")
            enemy = self._find_enemy_junction(obs)
            if enemy:
                return self._move_toward(state, enemy, "change_vibe_scrambler")
            return self._wander(state, "change_vibe_scrambler")

        # SCOUT or unknown - mine/explore
        if res >= 4:
            dep = self._find_deposit(obs)
            if dep:
                return self._move_toward(state, dep)
        ext = self._closest_tag(obs, self._extractor_tags)
        if ext:
            return self._move_toward(state, ext)
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
