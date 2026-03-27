"""Alpha's CogsVsClips policy v4.

Key improvements:
- All non-miners are aligners (maximize scoring)
- Wall-following when stuck instead of random unstick
- Larger exploration range (territory extends 19 tiles)
- Removed diagnostic code for performance
- Better exploration: longer sweeps with wall-following
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional

from mettagrid.policy.policy import MultiAgentPolicy, StatefulAgentPolicy, StatefulPolicyImpl
from mettagrid.policy.policy_env_interface import PolicyEnvInterface
from mettagrid.simulator import Action
from mettagrid.simulator.interface import AgentObservation

GEAR_NAMES = ("aligner", "scrambler", "miner", "scout")
ELEMENTS = ("carbon", "oxygen", "germanium", "silicon")
DIRECTIONS = ("north", "south", "east", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
DIR_DELTA = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
# For wall-following: turn right
TURN_RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
TURN_LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}

# Gear station offsets from hub: (row_delta, col_delta)
GEAR_STATION_OFFSETS = {
    "aligner": (4, -3),
    "scrambler": (4, -1),
    "miner": (4, 1),
    "scout": (4, 3),
}

# 2 miners, 6 aligners - maximize scoring agents
ROLE_MAP = {
    0: "miner",
    1: "miner",
    2: "aligner",
    3: "aligner",
    4: "aligner",
    5: "aligner",
    6: "aligner",
    7: "aligner",
}

MINER_DEPOSIT_THRESHOLD = 4
HP_DANGER = 40
MAX_RANGE = 18  # Territory extends ~19 tiles


@dataclass
class AlphaState:
    role: str = "aligner"
    step_count: int = 0
    phase: str = "get_gear"
    wander_dir: int = 0
    wander_steps: int = 0
    fail_count: int = 0
    unstick_remaining: int = 0
    unstick_dir: int = 0
    hub_wait_steps: int = 0
    explore_step: int = 0
    est_row: int = 0
    est_col: int = 0
    last_move_dir: str = ""
    hub_seen: bool = False
    # Wall-following state
    following_wall: bool = False
    wall_follow_dir: str = "east"
    wall_follow_steps: int = 0
    # Track aligned count for logging
    aligned_count: int = 0


class AlphaPolicyImpl(StatefulPolicyImpl[AlphaState]):
    def __init__(
        self,
        policy_env_info: PolicyEnvInterface,
        agent_id: int,
        shared_claims: dict[tuple[int, int], int],
    ):
        self._agent_id = agent_id
        self._policy_env_info = policy_env_info
        self._shared_claims = shared_claims

        self._action_names = policy_env_info.action_names
        self._action_name_set = set(self._action_names)
        self._fallback = "noop" if "noop" in self._action_name_set else self._action_names[0]
        self._center = (policy_env_info.obs_height // 2, policy_env_info.obs_width // 2)
        tag_map = {name: idx for idx, name in enumerate(policy_env_info.tags)}

        def resolve(names: list[str]) -> set[int]:
            ids: set[int] = set()
            for n in names:
                if n in tag_map:
                    ids.add(tag_map[n])
                if f"type:{n}" in tag_map:
                    ids.add(tag_map[f"type:{n}"])
            return ids

        self._hub_tags = resolve(["hub", "c:hub"])
        self._junction_tags = resolve(["junction"])
        self._extractor_tags = resolve([f"{e}_extractor" for e in ELEMENTS])
        self._element_extractor_tags = {e: resolve([f"{e}_extractor"]) for e in ELEMENTS}
        self._gear_tags = {g: resolve([f"c:{g}"]) for g in GEAR_NAMES}
        self._cogs_tags = resolve(["team:cogs", "net:cogs"])
        self._clips_tags = resolve(["team:clips", "net:clips"])
        self._wall_tags = resolve(["wall"])

    def _inventory(self, obs: AgentObservation) -> dict[str, int]:
        items: dict[str, int] = {}
        for token in obs.tokens:
            if token.location != self._center:
                continue
            name = token.feature.name
            if not name.startswith("inv:"):
                continue
            suffix = name[4:]
            if not suffix:
                continue
            item_name, sep, power_str = suffix.rpartition(":p")
            if not sep or not item_name or not power_str.isdigit():
                item_name = suffix
                power = 0
            else:
                power = int(power_str)
            value = int(token.value)
            if value <= 0:
                continue
            base = max(int(token.feature.normalization), 1)
            items[item_name] = items.get(item_name, 0) + value * (base ** power)
        return items

    def _hub_resources(self, obs: AgentObservation) -> dict[str, int]:
        res: dict[str, int] = {}
        for token in obs.tokens:
            if token.location is not None:
                continue
            name = token.feature.name
            if name.startswith("team:") and name[5:] in ELEMENTS:
                value = int(token.value)
                base = max(int(token.feature.normalization), 1)
                res[name[5:]] = value * base
        return res

    def _find_all(self, obs: AgentObservation, tag_ids: set[int]) -> list[tuple[int, int, int]]:
        if not tag_ids:
            return []
        results: list[tuple[int, int, int]] = []
        seen: set[tuple[int, int]] = set()
        cr, cc = self._center
        for token in obs.tokens:
            if token.feature.name != "tag" or token.value not in tag_ids:
                continue
            loc = token.location
            if loc is None or loc in seen:
                continue
            seen.add(loc)
            results.append((loc[0], loc[1], abs(loc[0] - cr) + abs(loc[1] - cc)))
        results.sort(key=lambda x: x[2])
        return results

    def _closest(self, obs: AgentObservation, tag_ids: set[int]) -> Optional[tuple[int, int]]:
        ents = self._find_all(obs, tag_ids)
        return (ents[0][0], ents[0][1]) if ents else None

    def _junctions_by_team(self, obs: AgentObservation):
        junctions = self._find_all(obs, self._junction_tags)
        if not junctions:
            return [], [], []
        cogs_locs: set[tuple[int, int]] = set()
        clips_locs: set[tuple[int, int]] = set()
        for token in obs.tokens:
            if token.feature.name != "tag":
                continue
            loc = token.location
            if loc is None:
                continue
            if token.value in self._cogs_tags:
                cogs_locs.add(loc)
            elif token.value in self._clips_tags:
                clips_locs.add(loc)
        neutral, friendly, enemy = [], [], []
        for r, c, d in junctions:
            pos = (r, c)
            if pos in cogs_locs:
                friendly.append((r, c, d))
            elif pos in clips_locs:
                enemy.append((r, c, d))
            else:
                neutral.append((r, c, d))
        return neutral, friendly, enemy

    def _walls_around(self, obs: AgentObservation) -> set[str]:
        walls: set[str] = set()
        cr, cc = self._center
        adj = {"north": (cr - 1, cc), "south": (cr + 1, cc), "east": (cr, cc + 1), "west": (cr, cc - 1)}
        for token in obs.tokens:
            if token.feature.name != "tag" or token.value not in self._wall_tags:
                continue
            loc = token.location
            if loc is None:
                continue
            for d, pos in adj.items():
                if loc == pos:
                    walls.add(d)
        return walls

    def _act(self, name: str) -> Action:
        return Action(name=name) if name in self._action_name_set else Action(name=self._fallback)

    def _move_dir(self, d: str, state: AlphaState) -> Action:
        state.last_move_dir = d
        return self._act(f"move_{d}")

    def _pick_dir(self, preferred: list[str], walls: set[str], state: AlphaState) -> Action:
        """Move in the first non-wall direction from preference list."""
        for d in preferred:
            if d not in walls:
                return self._move_dir(d, state)
        # All blocked - try anything
        for d in DIRECTIONS:
            if d not in walls:
                return self._move_dir(d, state)
        return self._move_dir(preferred[0], state)

    def _move_toward(self, target: tuple[int, int], obs: AgentObservation, state: AlphaState) -> Action:
        cr, cc = self._center
        dr = target[0] - cr
        dc = target[1] - cc
        if dr == 0 and dc == 0:
            return self._act(self._fallback)

        walls = self._walls_around(obs)
        if abs(dr) >= abs(dc):
            pref = ["south" if dr > 0 else "north",
                    "east" if dc > 0 else ("west" if dc < 0 else "east")]
        else:
            pref = ["east" if dc > 0 else "west",
                    "south" if dr > 0 else ("north" if dr < 0 else "south")]
        # Add perpendicular options (not opposite of primary)
        for d in DIRECTIONS:
            if d not in pref and d != OPPOSITE.get(pref[0], ""):
                pref.append(d)
        return self._pick_dir(pref, walls, state)

    def _move_toward_global(self, target_row: int, target_col: int, obs: AgentObservation, state: AlphaState) -> Action:
        dr = target_row - state.est_row
        dc = target_col - state.est_col
        if abs(dr) <= 1 and abs(dc) <= 1:
            return self._act(self._fallback)

        walls = self._walls_around(obs)
        if abs(dr) >= abs(dc):
            pref = ["south" if dr > 0 else "north",
                    "east" if dc > 0 else ("west" if dc < 0 else "east")]
        else:
            pref = ["east" if dc > 0 else "west",
                    "south" if dr > 0 else ("north" if dr < 0 else "south")]
        for d in DIRECTIONS:
            if d not in pref and d != OPPOSITE.get(pref[0], ""):
                pref.append(d)
        return self._pick_dir(pref, walls, state)

    def _explore(self, state: AlphaState, obs: AgentObservation) -> Action:
        """Explore with wall-following behavior for better coverage."""
        dist = abs(state.est_row) + abs(state.est_col)
        if dist >= MAX_RANGE:
            state.following_wall = False
            return self._move_toward_global(0, 0, obs, state)

        walls = self._walls_around(obs)
        state.explore_step += 1

        # If currently following a wall, continue wall-following
        if state.following_wall:
            state.wall_follow_steps += 1
            if state.wall_follow_steps > 30:
                # Stop following after a while to avoid infinite loops
                state.following_wall = False
            else:
                # Wall-following: try to move in wall_follow_dir
                # If blocked, turn right. If unblocked on left, turn left.
                d = state.wall_follow_dir
                left = TURN_LEFT[d]
                if left not in walls:
                    # Opening on left - turn left to follow wall
                    state.wall_follow_dir = left
                    return self._move_dir(left, state)
                elif d not in walls:
                    return self._move_dir(d, state)
                else:
                    # Blocked ahead - turn right
                    state.wall_follow_dir = TURN_RIGHT[d]
                    right = TURN_RIGHT[d]
                    if right not in walls:
                        return self._move_dir(right, state)
                    # Completely blocked - stop following
                    state.following_wall = False

        # Normal exploration: each agent explores different direction pattern
        # Use longer sweep periods (20 steps) for better coverage
        dirs_order = [
            ["east", "south", "west", "north"],
            ["south", "west", "north", "east"],
            ["west", "north", "east", "south"],
            ["north", "east", "south", "west"],
            ["east", "north", "west", "south"],
            ["south", "east", "north", "west"],
            ["west", "south", "east", "north"],
            ["north", "west", "south", "east"],
        ]
        pattern = dirs_order[self._agent_id % len(dirs_order)]
        idx = (state.explore_step // 20) % len(pattern)
        d = pattern[idx]

        if d in walls:
            # Start wall-following
            state.following_wall = True
            state.wall_follow_dir = TURN_RIGHT[d]
            state.wall_follow_steps = 0
            right = TURN_RIGHT[d]
            if right not in walls:
                return self._move_dir(right, state)
            # Try other directions
            for alt_d in [TURN_LEFT[d], OPPOSITE[d]]:
                if alt_d not in walls:
                    state.wall_follow_dir = alt_d
                    return self._move_dir(alt_d, state)
            return self._act(self._fallback)

        return self._move_dir(d, state)

    def _go_to_hub(self, obs: AgentObservation, state: AlphaState) -> Action:
        hub = self._closest(obs, self._hub_tags)
        if hub:
            if hub == self._center:
                return self._act(self._fallback)
            return self._move_toward(hub, obs, state)
        return self._move_toward_global(0, 0, obs, state)

    def step_with_state(
        self, obs: AgentObservation, state: AlphaState
    ) -> tuple[Action, AlphaState]:
        state.step_count += 1
        items = self._inventory(obs)
        hp = items.get("hp", 0)

        # Update position estimate
        last_move_ok = True
        for token in obs.tokens:
            if token.feature.name == "last_action_move" and token.location is None:
                last_move_ok = token.value != 0
                break

        if state.step_count > 1 and state.last_move_dir and last_move_ok:
            dr, dc = DIR_DELTA.get(state.last_move_dir, (0, 0))
            state.est_row += dr
            state.est_col += dc

        # Calibrate from hub
        hub_pos = self._closest(obs, self._hub_tags)
        if hub_pos:
            cr, cc = self._center
            state.est_row = -(hub_pos[0] - cr)
            state.est_col = -(hub_pos[1] - cc)
            state.hub_seen = True

        # Stuck detection
        if state.step_count > 1:
            if not last_move_ok:
                state.fail_count += 1
            else:
                state.fail_count = 0
                state.following_wall = False  # Reset wall following on successful move

        if state.fail_count >= 4:
            state.fail_count = 0
            # Start wall-following in a new direction
            state.following_wall = True
            state.wall_follow_dir = DIRECTIONS[(state.unstick_dir + 1) % 4]
            state.unstick_dir = (state.unstick_dir + 1) % 4
            state.wall_follow_steps = 0

        # HP safety
        if hp > 0 and hp < HP_DANGER:
            state.following_wall = False
            return self._go_to_hub(obs, state), state

        # Range safety
        dist = abs(state.est_row) + abs(state.est_col)
        if dist > MAX_RANGE:
            state.following_wall = False
            return self._move_toward_global(0, 0, obs, state), state

        # Phase logic
        role_gear = state.role
        has_gear = items.get(role_gear, 0) > 0
        has_heart = items.get("heart", 0) > 0

        if not has_gear:
            state.phase = "get_gear"
        elif state.role == "aligner" and not has_heart:
            state.phase = "get_heart"
        elif state.role == "miner":
            total_res = sum(items.get(e, 0) for e in ELEMENTS)
            if total_res >= MINER_DEPOSIT_THRESHOLD:
                state.phase = "return_hub"
            elif state.phase == "return_hub" and total_res == 0:
                state.phase = "do_job"
            elif state.phase != "return_hub":
                state.phase = "do_job"
        else:
            state.phase = "do_job"

        # Periodic logging
        if state.step_count % 2000 == 0:
            print(
                f"[COG] a={self._agent_id} s={state.step_count} "
                f"role={state.role} phase={state.phase} hp={hp} "
                f"pos=({state.est_row},{state.est_col}) "
                f"gear={has_gear} heart={has_heart} "
                f"aligned={state.aligned_count}",
                file=sys.stderr,
            )

        if state.phase == "get_gear":
            return self._phase_get_gear(obs, state), state
        elif state.phase == "get_heart":
            return self._phase_get_heart(obs, state, items), state
        elif state.phase == "return_hub":
            return self._phase_return_hub(obs, state), state
        else:
            return self._phase_do_job(obs, state, items), state

    def _phase_get_gear(self, obs: AgentObservation, state: AlphaState) -> Action:
        gear_name = state.role
        target = self._closest(obs, self._gear_tags[gear_name])
        if target:
            return self._move_toward(target, obs, state)
        # Navigate to gear station using dead-reckoning
        dr, dc = GEAR_STATION_OFFSETS.get(gear_name, (4, 1))
        return self._move_toward_global(dr, dc, obs, state)

    def _phase_get_heart(self, obs: AgentObservation, state: AlphaState, items: dict[str, int]) -> Action:
        hub = self._closest(obs, self._hub_tags)
        if hub:
            if hub == self._center:
                state.hub_wait_steps += 1
                if state.hub_wait_steps > 20:
                    state.hub_wait_steps = 0
                    # Hub lacks resources - mine a bit
                    target = self._closest(obs, self._extractor_tags)
                    if target and target != self._center:
                        return self._move_toward(target, obs, state)
                return self._act(self._fallback)
            state.hub_wait_steps = 0
            return self._move_toward(hub, obs, state)
        return self._move_toward_global(0, 0, obs, state)

    def _phase_return_hub(self, obs: AgentObservation, state: AlphaState) -> Action:
        hub = self._closest(obs, self._hub_tags)
        if hub:
            if hub == self._center:
                state.phase = "do_job"
                return self._act(self._fallback)
            return self._move_toward(hub, obs, state)
        return self._move_toward_global(0, 0, obs, state)

    def _phase_do_job(self, obs: AgentObservation, state: AlphaState, items: dict[str, int]) -> Action:
        if state.role == "miner":
            return self._job_mine(obs, state, items)
        elif state.role == "aligner":
            return self._job_align(obs, state, items)
        return self._explore(state, obs)

    def _job_mine(self, obs: AgentObservation, state: AlphaState, items: dict[str, int]) -> Action:
        hub_res = self._hub_resources(obs)
        min_e = min(ELEMENTS, key=lambda e: hub_res.get(e, 0) + items.get(e, 0))
        target = self._closest(obs, self._element_extractor_tags.get(min_e, set()))
        if target and target != self._center:
            return self._move_toward(target, obs, state)
        target = self._closest(obs, self._extractor_tags)
        if target and target != self._center:
            return self._move_toward(target, obs, state)
        return self._explore(state, obs)

    def _job_align(self, obs: AgentObservation, state: AlphaState, items: dict[str, int]) -> Action:
        neutral, _friendly, _enemy = self._junctions_by_team(obs)

        # Check if we just aligned (heart count decreased from last check)
        has_heart = items.get("heart", 0) > 0
        if not has_heart:
            # Used our heart - go get another one!
            state.phase = "get_heart"
            state.aligned_count += 1
            return self._go_to_hub(obs, state)

        # Find unclaimed neutral junction
        for r, c, d in neutral:
            pos = (r, c)
            if pos in self._shared_claims and self._shared_claims[pos] != self._agent_id:
                continue
            self._shared_claims[pos] = self._agent_id
            if pos == self._center:
                continue
            state.following_wall = False  # Found target, stop wall following
            return self._move_toward(pos, obs, state)

        # Try any neutral
        for r, c, d in neutral:
            if (r, c) != self._center:
                state.following_wall = False
                return self._move_toward((r, c), obs, state)

        # No junctions visible - explore
        return self._explore(state, obs)

    def initial_agent_state(self) -> AlphaState:
        role = ROLE_MAP.get(self._agent_id, "aligner")
        return AlphaState(
            role=role,
            wander_dir=self._agent_id % 4,
            wander_steps=6 + (self._agent_id * 3) % 7,
            unstick_dir=self._agent_id % 4,
        )


class AlphaPolicy(MultiAgentPolicy):
    short_names = ["alpha"]

    def __init__(self, policy_env_info: PolicyEnvInterface, device: str = "cpu", **kwargs):
        super().__init__(policy_env_info, device=device, **kwargs)
        self._agent_policies: dict[int, StatefulAgentPolicy[AlphaState]] = {}
        self._shared_claims: dict[tuple[int, int], int] = {}

    def agent_policy(self, agent_id: int) -> StatefulAgentPolicy[AlphaState]:
        if agent_id not in self._agent_policies:
            self._agent_policies[agent_id] = StatefulAgentPolicy(
                AlphaPolicyImpl(self._policy_env_info, agent_id, self._shared_claims),
                self._policy_env_info,
                agent_id=agent_id,
            )
        return self._agent_policies[agent_id]

    def reset(self) -> None:
        self._shared_claims.clear()
        for p in self._agent_policies.values():
            p.reset()
