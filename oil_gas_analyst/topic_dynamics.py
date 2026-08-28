"""Reddit oil-topic dynamics for the Dashboard ThemeRiver (Arctic Shift + UMAP/HDBSCAN).

Clustering matches semenoffalex/reddit-llm ``cluster_documents`` (precomputed embeddings,
HDBSCAN, UMAP above 15 docs) without importing BERTopic/Torch. Labels are Russian via DeepSeek.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from http.client import IncompleteRead
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import httpx

from oil_gas_analyst.settings import (
    DEEPSEEK_BASE_URL_DEFAULT,
    DEEPSEEK_MODEL,
    require_deepseek_key,
)

_LOG = logging.getLogger(__name__)

_MOSCOW = ZoneInfo("Europe/Moscow")

WINDOW_DAYS = 30
CACHE_TTL_SEC = 6 * 3600
TOPIC_SIM_MAX = 0.58
TOP_TOPIC_COUNT = 6
DRILL_IN_LIMIT = 20
MAX_POSTS_PER_SUB = 800
# r/energy is huge; ``query=oil`` keeps August coverage without paging the whole sub.
MAX_POSTS_BY_SUB = {
    "oil": 1000,
    "crudeoil": 600,
    "peakoil": 400,
    "oilandgas": 600,
    "energy": 400,
    "commodities": 400,
}
SUBREDDIT_QUERY = {
    "energy": "oil",
    "commodities": "oil",
}
OTHER_KEY = "other"
OTHER_LABEL = "Прочее"
OUTLIER_TOPIC_ID = -1

SUBREDDITS = ("oil", "CrudeOil", "peakoil", "oilandgas", "energy", "commodities")
# Already oil-scoped; keywords would drop EIA/SPR and field-work posts.
SUBREDDITS_ALWAYS_KEEP = frozenset({"oil", "crudeoil", "peakoil", "oilandgas"})
ARCTIC_SHIFT_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"
PAGE_LIMIT = 20
# permalink/stickied/removed_by_category are not valid `fields` (HTTP 400).
ARCTIC_FIELDS = (
    "id,created_utc,title,selftext,subreddit,num_comments,author,over_18,url"
)
_HEADERS = {
    "User-Agent": "oil-gas-analyst/0.1 (topic dynamics; compatible with reddit-llm/0.1)",
    "Accept": "application/json",
}

KEYWORD_PATTERN = re.compile(
    r"(?i)\b(?:oil|crude|brent|wti|opec|urals|gasoline|diesel|tanker|"
    r"refinery|petroleum|barrel|нефть|брент|уралс|опек)\w*"
)
# One kept cluster per storyline so the river is not six Hormuz variants.
_THEME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("daily_price", re.compile(r"daily oil price|price opinions", re.I)),
    ("hormuz", re.compile(r"hormuz|strait of|kharg|blockade", re.I)),
    ("iran", re.compile(r"\biran\b|tehran", re.I)),
    ("eia_spr", re.compile(r"\beia\b|\bspr\b|inventory|strategic reserve", re.I)),
    ("opec", re.compile(r"\bopec\b", re.I)),
    ("china", re.compile(r"\bchina\b|chinese", re.I)),
    ("tanker", re.compile(r"\btanker\b|vessel.{0,20}sunk", re.I)),
    ("jobs", re.compile(r"wireline|coiled tubing|odessa|midland|hiring", re.I)),
)
_THEME_LABELS_RU = {
    "daily_price": "Дневные цены",
    "hormuz": "Ормузский пролив",
    "iran": "Иран",
    "eia_spr": "Запасы EIA / SPR",
    "opec": "ОПЕК+",
    "china": "Китайский спрос",
    "tanker": "Танкеры",
    "jobs": "Вакансии в добыче",
}
_GENERIC_TOPIC_LABEL = re.compile(r"^Тема\s+\d+$")
_OPENROUTER_LABEL_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

TOPIC_CHART_EMPTY_COPY = (
    "Нет Reddit-тем за 30 дней. Не выдумываем нарративы — "
    "попробуйте обновить позже."
)
TOPIC_ARCHIVE_UNAVAILABLE_COPY = (
    "Архив Reddit не ответил. Не выдумываем темы — нажмите «Обновить темы»."
)
TOPIC_CLUSTER_UNAVAILABLE_COPY = (
    "Посты Reddit скачались, но кластеризация не удалась. "
    "Не выдумываем темы — нажмите «Обновить темы»."
)
TOPIC_REFRESH_COPY = "Обновляем темы Reddit…"
TOPIC_PANEL_TITLE = "Темы Reddit · нефть, 30 дней"

ClusterFn = Callable[[list[str], list[list[float]]], "ClusterResult"]
EmbedFn = Callable[[list[str]], list[list[float]]]
LabelFn = Callable[[dict[int, list[str]]], dict[int, str]]
PageFn = Callable[[dict[str, Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class ClusterResult:
    topic_ids: list[int]
    probabilities: list[float]
    representative_docs: dict[int, list[str]]


@dataclass(frozen=True)
class RedditOilPost:
    id: str
    subreddit: str
    title: str
    body: str
    url: str
    created_utc: float
    num_comments: int
    chunk_text: str
    day_msk: str


def _topics_cache_dir(cache_dir: Path | str | None = None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    return Path(os.environ.get("TOPICS_CACHE_PATH") or "data/topics_cache")


def _topics_cache_path(cache_dir: Path | str | None = None) -> Path:
    return _topics_cache_dir(cache_dir) / "topic_dynamics.json"


def _today_moscow() -> date:
    return datetime.now(_MOSCOW).date()


def window_dates(*, today: date | None = None) -> tuple[date, date]:
    end = today or _today_moscow()
    start = end - timedelta(days=WINDOW_DAYS - 1)
    return start, end


def msk_day_iso(created_utc: float) -> str:
    return (
        datetime.fromtimestamp(created_utc, tz=timezone.utc)
        .astimezone(_MOSCOW)
        .date()
        .isoformat()
    )


def matches_oil_keywords(text: str) -> bool:
    return bool(KEYWORD_PATTERN.search(text or ""))


def is_dropped_reddit_post(raw: dict[str, Any]) -> bool:
    if raw.get("over_18") or raw.get("stickied"):
        return True
    title = str(raw.get("title") or "").strip()
    if title in {"[deleted]", "[removed]"}:
        return True
    author = str(raw.get("author") or "")
    if author in {"[deleted]", "[removed]"}:
        return True
    body = str(raw.get("selftext") or "").strip()
    if body in {"[removed]", "[deleted]"}:
        return True
    if raw.get("removed_by_category"):
        return True
    return False


def reddit_permalink(raw: dict[str, Any]) -> str:
    permalink = str(raw.get("permalink") or "").strip()
    if permalink:
        if permalink.startswith("http"):
            return permalink
        return "https://www.reddit.com" + permalink
    pid = str(raw.get("id") or "").removeprefix("t3_")
    sub = str(raw.get("subreddit") or "")
    if pid and sub:
        return f"https://www.reddit.com/r/{sub}/comments/{pid}/"
    return str(raw.get("url") or "")


def reddit_post_to_record(raw: dict[str, Any]) -> RedditOilPost | None:
    if is_dropped_reddit_post(raw):
        return None
    title = str(raw.get("title") or "").strip()
    body = str(raw.get("selftext") or "").strip()
    chunk = f"{title}\n\n{body}" if body else title
    sub = str(raw.get("subreddit") or "")
    if sub.casefold() not in SUBREDDITS_ALWAYS_KEEP and not matches_oil_keywords(chunk):
        return None
    created = raw.get("created_utc") or 0
    try:
        created_utc = float(created)
    except (TypeError, ValueError):
        return None
    pid = str(raw.get("id") or "").removeprefix("t3_")
    if not pid:
        return None
    return RedditOilPost(
        id=f"t3_{pid}",
        subreddit=str(raw.get("subreddit") or ""),
        title=title,
        body=body,
        url=reddit_permalink(raw),
        created_utc=created_utc,
        num_comments=int(raw.get("num_comments") or 0),
        chunk_text=chunk,
        day_msk=msk_day_iso(created_utc),
    )


def archive_error_copy(exc: BaseException) -> str:
    """User-facing Arctic Shift failure; never dump urllib internals on the Demo."""
    return TOPIC_ARCHIVE_UNAVAILABLE_COPY


def _http_get_json(url: str, params: dict[str, Any], *, timeout: float = 120.0) -> dict[str, Any]:
    """httpx, same client reddit-llm uses; urllib stalls on Arctic Shift chunked bodies."""
    query = dict(params)
    query.setdefault("fields", ARCTIC_FIELDS)
    with httpx.Client(headers=_HEADERS, timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, params=query)
    if resp.status_code in {422, 429}:
        raise HTTPError(url, resp.status_code, str(resp.status_code), hdrs=None, fp=None)
    resp.raise_for_status()
    payload = resp.json()
    if payload is None:
        raise URLError("empty Arctic Shift body")
    if isinstance(payload, dict):
        return payload
    return {"data": payload}


def _arctic_shift_page(
    params: dict[str, Any],
    *,
    get_json: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    loader = get_json or _http_get_json
    last_exc: Exception | None = None
    retryable = (
        IncompleteRead,
        URLError,
        TimeoutError,
        OSError,
        ConnectionError,
        httpx.TimeoutException,
        httpx.TransportError,
    )
    for attempt in range(4):
        try:
            payload = loader(ARCTIC_SHIFT_URL, params)
            data = payload.get("data") if isinstance(payload, dict) else payload
            return list(data or [])
        except HTTPError as exc:
            last_exc = exc
            if exc.code in {422, 429} and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except retryable as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    if last_exc:
        raise last_exc
    return []


def _max_posts_for(sub: str) -> int:
    return int(MAX_POSTS_BY_SUB.get(sub.casefold(), MAX_POSTS_PER_SUB))


def fetch_subreddit_since(
    sub: str,
    since_ts: int,
    *,
    get_page: PageFn | None = None,
    throttle: float = 0.35,
    max_posts: int | None = None,
) -> list[dict[str, Any]]:
    """Newest-first Arctic Shift pages until ``created_utc`` falls before ``since_ts``."""

    page_fn = get_page or _arctic_shift_page
    cap = _max_posts_for(sub) if max_posts is None else max_posts
    query = SUBREDDIT_QUERY.get(sub.casefold())
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    before_ts: int | None = None
    while len(posts) < cap:
        params: dict[str, Any] = {
            "subreddit": sub,
            "limit": min(PAGE_LIMIT, cap - len(posts)),
            "fields": ARCTIC_FIELDS,
        }
        if query:
            params["query"] = query
        if before_ts is not None:
            params["before"] = before_ts
        data = page_fn(params)
        if not data:
            break
        added_any = False
        reached_floor = False
        for raw in data:
            pid = str(raw.get("id") or "")
            if not pid or pid in seen:
                continue
            try:
                created = float(raw.get("created_utc") or 0)
            except (TypeError, ValueError):
                continue
            if created < since_ts:
                reached_floor = True
                continue
            seen.add(pid)
            posts.append(raw)
            added_any = True
        if reached_floor or not added_any:
            break
        tail = data[-1].get("created_utc")
        if tail is None:
            break
        before_ts = int(float(tail))
        if throttle:
            time.sleep(throttle)
    return posts


def fetch_oil_reddit_posts(
    *,
    today: date | None = None,
    get_page: PageFn | None = None,
    throttle: float = 0.35,
    subreddits: tuple[str, ...] = SUBREDDITS,
) -> list[RedditOilPost]:
    start, _end = window_dates(today=today)
    since_ts = int(datetime(start.year, start.month, start.day, tzinfo=_MOSCOW).timestamp())
    collected: dict[str, RedditOilPost] = {}
    for i, sub in enumerate(subreddits):
        if i and throttle:
            time.sleep(throttle)
        for raw in fetch_subreddit_since(
            sub,
            since_ts,
            get_page=get_page,
            throttle=throttle,
        ):
            record = reddit_post_to_record(raw)
            if record is None:
                continue
            if record.day_msk < start.isoformat():
                continue
            collected[record.id] = record
    return list(collected.values())


def _hdbscan_min_size(n_docs: int) -> int:
    """Tiny corpora keep size 2; a month of posts needs larger clusters than micro-topics."""
    if n_docs < 24:
        return 2
    return max(10, min(n_docs // 50, 25))


def _assign_outliers_to_nearest(topic_ids: list[int], space) -> list[int]:
    """Attach leftover points only when they sit inside a cluster's radius."""
    import numpy as np

    ids = np.asarray(topic_ids, dtype=int)
    clustered = ids >= 0
    if not clustered.any() or clustered.all():
        return topic_ids
    centroid_ids: list[int] = []
    centroids: list = []
    radii: list[float] = []
    for tid in sorted(set(ids[clustered].tolist())):
        pts = space[ids == tid]
        center = pts.mean(axis=0)
        centroid_ids.append(tid)
        centroids.append(center)
        radii.append(float(np.median(np.linalg.norm(pts - center, axis=1))) + 1e-6)
    mat = np.stack(centroids)
    rad = np.asarray(radii, dtype=np.float64)
    for i in np.where(~clustered)[0]:
        dist = np.linalg.norm(mat - space[i], axis=1)
        nearest = int(dist.argmin())
        if dist[nearest] <= 2.0 * rad[nearest]:
            ids[i] = centroid_ids[nearest]
    return [int(v) for v in ids]


