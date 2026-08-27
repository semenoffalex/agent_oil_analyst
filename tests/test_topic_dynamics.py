"""Oil Reddit topic dynamics: filters, cache, ThemeRiver, skill payload."""

from datetime import date, datetime, timezone
from http.client import IncompleteRead

from oil_gas_analyst.topic_dynamics import (
    OTHER_KEY,
    OTHER_LABEL,
    OUTLIER_TOPIC_ID,
    RedditOilPost,
    _arctic_shift_page,
    archive_error_copy,
    build_topic_payload,
    cluster_documents,
    fetch_subreddit_since,
    is_dropped_reddit_post,
    load_cached_topic_payload,
    matches_oil_keywords,
    parse_labels_json,
    posts_for_topic,
    reddit_post_to_record,
    refresh_topic_dynamics_payload,
    save_topic_payload_cache,
    select_diverse_topic_ids,
    selected_topic_key,
    topic_chart_dataframe,
    topic_payload_is_fresh,
    topic_streamgraph_altair,
    topics_for_tool,
    window_dates,
)


def _post(
    pid: str,
    *,
    day: str,
    comments: int,
    title: str = "Brent crude jumps",
    sub: str = "oil",
) -> RedditOilPost:
    return RedditOilPost(
        id=pid,
        subreddit=sub,
        title=title,
        body="",
        url=f"https://www.reddit.com/r/{sub}/comments/{pid.removeprefix('t3_')}/",
        created_utc=0.0,
        num_comments=comments,
        chunk_text=title,
        day_msk=day,
    )


