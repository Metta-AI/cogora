---
description: Show your Cogora tournament status — identity, seasons, and leaderboard positions
---

Show the user's Cogora tournament status by calling these MCP tools in sequence:

1. Call `cogora_whoami` to get user identity
2. Call `cogora_list_seasons` to get all seasons
3. For each **in_progress** season, call `cogora_get_leaderboard` with that season's name to get standings

Present results as a concise summary:
- User identity (email, team status)
- Table of active seasons with status
- Leaderboard position in each active season (if the user appears)

If any tool call fails with an auth error, tell the user to run `cogames auth login`.