def _cluster_residual_outliers(topic_ids: list[int], space) -> list[int]:
    """Second HDBSCAN pass on leftovers so EIA/jobs/China can become real topics."""
    import numpy as np
    from hdbscan import HDBSCAN  # type: ignore[import-untyped]

    ids = np.asarray(topic_ids, dtype=int)
    residual = np.where(ids < 0)[0]
    if residual.size < 24:
        return topic_ids
    sub_n = int(residual.size)
    sub_size = max(8, min(sub_n // 40, 15))
    sub_labels = HDBSCAN(
        min_cluster_size=sub_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    ).fit_predict(space[residual])
    clustered = ids[ids >= 0]
    offset = int(clustered.max() + 1) if clustered.size else 0
    for local, doc_i in enumerate(residual):
        sub_id = int(sub_labels[local])
        if sub_id >= 0:
            ids[doc_i] = offset + sub_id
    return [int(v) for v in ids]


def cluster_theme(texts: list[str]) -> str | None:
    blob = " ".join(texts)
    for name, pattern in _THEME_PATTERNS:
        if pattern.search(blob):
            return name
    return None


def cluster_documents(
    docs: list[str],
    embeddings: list[list[float]],
    *,
    min_cluster_size: int | None = None,
) -> ClusterResult:
    """UMAP+HDBSCAN on precomputed vectors (reddit-llm ``cluster_documents`` without BERTopic)."""

    import numpy as np
    from hdbscan import HDBSCAN  # type: ignore[import-untyped]

    if not docs:
        return ClusterResult(topic_ids=[], probabilities=[], representative_docs={})
    if len(docs) < 2:
        return ClusterResult(
            topic_ids=[OUTLIER_TOPIC_ID] * len(docs),
            probabilities=[0.0] * len(docs),
            representative_docs={OUTLIER_TOPIC_ID: list(docs)},
        )

    emb = np.asarray(embeddings, dtype=np.float32)
    n_docs = len(docs)
    size = (
        min(min_cluster_size, max(2, n_docs))
        if min_cluster_size is not None
        else _hdbscan_min_size(n_docs)
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    space = emb
    if n_docs >= 15:
        from umap import UMAP  # type: ignore[import-untyped]

        space = UMAP(
            n_neighbors=min(30, n_docs - 1),
            n_components=5,
            min_dist=0.0,
            metric="cosine",
            random_state=42,
        ).fit_transform(emb)

    labels = hdbscan_model.fit_predict(space)
    if float(np.mean(labels == OUTLIER_TOPIC_ID)) > 0.5 and size > 8:
        hdbscan_model = HDBSCAN(
            min_cluster_size=max(8, size // 2),
            min_samples=1,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )
        labels = hdbscan_model.fit_predict(space)
    topic_ids = _assign_outliers_to_nearest([int(t) for t in labels], space)
    topic_ids = _cluster_residual_outliers(topic_ids, space)
    raw_probs = getattr(hdbscan_model, "probabilities_", None)
    if raw_probs is None:
        raw_probs = [0.0] * n_docs
    probabilities = [
        0.0 if tid == OUTLIER_TOPIC_ID else float(p)
        for tid, p in zip(topic_ids, raw_probs)
    ]
    return ClusterResult(
        topic_ids=topic_ids,
        probabilities=probabilities,
        representative_docs=_representative_docs(docs, topic_ids, probabilities),
    )


def _l2_normalize(vec) -> "list[float]":
    import numpy as np

    arr = np.asarray(vec, dtype=np.float64).reshape(-1)
    n = float(np.linalg.norm(arr))
    if n <= 0:
        return arr.tolist()
    return (arr / n).tolist()


def _cluster_mean_vectors(
    groups: dict[int, list[int]],
    embeddings: list[list[float]],
) -> dict[int, list[float]]:
    import numpy as np

    emb = np.asarray(embeddings, dtype=np.float64)
    out: dict[int, list[float]] = {}
    for tid, idxs in groups.items():
        if tid == OUTLIER_TOPIC_ID or not idxs:
            continue
        out[tid] = _l2_normalize(emb[idxs].mean(axis=0))
    return out


def select_diverse_topic_ids(
    ranked_ids: list[int],
    vectors: dict[int, list[float]],
    *,
    k: int = TOP_TOPIC_COUNT,
    max_sim: float = TOPIC_SIM_MAX,
    themes: dict[int, str | None] | None = None,
) -> list[int]:
    """Keep loud clusters first, skip the same storyline (Hormuz/Iran clones)."""
    import numpy as np

    keep: list[int] = []
    used_themes: set[str] = set()
    theme_map = themes or {}
    usable = [tid for tid in ranked_ids if tid in vectors] or list(ranked_ids)
    identical = False
    if len(usable) >= 2 and all(tid in vectors for tid in usable):
        first = np.asarray(vectors[usable[0]], dtype=np.float64)
        sims = [
            abs(float(np.dot(first, np.asarray(vectors[tid], dtype=np.float64))))
            for tid in usable[1:]
        ]
        identical = bool(sims) and min(sims) > 0.99

    def _too_close(tid: int, limit: float) -> bool:
        if identical or tid not in vectors:
            return False
        v = np.asarray(vectors[tid], dtype=np.float64)
        return any(
            float(np.dot(v, np.asarray(vectors[other], dtype=np.float64))) >= limit
            for other in keep
            if other in vectors
        )

    def _try_add(tid: int, limit: float) -> None:
        if len(keep) >= k or tid in keep:
            return
        theme = theme_map.get(tid)
        if theme and theme in used_themes:
            return
        if _too_close(tid, limit):
            return
        keep.append(tid)
        if theme:
            used_themes.add(theme)

    for tid in usable:
        _try_add(tid, max_sim)
    if len(keep) < k:
        for tid in usable:
            _try_add(tid, min(0.85, max_sim + 0.2))
    return keep


def _representative_docs(
    docs: list[str],
    topic_ids: list[int],
    probabilities: list[float],
    *,
    k: int = 3,
) -> dict[int, list[str]]:
    ranked: dict[int, list[tuple[float, str]]] = defaultdict(list)
    for doc, tid, prob in zip(docs, topic_ids, probabilities, strict=True):
        ranked[tid].append((prob, doc))
    out: dict[int, list[str]] = {}
    for tid, pairs in ranked.items():
        pairs.sort(key=lambda item: item[0], reverse=True)
        out[tid] = [doc for _, doc in pairs[:k]]
    return out


def parse_labels_json(content: str) -> dict[int, str]:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("labeler output must be a JSON object")
    raw = data.get("labels", data)
    if not isinstance(raw, dict):
        raise ValueError("labeler JSON must contain a labels object")
    return {int(key): str(value).strip() for key, value in raw.items() if str(value).strip()}


def _chat_headers(base_url: str, api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = os.environ.get(
            "OPENROUTER_HTTP_REFERER",
            "https://github.com/semenoffalex/agent_oil_analyst",
        )
        headers["X-Title"] = os.environ.get("OPENROUTER_APP_TITLE", "Oil Gas Analyst")
    return headers


def _chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
) -> str:
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    body = json.dumps(
        {"model": model, "messages": messages, "temperature": 0},
        ensure_ascii=False,
    ).encode("utf-8")
    req = Request(
        f"{base}/chat/completions",
        data=body,
        headers=_chat_headers(base, api_key),
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"chat HTTP {exc.code} {exc.reason}: {detail}") from exc
    message = payload["choices"][0]["message"]
    content = str(message.get("content") or message.get("reasoning_content") or "")
    if not content.strip():
        raise RuntimeError("chat completion returned empty content")
    return content


def _label_messages(to_label: dict[int, list[str]]) -> list[dict[str, str]]:
    payload = []
    for tid, docs in sorted(to_label.items()):
        joined = "\n---\n".join(docs[:3])
        payload.append(f"topic_id={tid}:\n{joined}")
    return [
        {
            "role": "system",
            "content": (
                "Ты подписываешь кластеры Reddit-постов про нефть. "
                "Короткие русские лейблы (2–5 слов), без кавычек. "
                "Каждый лейбл про разный сюжет: не повторяй Ормуз/Иран/цены разными словами. "
                'Верни только JSON: {"labels": {"<topic_id>": "<лейбл>"}}.'
            ),
        },
        {"role": "user", "content": "\n\n".join(payload)},
    ]


def _headline_label(docs: list[str]) -> str:
    for doc in docs:
        line = re.sub(r"\s+", " ", (doc or "").strip().split("\n")[0]).strip()
        if len(line) < 8:
            continue
        if len(line) > 52:
            clipped = line[:49].rsplit(" ", 1)[0]
            line = (clipped or line[:49]) + "…"
        return line
    return "Нефтяные обсуждения"


def _heuristic_topic_labels(to_label: dict[int, list[str]]) -> dict[int, str]:
    used: set[str] = set()
    out: dict[int, str] = {}
    for tid, docs in to_label.items():
        theme = cluster_theme(docs)
        label = _THEME_LABELS_RU.get(theme or "", "")
        if not label or label in used:
            label = _headline_label(docs)
        if label in used:
            label = f"{label} ({tid})"
        used.add(label)
        out[tid] = label
    return out


def _is_generic_topic_label(label: object) -> bool:
    return bool(_GENERIC_TOPIC_LABEL.match(str(label or "").strip()))


def _fill_topic_labels(
    to_label: dict[int, list[str]], parsed: dict[int, str]
) -> dict[int, str]:
    heuristics = _heuristic_topic_labels(to_label)
    out = dict(parsed)
    for tid in to_label:
        current = str(out.get(tid) or "").strip()
        if not current or _is_generic_topic_label(current):
            out[tid] = heuristics[tid]
    return out


def _label_with_llm(
    to_label: dict[int, list[str]],
    *,
    chat_fn: Callable[..., str],
    model: str,
    base_url: str,
    api_key: str,
) -> dict[int, str]:
    raw = chat_fn(
        _label_messages(to_label),
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    return parse_labels_json(raw)


def _openrouter_label_attempt() -> tuple[str, str, str] | None:
    key = (
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("EMBEDDING_API_KEY", "").strip()
    )
    if not key:
        return None
    model = (
        os.environ.get("TOPIC_LABEL_MODEL", "").strip()
        or os.environ.get("EVAL_CHAT_MODEL", "").strip()
        or _OPENROUTER_LABEL_MODEL
    )
    if "::" in model:
        model = model.split("::", 1)[1]
    base = (
        os.environ.get("OPENROUTER_BASE_URL", "").strip()
        or "https://openrouter.ai/api/v1"
    )
    return model, base, key


def label_topics(
    representative_docs: dict[int, list[str]],
    *,
    chat_fn: Callable[..., str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[int, str]:
    labels: dict[int, str] = {}
    if OUTLIER_TOPIC_ID in representative_docs:
        labels[OUTLIER_TOPIC_ID] = OTHER_LABEL
    to_label = {
        tid: docs
        for tid, docs in representative_docs.items()
        if tid != OUTLIER_TOPIC_ID
    }
    if not to_label:
        return labels

    parsed: dict[int, str] = {}
    completer = chat_fn or _chat_completion
    attempts: list[tuple[str, str, str]] = []
    if chat_fn is not None:
        attempts.append(
            (
                model or os.environ.get("DEEPSEEK_MODEL", "").strip() or DEEPSEEK_MODEL,
                base_url
                or os.environ.get("DEEPSEEK_BASE_URL", "").strip()
                or DEEPSEEK_BASE_URL_DEFAULT,
                api_key or "",
            )
        )
    else:
        try:
            attempts.append(
                (
                    model or os.environ.get("DEEPSEEK_MODEL", "").strip() or DEEPSEEK_MODEL,
                    base_url
                    or os.environ.get("DEEPSEEK_BASE_URL", "").strip()
                    or os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").strip()
                    or DEEPSEEK_BASE_URL_DEFAULT,
                    api_key if api_key is not None else require_deepseek_key(),
                )
            )
        except Exception as exc:
            _LOG.warning("DeepSeek key unavailable for topic labels: %s", exc)
        fallback = _openrouter_label_attempt()
        if fallback:
            attempts.append(fallback)

    for attempt_model, attempt_base, attempt_key in attempts:
        try:
            parsed = _label_with_llm(
                to_label,
                chat_fn=completer,
                model=attempt_model,
                base_url=attempt_base,
                api_key=attempt_key,
            )
            if parsed:
                break
        except Exception as exc:
            _LOG.warning("topic labeler failed (%s): %s", attempt_model, exc)

    labels.update(_fill_topic_labels(to_label, parsed))
    return labels


def _tfidf_embeddings(docs: list[str]) -> list[list[float]]:
    """Dense bag-of-words vectors when the remote embedding API is blocked."""
    import numpy as np
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    matrix = TfidfVectorizer(
        max_features=2048,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.6,
    ).fit_transform(docs)
    n_components = int(min(32, matrix.shape[0] - 1, matrix.shape[1] - 1))
    if n_components < 2:
        return [[float(i), 0.0] for i in range(len(docs))]
    dense = TruncatedSVD(n_components=n_components, random_state=42).fit_transform(matrix)
    return np.asarray(dense, dtype=np.float32).tolist()


def _embed_docs(docs: list[str]) -> list[list[float]]:
    from oil_gas_analyst.retrieve import make_embedding_function

    try:
        return make_embedding_function()(docs)
    except Exception:
        return _tfidf_embeddings(docs)


def _dynamics_label(daily: dict[str, int], start: date, end: date) -> str:
    days = (end - start).days + 1
    third = max(1, days // 3)
    first_end = start + timedelta(days=third - 1)
    last_start = end - timedelta(days=third - 1)
    first = sum(
        comments
        for iso, comments in daily.items()
        if start.isoformat() <= iso <= first_end.isoformat()
    )
    last = sum(
        comments
        for iso, comments in daily.items()
        if last_start.isoformat() <= iso <= end.isoformat()
    )
    if first <= 0 and last <= 0:
        return "без явного тренда"
    if first <= 0:
        return "выросла"
    if last > first * 1.15:
        return "выросла"
    if last < first * 0.85:
        return "упала"
    return "без явного тренда"


def _empty_payload(
    *,
    start: date,
    end: date,
    unavailable_reason: str | None,
    fetched_at: str | None = None,
) -> dict:
    return {
        "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "unavailable_reason": unavailable_reason,
        "topics": [],
        "series": [],
        "posts": [],
    }


def build_topic_payload(
    posts: list[RedditOilPost],
    *,
    today: date | None = None,
    embed_fn: EmbedFn | None = None,
    cluster_fn: ClusterFn | None = None,
    label_fn: LabelFn | None = None,
) -> dict:
    start, end = window_dates(today=today)
    in_window = [p for p in posts if start.isoformat() <= p.day_msk <= end.isoformat()]
    if len(in_window) < 2:
        return _empty_payload(start=start, end=end, unavailable_reason=None)

    docs = [p.chunk_text for p in in_window]
    embeddings = (embed_fn or _embed_docs)(docs)
    cluster = (cluster_fn or cluster_documents)(docs, embeddings)

    groups: dict[int, list[int]] = defaultdict(list)
    for i, tid in enumerate(cluster.topic_ids):
        groups[tid].append(i)

    ranked_ids = sorted(
        (tid for tid in groups if tid != OUTLIER_TOPIC_ID),
        key=lambda tid: (
            sum(in_window[i].num_comments for i in groups[tid]),
            len(groups[tid]),
        ),
        reverse=True,
    )
    vectors = _cluster_mean_vectors(groups, embeddings)
    themes = {
        tid: cluster_theme([in_window[i].chunk_text for i in groups[tid]])
        for tid in ranked_ids
    }
    keep_ids = select_diverse_topic_ids(
        ranked_ids, vectors, k=TOP_TOPIC_COUNT, themes=themes
    )
    keep = set(keep_ids)
    reps = {
        tid: docs_for_tid
        for tid, docs_for_tid in cluster.representative_docs.items()
        if tid in keep or tid == OUTLIER_TOPIC_ID
    }
    labels = (label_fn or label_topics)(reps)
    display_key: dict[int, str] = {}
    topic_meta: dict[str, dict] = {}
    for tid in ranked_ids:
        if tid in keep:
            key = str(tid)
            display_key[tid] = key
            topic_meta[key] = {
                "key": key,
                "label": labels.get(tid) or _headline_label(reps.get(tid) or []),
                "raw_id": tid,
            }
        else:
            display_key[tid] = OTHER_KEY
    display_key[OUTLIER_TOPIC_ID] = OTHER_KEY
    if any(display_key.get(tid) == OTHER_KEY for tid in groups):
        topic_meta[OTHER_KEY] = {
            "key": OTHER_KEY,
            "label": OTHER_LABEL,
            "raw_id": OUTLIER_TOPIC_ID,
        }

    post_rows: list[dict] = []
    daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i, post in enumerate(in_window):
        tid = cluster.topic_ids[i]
        key = display_key.get(tid, OTHER_KEY)
        meta = topic_meta.get(key) or topic_meta[OTHER_KEY]
        daily[key][post.day_msk] += max(0, post.num_comments)
        post_rows.append(
            {
                "id": post.id,
                "topic_key": key,
                "label": meta["label"],
                "title": post.title,
                "subreddit": post.subreddit,
                "url": post.url,
                "num_comments": post.num_comments,
                "day_msk": post.day_msk,
            }
        )

    days = [
        (start + timedelta(days=offset)).isoformat()
        for offset in range((end - start).days + 1)
    ]
    ordered_keys = [
        key
        for key, _ in sorted(
            (
                (key, sum(day_map.values()))
                for key, day_map in daily.items()
                if key != OTHER_KEY
            ),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    if OTHER_KEY in topic_meta:
        ordered_keys.append(OTHER_KEY)

    topics_out: list[dict] = []
    series: list[dict] = []
    for key in ordered_keys:
        meta = topic_meta[key]
        day_map = daily.get(key) or {}
        total_comments = sum(day_map.values())
        size = sum(1 for row in post_rows if row["topic_key"] == key)
        headlines = [
            row["title"]
            for row in sorted(
                (r for r in post_rows if r["topic_key"] == key),
                key=lambda r: r["num_comments"],
                reverse=True,
            )[:3]
        ]
        topics_out.append(
            {
                "key": key,
                "label": meta["label"],
                "total_comments": total_comments,
                "size": size,
                "dynamics": _dynamics_label(dict(day_map), start, end),
                "headlines": headlines,
            }
        )
        for iso in days:
            series.append(
                {
                    "date": iso,
                    "topic_key": key,
                    "label": meta["label"],
                    "comments": int(day_map.get(iso) or 0),
                }
            )

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "unavailable_reason": None,
        "topics": topics_out,
        "series": series,
        "posts": post_rows,
    }


def save_topic_payload_cache(payload: dict, *, cache_dir: Path | str | None = None) -> None:
    if payload.get("unavailable_reason") or not payload.get("topics"):
        return
    path = _topics_cache_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cached_topic_payload(*, cache_dir: Path | str | None = None) -> dict | None:
    path = _topics_cache_path(cache_dir)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def topic_payload_is_fresh(payload: dict | None, *, now: datetime | None = None) -> bool:
    if not payload or payload.get("unavailable_reason") or not payload.get("topics"):
        return False
    raw = payload.get("fetched_at")
    if not raw:
        return False
    try:
        fetched = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (stamp - fetched).total_seconds() < CACHE_TTL_SEC


def topic_payload_needs_relabel(payload: dict | None) -> bool:
    if not payload:
        return False
    named = [row for row in (payload.get("topics") or []) if row.get("key") != OTHER_KEY]
    return bool(named) and any(_is_generic_topic_label(row.get("label")) for row in named)


def relabel_topic_payload(payload: dict, *, label_fn: LabelFn | None = None) -> dict:
    """Replace generic «Тема N» labels on an existing cache payload."""
    reps: dict[int, list[str]] = {}
    for topic in payload.get("topics") or []:
        if topic.get("key") == OTHER_KEY:
            continue
        try:
            tid = int(topic.get("raw_id", topic.get("key")))
        except (TypeError, ValueError):
            continue
        posts = [
            row
            for row in (payload.get("posts") or [])
            if row.get("topic_key") == topic.get("key")
        ]
        posts.sort(key=lambda row: int(row.get("num_comments") or 0), reverse=True)
        titles = [str(row.get("title") or "").strip() for row in posts[:3]]
        reps[tid] = [title for title in titles if title] or [str(topic.get("label") or tid)]
    if not reps:
        return payload
    labels = (label_fn or label_topics)(reps)
    by_key: dict[str, str] = {}
    for topic in payload.get("topics") or []:
        if topic.get("key") == OTHER_KEY:
            continue
        try:
            tid = int(topic.get("raw_id", topic.get("key")))
        except (TypeError, ValueError):
            continue
        label = labels.get(tid)
        if not label:
            continue
        topic["label"] = label
        by_key[str(topic["key"])] = label
    for row in payload.get("series") or []:
        key = str(row.get("topic_key") or "")
        if key in by_key:
            row["label"] = by_key[key]
    for row in payload.get("posts") or []:
        key = str(row.get("topic_key") or "")
        if key in by_key:
            row["label"] = by_key[key]
    return payload


def refresh_topic_dynamics_payload(
    *,
    cache_dir: Path | str | None = None,
    force: bool = False,
    today: date | None = None,
    get_page: PageFn | None = None,
    embed_fn: EmbedFn | None = None,
    cluster_fn: ClusterFn | None = None,
    label_fn: LabelFn | None = None,
    throttle: float = 0.35,
) -> dict:
    cached = load_cached_topic_payload(cache_dir=cache_dir)
    if not force and topic_payload_is_fresh(cached) and cached is not None:
        if topic_payload_needs_relabel(cached):
            relabeled = relabel_topic_payload(cached, label_fn=label_fn)
            save_topic_payload_cache(relabeled, cache_dir=cache_dir)
            return relabeled
        return cached

    start, end = window_dates(today=today)
    try:
        posts = fetch_oil_reddit_posts(
            today=today,
            get_page=get_page,
            throttle=0.0 if get_page is not None else throttle,
        )
    except Exception as exc:
        if cached and (cached.get("topics") or cached.get("series")):
            return cached
        return _empty_payload(start=start, end=end, unavailable_reason=archive_error_copy(exc))

    try:
        payload = build_topic_payload(
            posts,
            today=today,
            embed_fn=embed_fn,
            cluster_fn=cluster_fn,
            label_fn=label_fn,
        )
        save_topic_payload_cache(payload, cache_dir=cache_dir)
        return payload
    except Exception:
        if cached and (cached.get("topics") or cached.get("series")):
            return cached
        return _empty_payload(start=start, end=end, unavailable_reason=TOPIC_CLUSTER_UNAVAILABLE_COPY)


def topic_chart_dataframe(payload: dict):
    import pandas as pd

    rows = payload.get("series") or []
    if not rows:
        return None
    named = [row for row in rows if row.get("topic_key") != OTHER_KEY]
    frame = pd.DataFrame(named or rows)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


_NAMED_TOPIC_COLORS = (
    "#5B8FF9",
    "#F6BD16",
    "#E8684A",
    "#5AD8A6",
    "#9270CA",
    "#FF9D4D",
)
_OTHER_TOPIC_COLOR = "#64748B"

TOPIC_CHART_RIVER = "Река"
TOPIC_CHART_RIDGES = "По осям"


def _topic_color_scale(frame) -> tuple[list[str], list[str]]:
    labels = list(dict.fromkeys(frame.sort_values("date")["label"].tolist()))
    named = [name for name in labels if name != OTHER_LABEL]
    domain = named + ([OTHER_LABEL] if OTHER_LABEL in labels else [])
    palette = [_NAMED_TOPIC_COLORS[i % len(_NAMED_TOPIC_COLORS)] for i in range(len(named))]
    if OTHER_LABEL in domain:
        palette.append(_OTHER_TOPIC_COLOR)
    return domain, palette


def _topic_tooltip():
    import altair as alt

    return [
        alt.Tooltip("date:T", title="Дата"),
        alt.Tooltip("label:N", title="Тема"),
        alt.Tooltip("comments:Q", title="Комментарии"),
    ]


def topic_streamgraph_altair(frame, *, height: int = 280):
    """Classic ThemeRiver: centered stack, volume = comments."""
    import altair as alt

    domain, palette = _topic_color_scale(frame)
    return (
        alt.Chart(frame)
        .mark_area(interpolate="monotone")
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("comments:Q", title=None, stack="center", axis=None),
            color=alt.Color(
                "label:N",
                title=None,
                scale=alt.Scale(domain=domain, range=palette),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=_topic_tooltip(),
        )
        .properties(height=height)
    )


def _ordered_topic_labels(frame, label_order: list[str] | None) -> tuple[list[str], list[str]]:
    domain, palette = _topic_color_scale(frame)
    if not label_order:
        return domain, palette
    present = set(domain)
    ordered = [name for name in label_order if name in present]
    domain = ordered + [name for name in domain if name not in ordered]
    named = [name for name in domain if name != OTHER_LABEL]
    palette = [_NAMED_TOPIC_COLORS[i % len(_NAMED_TOPIC_COLORS)] for i in range(len(named))]
    if OTHER_LABEL in domain:
        palette.append(_OTHER_TOPIC_COLOR)
    return domain, palette


def topic_ridgeline_charts(frame, *, row_height: int = 78, label_order: list[str] | None = None):
    """One unit area chart per topic. Width is ``container`` so Streamlit can stretch."""
    import altair as alt

    domain, palette = _ordered_topic_labels(frame, label_order)
    charts: list[tuple[str, object]] = []
    for index, name in enumerate(domain):
        color = palette[index % len(palette)] if palette else _NAMED_TOPIC_COLORS[0]
        charts.append(
            (
                name,
                alt.Chart(frame.loc[frame["label"] == name])
                .mark_area(
                    interpolate="monotone",
                    color=color,
                    opacity=0.9,
                    line={"color": color, "strokeWidth": 1.5},
                )
                .encode(
                    x=alt.X(
                        "date:T",
                        title=None,
                        axis=alt.Axis(
                            format="%d.%m",
                            grid=True,
                            tickCount=6,
                            labelFontSize=11,
                            labelColor="#94A3B8",
                            gridColor="#334155",
                            domainColor="#475569",
                            tickColor="#475569",
                        ),
                    ),
                    y=alt.Y(
                        "comments:Q",
                        title=None,
                        stack=None,
                        axis=None,
                        scale=alt.Scale(zero=True, nice=True),
                    ),
                    tooltip=_topic_tooltip(),
                )
                .properties(width="container", height=row_height),
            )
        )
    return charts


def topic_ridgeline_altair(frame, *, row_height: int = 52, label_order: list[str] | None = None):
    """Stacked small multiples (tests / non-Streamlit). Dashboard uses unit charts."""
    import altair as alt

    plots = [chart for _, chart in topic_ridgeline_charts(frame, row_height=row_height, label_order=label_order)]
    if not plots:
        return alt.Chart()
    return alt.vconcat(*plots, spacing=8).resolve_scale(y="independent")


def posts_for_topic(payload: dict, topic_key: str, *, limit: int = DRILL_IN_LIMIT) -> list[dict]:
    rows = [row for row in (payload.get("posts") or []) if row.get("topic_key") == topic_key]
    rows.sort(key=lambda row: int(row.get("num_comments") or 0), reverse=True)
    return rows[:limit]


def selected_topic_key(selection: object) -> str | None:
    """Parse Streamlit/Vega selection for a single ``topic_key``."""

    def _walk(obj: object) -> str | None:
        if obj is None:
            return None
        if isinstance(obj, dict):
            if obj.get("topic_key"):
                return str(obj["topic_key"])
            for value in obj.values():
                found = _walk(value)
                if found:
                    return found
            return None
        if isinstance(obj, (list, tuple)):
            for item in obj:
                found = _walk(item)
                if found:
                    return found
            return None
        mapping = getattr(obj, "selection", None)
        if mapping is not None and mapping is not obj:
            found = _walk(mapping)
            if found:
                return found
        if hasattr(obj, "to_dict"):
            try:
                return _walk(obj.to_dict())
            except Exception:
                pass
        data = getattr(obj, "__dict__", None)
        if isinstance(data, dict) and data:
            return _walk(data)
        return None

    return _walk(selection)


def topics_for_tool(*, cache_dir: Path | str | None = None) -> dict:
    """Ouroboros skill payload: overview only, same JSON cache as the chart."""

    payload = load_cached_topic_payload(cache_dir=cache_dir)
    note = (
        "Reddit oil/energy posts, last 30 Moscow days. Width is comment volume, not prices. "
        "Copy topic labels verbatim. Do not invent extra topics or oil prices from this tool."
    )
    if not payload or payload.get("unavailable_reason"):
        return {
            "topics": [],
            "unavailable_reason": (payload or {}).get("unavailable_reason")
            or "Topic cache is empty. Do not invent narratives.",
            "note": note,
        }
    topics = [
        {
            "label": row.get("label"),
            "total_comments": row.get("total_comments"),
            "size": row.get("size"),
            "dynamics": row.get("dynamics"),
            "headlines": list(row.get("headlines") or [])[:3],
        }
        for row in (payload.get("topics") or [])
    ]
    return {
        "window_start": payload.get("window_start"),
        "window_end": payload.get("window_end"),
        "topics": topics,
        "unavailable_reason": None,
        "note": note,
    }
