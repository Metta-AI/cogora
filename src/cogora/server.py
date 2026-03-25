"""Cogora MCP server — Observatory API as MCP tools."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from cogora.client import ObservatoryClient

logger = logging.getLogger(__name__)

NO_AUTH_MSG = (
    "Not authenticated with Observatory. "
    "Run `cogames auth login` or `uv run python devops/observatory_login.py` to get a token."
)


def _text(data: Any) -> list[types.TextContent]:
    if isinstance(data, str):
        return [types.TextContent(type="text", text=data)]
    return [types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _error(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"Error: {msg}")]


def _str_param(args: dict, key: str) -> str | None:
    v = args.get(key)
    return str(v) if v is not None else None


def _int_param(args: dict, key: str) -> int | None:
    v = args.get(key)
    return int(v) if v is not None else None


def _bool_param(args: dict, key: str) -> bool | None:
    v = args.get(key)
    return bool(v) if v is not None else None


def _list_str_param(args: dict, key: str) -> list[str] | None:
    v = args.get(key)
    if v is None:
        return None
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[types.Tool] = [
    # Identity
    types.Tool(
        name="cogora_whoami",
        description="Who am I? Returns your user email and team membership status.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="cogora_my_memberships",
        description="List all season memberships for my policy versions. Returns policy_version_id -> [season_names].",
        inputSchema={"type": "object", "properties": {}},
    ),
    # Seasons
    types.Tool(
        name="cogora_list_seasons",
        description="List all active tournament seasons (games). Each season is a competition you can enter.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="cogora_get_season",
        description="Get detailed info about a season including entrant counts and match stats.",
        inputSchema={
            "type": "object",
            "properties": {"season_name": {"type": "string", "description": "Season name (e.g. 'arena')"}},
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_season_versions",
        description="List all versions of a season.",
        inputSchema={
            "type": "object",
            "properties": {"season_name": {"type": "string"}},
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_list_compat_versions",
        description="List available episode runner compatibility versions.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # Leaderboards
    types.Tool(
        name="cogora_get_leaderboard",
        description="Get the leaderboard (rankings) for a season. Shows policies ranked by Elo/rating.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string", "description": "Season name"},
                "pool": {"type": "string", "description": "Optional pool name to scope leaderboard"},
            },
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_score_policies_leaderboard",
        description="Get the score-policies leaderboard for team seasons.",
        inputSchema={
            "type": "object",
            "properties": {"season_name": {"type": "string"}},
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_stage_leaderboard",
        description="Get a leaderboard for a specific stage/pool. Type can be 'policy', 'team', or 'score-policies'.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "leaderboard_type": {"type": "string", "enum": ["policy", "team", "score-policies"]},
                "pool_name": {"type": "string"},
            },
            "required": ["season_name", "leaderboard_type", "pool_name"],
        },
    ),
    # Policies
    types.Tool(
        name="cogora_list_policies",
        description="Search policies by name. Returns policy names with version counts.",
        inputSchema={
            "type": "object",
            "properties": {
                "name_exact": {"type": "string", "description": "Exact name match"},
                "name_fuzzy": {"type": "string", "description": "Fuzzy name search"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
    ),
    types.Tool(
        name="cogora_get_policy_versions",
        description="List policy versions with filtering options.",
        inputSchema={
            "type": "object",
            "properties": {
                "name_exact": {"type": "string"},
                "name_fuzzy": {"type": "string"},
                "version": {"type": "integer"},
                "policy_id": {"type": "string", "description": "Filter by policy UUID"},
                "mine": {"type": "boolean", "description": "Only show my policy versions"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
    ),
    types.Tool(
        name="cogora_get_policy_version",
        description="Get details about a specific policy version by its UUID.",
        inputSchema={
            "type": "object",
            "properties": {"policy_version_id": {"type": "string", "description": "Policy version UUID"}},
            "required": ["policy_version_id"],
        },
    ),
    types.Tool(
        name="cogora_get_season_policies",
        description="List all policies submitted to a season with their pool memberships and match counts.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "mine": {"type": "boolean", "description": "Only show my policies"},
            },
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_policy_memberships",
        description="Get membership history for a policy version across all seasons.",
        inputSchema={
            "type": "object",
            "properties": {"policy_version_id": {"type": "string"}},
            "required": ["policy_version_id"],
        },
    ),
    # Matches
    types.Tool(
        name="cogora_get_matches",
        description="List matches in a season. Can filter by pool and policy.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
                "pool_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter to specific pools",
                },
                "policy_version_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter to matches containing these policy versions",
                },
            },
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_match",
        description="Get detailed info about a specific match including episode data.",
        inputSchema={
            "type": "object",
            "properties": {"match_id": {"type": "string", "description": "Match UUID"}},
            "required": ["match_id"],
        },
    ),
    types.Tool(
        name="cogora_get_match_artifact",
        description="Get an artifact (e.g. logs) from a match for a specific policy you own.",
        inputSchema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "artifact_type": {"type": "string", "description": "Artifact type, e.g. 'logs'"},
            },
            "required": ["match_id", "policy_version_id", "artifact_type"],
        },
    ),
    types.Tool(
        name="cogora_list_match_policy_logs",
        description="List policy log files for a specific policy in a match.",
        inputSchema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
            },
            "required": ["match_id", "policy_version_id"],
        },
    ),
    types.Tool(
        name="cogora_get_match_policy_log",
        description="Get the policy log for a specific agent in a match.",
        inputSchema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "agent_idx": {"type": "integer"},
            },
            "required": ["match_id", "policy_version_id", "agent_idx"],
        },
    ),
    # Episodes
    types.Tool(
        name="cogora_list_episodes",
        description="List episodes with optional filtering by policy version and tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "policy_version_id": {"type": "string"},
                "tags": {"type": "string", "description": "Comma-separated key:value filters"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
    ),
    types.Tool(
        name="cogora_get_episode",
        description="Get detailed info about a specific episode.",
        inputSchema={
            "type": "object",
            "properties": {"episode_id": {"type": "string"}},
            "required": ["episode_id"],
        },
    ),
    types.Tool(
        name="cogora_query_episodes",
        description="Query episodes with advanced filtering (policy version IDs, episode IDs, tag filters).",
        inputSchema={
            "type": "object",
            "properties": {
                "primary_policy_version_ids": {"type": "array", "items": {"type": "string"}},
                "episode_ids": {"type": "array", "items": {"type": "string"}},
                "tag_filters": {
                    "type": "object",
                    "description": "Map of tag key to list of allowed values (or null for any)",
                },
                "limit": {"type": "integer", "default": 200},
                "offset": {"type": "integer", "default": 0},
            },
        },
    ),
    # Submissions
    types.Tool(
        name="cogora_submit_policy",
        description="Submit a policy version to a tournament season.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "policy_version_id": {"type": "string"},
            },
            "required": ["season_name", "policy_version_id"],
        },
    ),
    # Pools & Configs
    types.Tool(
        name="cogora_get_pool_config",
        description="Get the environment configuration for a pool in a season.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "pool_name": {"type": "string"},
            },
            "required": ["season_name", "pool_name"],
        },
    ),
    types.Tool(
        name="cogora_get_config",
        description="Get a MettagridEnvConfig by its UUID.",
        inputSchema={
            "type": "object",
            "properties": {"config_id": {"type": "string"}},
            "required": ["config_id"],
        },
    ),
    # Teams
    types.Tool(
        name="cogora_get_teams",
        description="List teams in a season with filtering by pool, elimination status, and policy.",
        inputSchema={
            "type": "object",
            "properties": {
                "season_name": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
                "pool_name": {"type": "string"},
                "eliminated": {"type": "boolean"},
                "policy_version_id": {"type": "string"},
            },
            "required": ["season_name"],
        },
    ),
    # Stages & Progress
    types.Tool(
        name="cogora_get_stages",
        description="List tournament stages for a season with match and policy counts.",
        inputSchema={
            "type": "object",
            "properties": {"season_name": {"type": "string"}},
            "required": ["season_name"],
        },
    ),
    types.Tool(
        name="cogora_get_progress",
        description="Get team tournament progress for a season.",
        inputSchema={
            "type": "object",
            "properties": {"season_name": {"type": "string"}},
            "required": ["season_name"],
        },
    ),
    # Jobs (softmax-only)
    types.Tool(
        name="cogora_list_jobs",
        description="List jobs with filtering. Softmax team members only.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_type": {"type": "string", "description": "Filter by job type"},
                "statuses": {"type": "array", "items": {"type": "string"}},
                "job_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "season_id": {"type": "string"},
                "pool_id": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
                "offset": {"type": "integer", "default": 0},
            },
        },
    ),
    types.Tool(
        name="cogora_get_job",
        description="Get details about a specific job. Softmax team members only.",
        inputSchema={
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    ),
    types.Tool(
        name="cogora_get_job_episode_stats",
        description="Get per-policy stats for a completed job's episode. Softmax team members only.",
        inputSchema={
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


async def handle_tool(client: ObservatoryClient, name: str, args: dict[str, Any]) -> list[types.TextContent]:
    if not client.authenticated and name != "cogora_whoami":
        return _error(NO_AUTH_MSG)

    match name:
        # Identity
        case "cogora_whoami":
            if not client.authenticated:
                return _error(NO_AUTH_MSG)
            return _text(await client.get("/whoami"))

        case "cogora_my_memberships":
            return _text(await client.get("/tournament/my-memberships"))

        # Seasons
        case "cogora_list_seasons":
            return _text(await client.get("/tournament/seasons"))

        case "cogora_get_season":
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}"))

        case "cogora_get_season_versions":
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/versions"))

        case "cogora_list_compat_versions":
            return _text(await client.get("/tournament/compat-versions"))

        # Leaderboards
        case "cogora_get_leaderboard":
            params = {"pool": _str_param(args, "pool")}
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/leaderboard", params))

        case "cogora_get_score_policies_leaderboard":
            return _text(
                await client.get(f"/tournament/seasons/{args['season_name']}/score-policies-leaderboard")
            )

        case "cogora_get_stage_leaderboard":
            return _text(
                await client.get(
                    f"/tournament/seasons/{args['season_name']}/leaderboard/{args['leaderboard_type']}/{args['pool_name']}"
                )
            )

        # Policies
        case "cogora_list_policies":
            params = {
                "name_exact": _str_param(args, "name_exact"),
                "name_fuzzy": _str_param(args, "name_fuzzy"),
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            return _text(await client.get("/stats/policies", params))

        case "cogora_get_policy_versions":
            params = {
                "name_exact": _str_param(args, "name_exact"),
                "name_fuzzy": _str_param(args, "name_fuzzy"),
                "version": _int_param(args, "version"),
                "policy_id": _str_param(args, "policy_id"),
                "mine": _bool_param(args, "mine"),
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            return _text(await client.get("/stats/policy-versions", params))

        case "cogora_get_policy_version":
            return _text(await client.get(f"/stats/policy-versions/{args['policy_version_id']}"))

        case "cogora_get_season_policies":
            params = {"mine": _bool_param(args, "mine")}
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/policies", params))

        case "cogora_get_policy_memberships":
            return _text(await client.get(f"/tournament/policies/{args['policy_version_id']}/memberships"))

        # Matches
        case "cogora_get_matches":
            params: dict[str, Any] = {
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            pool_names = _list_str_param(args, "pool_names")
            if pool_names:
                params["pool_names"] = pool_names
            pv_ids = _list_str_param(args, "policy_version_ids")
            if pv_ids:
                params["policy_version_ids"] = pv_ids
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/matches", params))

        case "cogora_get_match":
            return _text(await client.get(f"/tournament/matches/{args['match_id']}"))

        case "cogora_get_match_artifact":
            path = f"/tournament/matches/{args['match_id']}/{args['policy_version_id']}/artifacts/{args['artifact_type']}"
            return _text(await client.get(path))

        case "cogora_list_match_policy_logs":
            path = f"/tournament/matches/{args['match_id']}/{args['policy_version_id']}/policy-logs"
            return _text(await client.get(path))

        case "cogora_get_match_policy_log":
            path = f"/tournament/matches/{args['match_id']}/{args['policy_version_id']}/policy-logs/{args['agent_idx']}"
            return _text(await client.get(path))

        # Episodes
        case "cogora_list_episodes":
            params = {
                "policy_version_id": _str_param(args, "policy_version_id"),
                "tags": _str_param(args, "tags"),
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            return _text(await client.get("/episodes", params))

        case "cogora_get_episode":
            return _text(await client.get(f"/episodes/{args['episode_id']}"))

        case "cogora_query_episodes":
            body = {
                "primary_policy_version_ids": args.get("primary_policy_version_ids"),
                "episode_ids": args.get("episode_ids"),
                "tag_filters": args.get("tag_filters"),
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            body = {k: v for k, v in body.items() if v is not None}
            return _text(await client.post("/stats/episodes/query", json=body))

        # Submissions
        case "cogora_submit_policy":
            body = {"policy_version_id": args["policy_version_id"]}
            return _text(await client.post(f"/tournament/seasons/{args['season_name']}/submissions", json=body))

        # Pools & Configs
        case "cogora_get_pool_config":
            return _text(
                await client.get(f"/tournament/seasons/{args['season_name']}/pools/{args['pool_name']}/config")
            )

        case "cogora_get_config":
            return _text(await client.get(f"/tournament/configs/{args['config_id']}"))

        # Teams
        case "cogora_get_teams":
            params = {
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
                "pool_name": _str_param(args, "pool_name"),
                "eliminated": _bool_param(args, "eliminated"),
                "policy_version_id": _str_param(args, "policy_version_id"),
            }
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/teams", params))

        # Stages & Progress
        case "cogora_get_stages":
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/stages"))

        case "cogora_get_progress":
            return _text(await client.get(f"/tournament/seasons/{args['season_name']}/progress"))

        # Jobs
        case "cogora_list_jobs":
            params = {
                "job_type": _str_param(args, "job_type"),
                "job_id": _str_param(args, "job_id"),
                "policy_version_id": _str_param(args, "policy_version_id"),
                "season_id": _str_param(args, "season_id"),
                "pool_id": _str_param(args, "pool_id"),
                "limit": _int_param(args, "limit"),
                "offset": _int_param(args, "offset"),
            }
            statuses = _list_str_param(args, "statuses")
            if statuses:
                params["statuses"] = statuses
            return _text(await client.get("/jobs", params))

        case "cogora_get_job":
            return _text(await client.get(f"/jobs/{args['job_id']}"))

        case "cogora_get_job_episode_stats":
            return _text(await client.get(f"/jobs/{args['job_id']}/episode-stats"))

        case _:
            return _error(f"Unknown tool: {name}")


def build_server() -> tuple[Server, ObservatoryClient]:
    client = ObservatoryClient()
    app = Server("cogora")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOLS

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        return await handle_tool(client, name, arguments)

    return app, client


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Starting Cogora MCP server")

    app, client = build_server()

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Cogora MCP server running (observatory: %s)", client.server_url)
            await app.run(read_stream, write_stream, app.create_initialization_options())
        await client.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