def _two_cluster_fn(docs: list[str], vectors: list[list[float]]):
    from oil_gas_analyst.topic_dynamics import ClusterResult

    topic_ids = [0 if i < len(docs) // 2 else 1 for i in range(len(docs))]
    if len(docs) > 8:
        topic_ids = [i % 7 for i in range(len(docs))]
    reps: dict[int, list[str]] = {}
    for doc, tid in zip(docs, topic_ids, strict=True):
        reps.setdefault(tid, [])
        if len(reps[tid]) < 3:
            reps[tid].append(doc)
    return ClusterResult(
        topic_ids=topic_ids,
        probabilities=[0.9] * len(docs),
        representative_docs=reps,
    )


def test_keyword_filter_accepts_oil_rejects_boiler_and_bare_gas():
    assert matches_oil_keywords("Brent crude inventory")
    assert matches_oil_keywords("нефть марки Urals")
    assert not matches_oil_keywords("natural gas prices only")
    assert not matches_oil_keywords("a boiler explosion downtown")


def test_dropped_posts_include_nsfw_stickied_removed():
    assert is_dropped_reddit_post({"over_18": True, "title": "Brent", "selftext": "oil"})
    assert is_dropped_reddit_post({"stickied": True, "title": "Brent", "selftext": "oil"})
    assert is_dropped_reddit_post({"title": "[removed]", "selftext": "oil"})
    assert is_dropped_reddit_post({"title": "Brent oil", "selftext": "[deleted]"})
    assert is_dropped_reddit_post({"title": "Brent oil", "removed_by_category": "moderator"})
    raw = {
        "id": "abc",
        "title": "OPEC+ output",
        "selftext": "crude cuts",
        "subreddit": "oil",
        "created_utc": 1_700_000_000,
        "num_comments": 4,
        "permalink": "/r/oil/comments/abc/opec/",
        "over_18": False,
        "stickied": False,
    }
    record = reddit_post_to_record(raw)
    assert record is not None
    assert record.id == "t3_abc"
    assert "opec" in record.url
    eia = {
        "id": "spr1",
        "title": "Where is this weeks EIA SPR weekly report?",
        "selftext": "Isn't it supposed to come out every Wednesday?",
        "subreddit": "oil",
        "created_utc": 1_700_000_000,
        "num_comments": 2,
        "permalink": "/r/oil/comments/spr1/eia/",
        "over_18": False,
        "stickied": False,
    }
    assert reddit_post_to_record(eia) is not None
    solar = dict(eia, id="sol1", subreddit="energy", title="New solar farm capacity")
    assert reddit_post_to_record(solar) is None
    brent_energy = dict(eia, id="br1", subreddit="energy", title="Brent crude slips")
    assert reddit_post_to_record(brent_energy) is not None


def test_window_is_thirty_moscow_calendar_days():
    start, end = window_dates(today=date(2026, 8, 27))
    assert start == date(2026, 7, 29)
    assert end == date(2026, 8, 27)


def test_fetch_pages_until_before_window(monkeypatch):
    pages = [
        [
            {"id": "new", "created_utc": 2_000, "title": "new"},
            {"id": "mid", "created_utc": 1_500, "title": "mid"},
        ],
        [
            {"id": "old", "created_utc": 500, "title": "old"},
        ],
    ]

    def get_page(params):
        assert params["subreddit"] == "oil"
        assert "after" not in params
        assert "query" not in params
        return pages.pop(0)

    posts = fetch_subreddit_since("oil", since_ts=1000, get_page=get_page, throttle=0.0)
    ids = [p["id"] for p in posts]
    assert ids == ["new", "mid"]
    assert "old" not in ids
    assert pages == []


def test_energy_pages_request_oil_query():
    seen: dict = {}

    def get_page(params):
        seen.update(params)
        return [{"id": "e1", "created_utc": 1500}]

    posts = fetch_subreddit_since(
        "energy", since_ts=1000, get_page=get_page, throttle=0.0, max_posts=20
    )
    assert seen["query"] == "oil"
    assert "after" not in seen
    assert posts[0]["id"] == "e1"


def test_oilandgas_keeps_posts_without_oil_keyword():
    raw = {
        "id": "og1",
        "title": "Looking to connect with people in the industry",
        "selftext": "",
        "subreddit": "oilandgas",
        "created_utc": 1_700_000_000,
        "num_comments": 2,
        "over_18": False,
        "stickied": False,
    }
    assert reddit_post_to_record(raw) is not None


def test_arctic_shift_retries_incomplete_read(monkeypatch):
    monkeypatch.setattr("oil_gas_analyst.topic_dynamics.time.sleep", lambda _s: None)
    calls = {"n": 0}

    def get_json(url, params, timeout=120.0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise IncompleteRead(b"")
        return {"data": [{"id": "abc", "created_utc": 1}]}

    rows = _arctic_shift_page({"subreddit": "oil", "limit": 10}, get_json=get_json)
    assert calls["n"] == 3
    assert rows[0]["id"] == "abc"


def test_archive_error_copy_hides_urllib_guts():
    text = archive_error_copy(IncompleteRead(b""))
    assert "IncompleteRead" not in text
    assert "bytes" not in text
    assert "Обновить" in text


def test_build_payload_top_six_plus_other_and_comment_width():
    today = date(2026, 8, 27)
    posts = []
    for tid in range(7):
        for n in range(2):
            posts.append(
                _post(
                    f"t3_{tid}_{n}",
                    day="2026-08-20" if n == 0 else "2026-08-26",
                    comments=10 * (tid + 1),
                    title=f"Brent cluster {tid}",
                )
            )
    payload = build_topic_payload(
        posts,
        today=today,
        embed_fn=lambda docs: [[1.0, 0.0]] * len(docs),
        cluster_fn=_two_cluster_fn,
        label_fn=lambda reps: {tid: f"Тема {tid}" for tid in reps if tid != OUTLIER_TOPIC_ID},
    )
    keys = [row["key"] for row in payload["topics"]]
    assert OTHER_KEY in keys
    assert len([k for k in keys if k != OTHER_KEY]) == 6
    other = next(row for row in payload["topics"] if row["key"] == OTHER_KEY)
    assert other["label"] == OTHER_LABEL
    assert other["size"] == 2
    assert {row["date"] for row in payload["series"]} >= {"2026-07-29", "2026-08-27"}
    late = [
        row
        for row in payload["series"]
        if row["date"] == "2026-08-26" and row["topic_key"] != OTHER_KEY
    ]
    assert all(row["comments"] > 0 for row in late)


def test_posts_for_topic_sorts_by_comments_and_ignores_day():
    today = date(2026, 8, 27)
    posts = [
        _post("t3_a", day="2026-08-01", comments=1, title="Brent quiet"),
        _post("t3_b", day="2026-08-20", comments=50, title="Brent spike"),
        _post("t3_c", day="2026-08-10", comments=20, title="Brent mid"),
    ]

    def one_cluster(docs, vectors):
        from oil_gas_analyst.topic_dynamics import ClusterResult

        return ClusterResult(
            topic_ids=[0, 0, 0],
            probabilities=[1.0, 1.0, 1.0],
            representative_docs={0: docs[:3]},
        )

    payload = build_topic_payload(
        posts,
        today=today,
        embed_fn=lambda docs: [[1.0]] * len(docs),
        cluster_fn=one_cluster,
        label_fn=lambda reps: {0: "ОПЕК"},
    )
    ranked = posts_for_topic(payload, "0")
    assert [row["id"] for row in ranked] == ["t3_b", "t3_c", "t3_a"]


def test_topic_cache_roundtrip_and_ttl(tmp_path):
    payload = {
        "fetched_at": datetime(2026, 8, 27, 12, tzinfo=timezone.utc).isoformat(),
        "window_start": "2026-07-29",
        "window_end": "2026-08-27",
        "unavailable_reason": None,
        "topics": [{"key": "0", "label": "ОПЕК", "total_comments": 3, "size": 1, "dynamics": "выросла", "headlines": ["Brent"]}],
        "series": [],
        "posts": [],
    }
    save_topic_payload_cache(payload, cache_dir=tmp_path)
    cached = load_cached_topic_payload(cache_dir=tmp_path)
    assert cached is not None
    assert cached["topics"][0]["label"] == "ОПЕК"
    now = datetime(2026, 8, 27, 14, tzinfo=timezone.utc)
    assert topic_payload_is_fresh(cached, now=now)
    later = datetime(2026, 8, 28, 0, tzinfo=timezone.utc)
    assert not topic_payload_is_fresh(cached, now=later)


def test_refresh_reuses_fresh_cache(tmp_path, monkeypatch):
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "window_start": "2026-07-29",
        "window_end": "2026-08-27",
        "unavailable_reason": None,
        "topics": [{"key": "0", "label": "кэш", "total_comments": 1, "size": 1, "dynamics": "без явного тренда", "headlines": []}],
        "series": [{"date": "2026-08-01", "topic_key": "0", "label": "кэш", "comments": 1}],
        "posts": [],
    }
    save_topic_payload_cache(payload, cache_dir=tmp_path)

    def boom(**kwargs):
        raise AssertionError("must not fetch when cache is fresh")

    monkeypatch.setattr("oil_gas_analyst.topic_dynamics.fetch_oil_reddit_posts", boom)
    out = refresh_topic_dynamics_payload(cache_dir=tmp_path, force=False)
    assert out["topics"][0]["label"] == "кэш"


def test_streamgraph_uses_centered_stack():
    payload = {
        "series": [
            {"date": "2026-08-01", "topic_key": "0", "label": "ОПЕК", "comments": 4},
            {"date": "2026-08-01", "topic_key": OTHER_KEY, "label": OTHER_LABEL, "comments": 1},
            {"date": "2026-08-02", "topic_key": "0", "label": "ОПЕК", "comments": 2},
            {"date": "2026-08-02", "topic_key": OTHER_KEY, "label": OTHER_LABEL, "comments": 0},
        ]
    }
    frame = topic_chart_dataframe(payload)
    assert frame is not None
    chart = topic_streamgraph_altair(frame)
    spec = chart.to_dict()
    y = spec["encoding"]["y"]
    assert y["stack"] == "center"
    color = spec["encoding"]["color"]["scale"]
    assert "ОПЕК" in color["domain"]
    assert OTHER_LABEL not in color["domain"]


def test_selected_topic_key_reads_vega_and_streamlit_shapes():
    assert selected_topic_key({"topic_pick": [{"topic_key": "other"}]}) == "other"
    assert selected_topic_key({"selection": {"topic_pick": [{"topic_key": "0"}]}}) == "0"
    assert selected_topic_key({}) is None


def test_topics_for_tool_reads_cache(tmp_path):
    save_topic_payload_cache(
        {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "window_start": "2026-07-29",
            "window_end": "2026-08-27",
            "unavailable_reason": None,
            "topics": [
                {
                    "key": "0",
                    "label": "Запасы EIA",
                    "total_comments": 12,
                    "size": 4,
                    "dynamics": "выросла",
                    "headlines": ["Brent inventory", "crude stocks", "extra"],
                }
            ],
            "series": [],
            "posts": [],
        },
        cache_dir=tmp_path,
    )
    tool = topics_for_tool(cache_dir=tmp_path)
    assert tool["unavailable_reason"] is None
    assert tool["topics"][0]["label"] == "Запасы EIA"
    assert tool["topics"][0]["headlines"] == ["Brent inventory", "crude stocks", "extra"]
    assert "Do not invent" in tool["note"]


def test_parse_labels_json_fenced():
    assert parse_labels_json('```json\n{"labels": {"0": "ОПЕК+"}}\n```') == {0: "ОПЕК+"}


def test_select_diverse_topics_skips_near_duplicates():
    vectors = {
        0: [1.0, 0.0, 0.0],
        1: [0.995, 0.1, 0.0],
        2: [0.0, 1.0, 0.0],
        3: [0.0, 0.0, 1.0],
    }
    import numpy as np

    normed = {
        tid: (np.asarray(vec) / np.linalg.norm(vec)).tolist() for tid, vec in vectors.items()
    }
    keep = select_diverse_topic_ids([0, 1, 2, 3], normed, k=3)
    assert keep[0] == 0
    assert 1 not in keep
    assert set(keep) == {0, 2, 3}


def test_select_diverse_topics_one_cluster_per_storyline():
    vectors = {
        0: [1.0, 0.0, 0.0],
        1: [0.0, 1.0, 0.0],
        2: [0.0, 0.0, 1.0],
    }
    import numpy as np

    normed = {
        tid: (np.asarray(vec) / np.linalg.norm(vec)).tolist() for tid, vec in vectors.items()
    }
    keep = select_diverse_topic_ids(
        [0, 1, 2],
        normed,
        k=3,
        themes={0: "hormuz", 1: "hormuz", 2: "eia_spr"},
    )
    assert keep == [0, 2]


def test_cluster_documents_splits_two_blobs():
    docs = ["a", "b", "c", "d"]
    embeddings = [
        [1.0, 0.0],
        [0.99, 0.01],
        [0.0, 1.0],
        [0.01, 0.99],
    ]
    result = cluster_documents(docs, embeddings, min_cluster_size=2)
    assert set(result.topic_ids) != {OUTLIER_TOPIC_ID}
    assert len(result.topic_ids) == 4


def test_hdbscan_min_size_grows_with_corpus():
    from oil_gas_analyst.topic_dynamics import _hdbscan_min_size

    assert _hdbscan_min_size(10) == 2
    assert 10 <= _hdbscan_min_size(1105) <= 25


def test_assign_outliers_joins_nearest_blob():
    import numpy as np
    from oil_gas_analyst.topic_dynamics import _assign_outliers_to_nearest

    space = np.array([[0.0, 0.0], [0.1, 0.0], [10.0, 0.0], [0.05, 0.0]])
    out = _assign_outliers_to_nearest([0, 0, 1, -1], space)
    assert out[3] == 0
