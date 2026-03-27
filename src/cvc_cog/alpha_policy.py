"""Alpha policy - hub-centric junction alignment strategy.

Key insights from debugging:
1. Junctions must be within 25 cells of hub to align
2. Agents get stuck against objects (on_use fires but agent doesn't move)
3. Need robust wall/obstacle avoidance
4. Most junctions near hub start neutral - grab them fast
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
DELTAS = {"north": (-1, 0), "east": (0, 1), "south": (1, 0), "west": (0, -1)}


@dataclass
class CogState:
    wander_idx: int = 0
    wander_rem: int = 8
    last_action: str = ""
    fails: int = 0
    last_pos: tuple[int, int] = (0, 0)  # track center position hasn't changed


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

        self._hub_tags = self._res(["hub"])
        self._junction_tags = self._res(["junction"])
        self._cogs_tags = self._res(["team:cogs"])
        self._clips_tags = self._res(["team:clips"])
        self._extractor_tags = self._res([f"{e}_extractor" for e in ELEMENTS])
        self._wall_tags = self._res(["wall"])
        self._station_tags: dict[str, set[int]] = {}
        self._all_station_tags: set[int] = set()
        for g in GEAR:
            ids = self._res([f"c:{g}"])
            self._station_tags[g] = ids
            self._all_station_tags |= ids

    def _res(self, names: list[str]) -> set[int]:
        ids: set[int] = set()
        for n in names:
            if n in self._tags:
                ids.add(self._tags[n])
            t = f"type:{n}"
            if t in self._tags:
                ids.add(self._tags[t])
        return ids

    def _inv(self, obs) -> dict[str, int]:
        items: dict[str, int] = {}
        for tok in obs.tokens:
            loc = tok.location
            if loc is None or (loc.row, loc.col) != self._center:
                continue
            fn = tok.feature.name
            if not fn.startswith("inv:"):
                continue
            suffix = fn[4:]
            nm, sep, pstr = suffix.rpartition(":p")
            if not sep or not nm or not pstr.isdigit():
                nm, power = suffix, 0
            else:
                power = int(pstr)
            val = int(tok.value)
            if val > 0:
                base = max(int(tok.feature.normalization), 1)
                items[nm] = items.get(nm, 0) + val * (base ** power)
        return items

    def _parse(self, obs):
        """Parse observation into cell tag sets and wall set."""
        cells: dict[tuple[int, int], set[int]] = {}
        walls: set[tuple[int, int]] = set()
        for tok in obs.tokens:
            if tok.feature.name != "tag":
                continue
            loc = tok.location
            if loc is None:
                continue
            pos = (loc.row, loc.col)
            v = int(tok.value)
            cells.setdefault(pos, set()).add(v)
            if v in self._wall_tags:
                walls.add(pos)
        return cells, walls

    def _closest(self, cells, tag_ids, exclude_tags=None):
        best, best_d = None, 999
        for pos, tags in cells.items():
            if not (tags & tag_ids):
                continue
            if exclude_tags and (tags & exclude_tags):
                continue
            d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
            if d < best_d:
                best_d = d
                best = pos
        return best

    def _neutral_junction(self, cells):
        best, best_d = None, 999
        for pos, tags in cells.items():
            if not (tags & self._junction_tags):
                continue
            if tags & self._cogs_tags or tags & self._clips_tags:
                continue
            d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
            if d < best_d:
                best_d = d
                best = pos
        return best

    def _enemy_junction(self, cells):
        best, best_d = None, 999
        for pos, tags in cells.items():
            if (tags & self._junction_tags) and (tags & self._clips_tags):
                d = abs(pos[0] - self._center[0]) + abs(pos[1] - self._center[1])
                if d < best_d:
                    best_d = d
                    best = pos
        return best

    def _deposit(self, cells):
        best, best_d = None, 999
        for pos, tags in cells.items():
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

    def _act(self, name, vibe=None):
        an = name if name in self._actions else self._noop
        vn = vibe if vibe and vibe in self._vibes else None
        return Action(name=an, vibe=vn)

    def _move(self, state, target, walls, vibe=None):
        if target is None:
            return self._wander(state, walls, vibe)
        dr = target[0] - self._center[0]
        dc = target[1] - self._center[1]
        if dr == 0 and dc == 0:
            state.last_action = self._noop
            return self._act(self._noop, vibe), state

        # Rank all 4 directions by distance reduction, skip walls
        cands = []
        for d, (ddr, ddc) in DELTAS.items():
            npos = (self._center[0] + ddr, self._center[1] + ddc)
            if npos in walls:
                continue
            nd = abs(target[0] - npos[0]) + abs(target[1] - npos[1])
            cands.append((nd, d))
        cands.sort()

        if cands:
            # If stuck, skip the direction that failed
            if state.fails >= 2 and len(cands) > 1 and f"move_{cands[0][1]}" == state.last_action:
                d = cands[1][1]
            else:
                d = cands[0][1]
            state.last_action = f"move_{d}"
            return self._act(f"move_{d}", vibe), state

        # All blocked by walls, try primary anyway
        if abs(dr) >= abs(dc):
            d = "south" if dr > 0 else "north"
        else:
            d = "east" if dc > 0 else "west"
        state.last_action = f"move_{d}"
        return self._act(f"move_{d}", vibe), state

    def _wander(self, state, walls, vibe=None):
        if state.wander_rem <= 0:
            state.wander_idx = (state.wander_idx + 1) % 4
            state.wander_rem = 6 + (self._id % 4) * 3
        d = DIRECTIONS[(state.wander_idx + self._id) % 4]
        # If wall ahead, try next direction
        ddr, ddc = DELTAS[d]
        npos = (self._center[0] + ddr, self._center[1] + ddc)
        if npos in walls:
            state.wander_idx = (state.wander_idx + 1) % 4
            d = DIRECTIONS[(state.wander_idx + self._id) % 4]
        state.wander_rem -= 1
        state.last_action = f"move_{d}"
        return self._act(f"move_{d}", vibe), state

    def initial_agent_state(self):
        return CogState(wander_idx=self._id % 4, wander_rem=8 + self._id, last_pos=self._center)

    def step_with_state(self, obs, state):
        self._step += 1
        items = self._inv(obs)
        cells, walls = self._parse(obs)

        # Also treat other agents as soft obstacles for pathfinding
        # (they block movement too)

        # Stuck detection: if last action was a move and we're at same
        # agent_id position (center always = center, so use last_action)
        if state.last_action.startswith("move_"):
            # Check last_action_move feature
            moved = True
            for tok in obs.tokens:
                if tok.feature.name == "last_action_move":
                    moved = int(tok.value) > 0
                    break
            if not moved:
                state.fails += 1
                # Add the blocked cell as a wall
                if state.last_action.startswith("move_"):
                    d = state.last_action.split("_")[1]
                    if d in DELTAS:
                        ddr, ddc = DELTAS[d]
                        walls.add((self._center[0] + ddr, self._center[1] + ddc))
            else:
                state.fails = 0

        # Force direction change when very stuck
        if state.fails >= 4:
            state.wander_idx = (state.wander_idx + 1 + (self._step % 3)) % 4
            state.wander_rem = 3
            state.fails = 0

        # What gear?
        gear = None
        for g in GEAR:
            if items.get(g, 0) > 0:
                gear = g
                break

        has_heart = items.get("heart", 0) > 0
        res = sum(items.get(e, 0) for e in ELEMENTS)

        # No gear - find station
        if gear is None:
            target = self._closest(cells, self._all_station_tags)
            if target:
                return self._move(state, target, walls, "change_vibe_gear")
            return self._wander(state, walls, "change_vibe_gear")

        # MINER
        if gear == "miner":
            # Always try to deposit when we see a deposit point and have resources
            if res > 0:
                dep = self._deposit(cells)
                if dep:
                    return self._move(state, dep, walls, "change_vibe_miner")
            # Find extractor
            ext = self._closest(cells, self._extractor_tags)
            if ext:
                return self._move(state, ext, walls, "change_vibe_miner")
            # Hub as deposit fallback
            hub = self._closest(cells, self._hub_tags)
            if hub and res > 0:
                return self._move(state, hub, walls, "change_vibe_miner")
            return self._wander(state, walls, "change_vibe_miner")

        # ALIGNER
        if gear == "aligner":
            if not has_heart:
                hub = self._closest(cells, self._hub_tags)
                if hub:
                    return self._move(state, hub, walls, "change_vibe_heart")
                return self._wander(state, walls, "change_vibe_heart")
            junc = self._neutral_junction(cells)
            if junc:
                return self._move(state, junc, walls, "change_vibe_aligner")
            if res > 0:
                dep = self._deposit(cells)
                if dep:
                    return self._move(state, dep, walls, "change_vibe_aligner")
            return self._wander(state, walls, "change_vibe_aligner")

        # SCRAMBLER
        if gear == "scrambler":
            if not has_heart:
                hub = self._closest(cells, self._hub_tags)
                if hub:
                    return self._move(state, hub, walls, "change_vibe_heart")
                return self._wander(state, walls, "change_vibe_heart")
            enemy = self._enemy_junction(cells)
            if enemy:
                return self._move(state, enemy, walls, "change_vibe_scrambler")
            return self._wander(state, walls, "change_vibe_scrambler")

        # SCOUT or unknown
        if res >= 4:
            dep = self._deposit(cells)
            if dep:
                return self._move(state, dep, walls)
        ext = self._closest(cells, self._extractor_tags)
        if ext:
            return self._move(state, ext, walls)
        return self._wander(state, walls)


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
