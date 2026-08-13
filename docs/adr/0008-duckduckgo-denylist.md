# 0008. DuckDuckGo plus a yellow-press denylist

## Status

Accepted

## Context

Web sources are used only on Thin retrieval or Time-sensitive questions ([0003](0003-thin-or-fresh-web.md)). The spec requires filtering yellow press.

Alternatives: Tavily or SerpAPI with a domain allowlist (tabloids never queried), or Tavily plus a DeepSeek “is this tabloid?” pass (non-deterministic, extra call).

The product owner chose no search API key.

## Decision

v1 web search is DuckDuckGo. After hits return, drop any URL whose domain is on a Yellow-press denylist checked into the repo. There is no allowlist and no LLM classifier.

## Consequences

- `.env.example` has no Tavily/SerpAPI key. Demos depend on DuckDuckGo staying reachable from Docker.
- The denylist will lag. Unlisted tabloids can appear in answers and must be cited as Web sources when they do.
- Live quotes can fail when DDG HTML/API changes or rate-limits.
- Switching to an allowlist later is a behavior change, not a flag: answers will cite a narrower set of outlets.
