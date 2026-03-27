"""Alpha's CogsVsClips policy.

Key learnings:
- Move costs 4 energy. Solar gives 1 energy/tick. ~1 move per 4 ticks sustainable.
- Agents start ON the hub. Gear stations are ~3-4 cells from hub.
- 13x13 observation grid, center is (6,6).
- Must get gear, then hearts from hub, then align/mine/scramble.
- Alignment: walk aligner onto neutral junction (costs 1 heart).
- Score = avg aligned junctions per tick. More = better.
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

# Gear station offsets relative to hub (row_delta, col_delta)
# Based on semantic_cog.py: aligner(-3,4), scrambler(-1,4), miner(1,4), scout(3,4)
GEAR_STATION_OFFSETS = {
    "aligner": (-3, 4),
    "scrambler": (-1, 4),
    "miner": (1, 4),
    "scout": (3, 4),
}

# Role assignments: 3 miners (economy), 4 aligners (scoring), 1 scrambler (defense)
ROLE_MAP = {
    0: "miner",
    1: "miner",
    2: "miner",
    3: "aligner",
    4: "aligner",
    5: "aligner",
    6: "aligner",
    7: "scrambler",
}

MINER_DEPOSIT_THRESHOLD = 4


@dataclass
class AlphaState:
    role: str = "aligner"
    step_count: int = 0
    # Phase tracking
    phase: str = "get_gear"  # get_gear -> get_heart -> do_job -> return_hub
    # Navigation
    wander_dir: int = 0
    wander_steps: int = 0
    # Hub tracking - remember where hub was in observation
    hub_obs_pos: Optional[tuple[int, int]] = None
    # Track failed moves for unstick
    fail_count: int = 0
    unstick_remaining: int = 0
    unstick_dir: int = 0


class AlphaPolicyImpl(StatefulPolicyImpl[AlphaState]):
    def __init__(
        self,
        policy_env_info: PolicyEnvInterface,
        agent_id: int,
        shared_claims: dict[tuple[int, int], int],
    ):
        self._agent_id = agent_id
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

    def _find_all(self, obs: AgentObservation, tag_ids: set[int]) -> list[tuple[int, int, int]]:
        """Find entities matching tags. Returns [(row, col, manhattan_dist)] sorted by dist."""
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
        """Returns (neutral, friendly, enemy) lists of (row, col, dist)."""
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
        adj = {"north": (cr-1, cc), "south": (cr+1, cc), "east": (cr, cc+1), "west": (cr, cc-1)}
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

    def _move_toward(self, target: tuple[int, int], obs: AgentObservation) -> Action:
        cr, cc = self._center
        dr = target[0] - cr
        dc = target[1] - cc
        if dr == 0 and dc == 0:
            # Already at target - noop
            return self._act(self._fallback)

        walls = self._walls_around(obs)

        # Primary and secondary directions
        if abs(dr) >= abs(dc):
            dirs = ["south" if dr > 0 else "north",
                    "east" if dc > 0 else ("west" if dc < 0 else "east")]
        else:
            dirs = ["east" if dc > 0 else "west",
                    "south" if dr > 0 else ("north" if dr < 0 else "south")]
        # Add remaining
        for d in DIRECTIONS:
            if d not in dirs and d != OPPOSITE.get(dirs[0], ""):
                dirs.append(d)

        for d in dirs:
            if d not in walls:
                return self._act(f"move_{d}")
        return self._act(f"move_{dirs[0]}")

    def _wander(self, state: AlphaState, obs: AgentObservation) -> Action:
        walls = self._walls_around(obs)
        if state.wander_steps <= 0:
            state.wander_dir = (state.wander_dir + 1) % 4
            state.wander_steps = 6 + (self._agent_id * 3) % 7
        state.wander_steps -= 1
        d = DIRECTIONS[state.wander_dir]
        if d in walls:
            for offset in [1, 3, 2]:
                alt = DIRECTIONS[(state.wander_dir + offset) % 4]
                if alt not in walls:
                    d = alt
                    break
        return self._act(f"move_{d}")

    def _explore_direction(self, state: AlphaState, obs: AgentObservation) -> Action:
        """Explore in a pattern based on agent_id to spread agents out."""
        quadrants = [("north", "east"), ("south", "east"), ("north", "west"), ("south", "west")]
        q = quadrants[self._agent_id % 4]
        phase = (state.step_count // 12) % 2
        d = q[phase]
        walls = self._walls_around(obs)
        if d in walls:
            d = q[1 - phase]
        if d in walls:
            return self._wander(state, obs)
        return self._act(f"move_{d}")

    def _unstick(self, state: AlphaState, obs: AgentObservation) -> Action:
        walls = self._walls_around(obs)
        if state.unstick_remaining <= 0:
            state.unstick_dir = (state.unstick_dir + 1) % 4
            state.unstick_remaining = 6
        state.unstick_remaining -= 1
        d = DIRECTIONS[state.unstick_dir]
        if d in walls:
            for offset in [1, 3, 2]:
                alt = DIRECTIONS[(state.unstick_dir + offset) % 4]
                if alt not in walls:
                    d = alt
                    break
        return self._act(f"move_{d}")

    def step_with_state(
        self, obs: AgentObservation, state: AlphaState
    ) -> tuple[Action, AlphaState]:
        state.step_count += 1
        items = self._inventory(obs)

        # Track hub position when visible
        hub_pos = self._closest(obs, self._hub_tags)
        if hub_pos:
            state.hub_obs_pos = hub_pos

        # Check if last move failed (using last_action_move feature)
        last_move_ok = True
        for token in obs.tokens:
            if token.feature.name == "last_action_move" and token.location is None:
                # Global obs - value indicates if move succeeded
                last_move_ok = token.value != 0
                break

        if state.step_count > 1:
            if not last_move_ok:
                state.fail_count += 1
            else:
                state.fail_count = 0

        # Unstick if too many consecutive fails
        if state.fail_count >= 3:
            state.fail_count = 0
            state.unstick_remaining = 8
            state.unstick_dir = (state.unstick_dir + 1) % 4

        if state.unstick_remaining > 0:
            return self._unstick(state, obs), state

        # Determine gear for this role
        role_gear = state.role  # miner, aligner, scrambler
        has_gear = items.get(role_gear, 0) > 0
        has_heart = items.get("heart", 0) > 0

        # Phase logic
        if not has_gear:
            state.phase = "get_gear"
        elif state.role in ("aligner", "scrambler") and not has_heart:
            state.phase = "get_heart"
        elif state.role == "miner":
            total_res = sum(items.get(e, 0) for e in ELEMENTS)
            if total_res >= MINER_DEPOSIT_THRESHOLD:
                state.phase = "return_hub"
            elif state.phase == "return_hub" and total_res == 0:
                state.phase = "do_job"
            elif state.phase not in ("return_hub",):
                state.phase = "do_job"
        else:
            state.phase = "do_job"

        # HP monitoring
        hp = items.get("hp", 0)
        energy = items.get("energy", 0)
        if state.step_count <= 5 or state.step_count % 100 == 0:
            print(
                f"[COG] a={self._agent_id} s={state.step_count} "
                f"hp={hp} energy={energy} phase={state.phase} "
                f"hub_vis={hub_pos is not None} last_ok={last_move_ok}",
                file=sys.stderr,
            )

        # Log periodically
        if state.step_count % 1000 == 0:
            print(
                f"[COG] a={self._agent_id} s={state.step_count} "
                f"role={state.role} phase={state.phase} "
                f"gear={has_gear} heart={has_heart} "
                f"items={dict((k,v) for k,v in items.items() if v > 0)}",
                file=sys.stderr,
            )

        # Execute phase
        if state.phase == "get_gear":
            return self._phase_get_gear(obs, state, role_gear), state
        elif state.phase == "get_heart":
            return self._phase_get_heart(obs, state), state
        elif state.phase == "return_hub":
            return self._phase_return_hub(obs, state), state
        else:  # do_job
            return self._phase_do_job(obs, state, items), state

    def _phase_get_gear(self, obs: AgentObservation, state: AlphaState, gear_name: str) -> Action:
        """Navigate to the gear station for our role."""
        # Can we see the gear station?
        target = self._closest(obs, self._gear_tags[gear_name])
        if target:
            return self._move_toward(target, obs)

        # Can't see gear station - navigate toward hub, then offset
        hub_pos = self._closest(obs, self._hub_tags)
        if hub_pos:
            # Hub visible - compute gear station position relative to hub
            hr, hc = hub_pos
            dr, dc = GEAR_STATION_OFFSETS.get(gear_name, (0, 4))
            gear_r = hr + dr
            gear_c = hc + dc
            # Clamp to observation bounds
            obs_h = self._center[0] * 2 + 1
            obs_w = self._center[1] * 2 + 1
            gear_r = max(0, min(obs_h - 1, gear_r))
            gear_c = max(0, min(obs_w - 1, gear_c))
            return self._move_toward((gear_r, gear_c), obs)

        # Can't see hub either - wander (this shouldn't happen at game start)
        return self._wander(state, obs)

    def _phase_get_heart(self, obs: AgentObservation, state: AlphaState) -> Action:
        """Go to hub to get hearts."""
        hub_pos = self._closest(obs, self._hub_tags)
        if hub_pos:
            if hub_pos == self._center:
                # We're on the hub but don't have heart yet - hub might not have enough resources
                # Just wait (noop) or wander nearby
                return self._act(self._fallback)
            return self._move_toward(hub_pos, obs)
        # Can't see hub - wander to find it
        return self._wander(state, obs)

    def _phase_return_hub(self, obs: AgentObservation, state: AlphaState) -> Action:
        """Return to hub to deposit resources."""
        hub_pos = self._closest(obs, self._hub_tags)
        if hub_pos:
            if hub_pos == self._center:
                # On hub - resources auto-deposit. Switch to mining.
                state.phase = "do_job"
                return self._act(self._fallback)
            return self._move_toward(hub_pos, obs)
        return self._wander(state, obs)

    def _phase_do_job(self, obs: AgentObservation, state: AlphaState, items: dict[str, int]) -> Action:
        """Execute role-specific behavior."""
        if state.role == "miner":
            return self._job_mine(obs, state)
        elif state.role == "aligner":
            return self._job_align(obs, state)
        elif state.role == "scrambler":
            return self._job_scramble(obs, state)
        return self._wander(state, obs)

    def _job_mine(self, obs: AgentObservation, state: AlphaState) -> Action:
        """Find and walk onto extractors to mine resources."""
        target = self._closest(obs, self._extractor_tags)
        if target:
            if target == self._center:
                # On an extractor - stay or find another
                ents = self._find_all(obs, self._extractor_tags)
                if len(ents) > 1:
                    return self._move_toward((ents[1][0], ents[1][1]), obs)
                return self._wander(state, obs)
            return self._move_toward(target, obs)
        return self._explore_direction(state, obs)

    def _job_align(self, obs: AgentObservation, state: AlphaState) -> Action:
        """Find neutral junctions and align them."""
        neutral, _friendly, _enemy = self._junctions_by_team(obs)

        # Find best unclaimed neutral junction
        for r, c, d in neutral:
            pos = (r, c)
            if pos in self._shared_claims and self._shared_claims[pos] != self._agent_id:
                continue
            self._shared_claims[pos] = self._agent_id
            if pos == self._center:
                # We're on it - alignment should happen automatically
                # Find next target
                continue
            return self._move_toward(pos, obs)

        # Try any neutral
        for r, c, d in neutral:
            if (r, c) != self._center:
                return self._move_toward((r, c), obs)

        # No neutrals visible - explore to find junctions
        return self._explore_direction(state, obs)

    def _job_scramble(self, obs: AgentObservation, state: AlphaState) -> Action:
        """Find enemy junctions and scramble them."""
        _neutral, _friendly, enemy = self._junctions_by_team(obs)
        if enemy:
            target = (enemy[0][0], enemy[0][1])
            if target == self._center:
                if len(enemy) > 1:
                    return self._move_toward((enemy[1][0], enemy[1][1]), obs)
                return self._explore_direction(state, obs)
            return self._move_toward(target, obs)
        return self._explore_direction(state, obs)

    def initial_agent_state(self) -> AlphaState:
        role = ROLE_MAP.get(self._agent_id, "aligner")
        return AlphaState(
            role=role,
            wander_dir=self._agent_id % 4,
            wander_steps=6 + (self._agent_id * 3) % 7,
            unstick_dir=(self._agent_id + 1) % 4,
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
