# Session Summary — 2026-03-29-131500

## Goal: Push tournament score from 10.05 to 11+

## Key Result
Discovered that the default hotspot_weight=8.0 (avoids scrambled junctions)
was hurting performance. Inverting to negative values makes agents prefer
re-aligning scrambled junctions, which is cheap and effective.

**TV28 (hotspot=-10) averaged 8.91 vs TV18's 7.83 in self-play (+13.8%).**

## Tournament Uploads
Uploaded 10 versions (v392-v401) with various hotspot weights and improvements.
All passed qualifying and entered competition. No completed matches during session
due to slow tournament queue.

## What to Check Next Session
1. Tournament results for v392-v401 (which hotspot value wins?)
2. Does TV28's self-play advantage translate to tournament?
3. New opponents Paz-Bot-9005 and slanky:v112 — study their strategies
4. Consider further orthogonal improvements if TV28 proves effective
