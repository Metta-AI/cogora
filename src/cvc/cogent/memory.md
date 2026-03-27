# Memory System

Persistent memory stored in git under `cogents/alpha/`.

## Session Start
1. `git pull --rebase origin main`
2. Check `data/active-session.txt`:
   - If it exists: previous session crashed. Read its session dir,
     write a `summary.md` noting it was interrupted, set status
     to `interrupted` in `activity.log`, clear active-session.txt,
     commit and push.
3. Read `data/recent.md` and `data/todos.md` for context
4. Create `sessions/YYYY-MM-DD-HHMMSS/` with `activity.log` (status: in-progress)
5. Write session dir path to `data/active-session.txt`
6. Commit and push: "session start: YYYY-MM-DD-HHMMSS"

## During Session
- Append to `activity.log` after key actions
- **Commit and push after every meaningful chunk of work** — code changes,
  game results, strategy updates. Don't batch. If the container dies,
  only uncommitted work is lost.

## Session End (MANDATORY)
1. Write `learnings.md` and `summary.md`
2. Set status to `completed` in `activity.log`
3. Update `data/todos.md` — add/remove/reprioritize
4. Prepend entry to `data/recent.md` (date, one-line summary, session link)
5. If `recent.md` exceeds 10 entries, move oldest to `data/archive/YYYY-MM.md`
6. Remove `data/active-session.txt`
7. Commit and push: "session complete: YYYY-MM-DD-HHMMSS — <one-line>"
