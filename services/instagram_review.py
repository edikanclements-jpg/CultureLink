"""Bounded public Instagram collection. Activity metrics never verify a business.

Direct public HTML only. No API keys, paid provider, login, cookies, or proxy.
Only the six handles supplied by the project owner are eligible for collection.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import statistics
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import current_app


ACCOUNTS = {
    1: ("Anita Dongre", "anitadongre"),
    2: ("Anu Attires", "anu_attires"),
    5: ("The India Craft House", "theindiacrafthouse"),
    6: ("Klothouse", "klothouse_official"),
    7: ("Olis Collections", "oliscollections"),
    8: ("Priscer Luxe", "priscer_luxe"),
}
HANDLES = frozenset(value[1] for value in ACCOUNTS.values())
REFRESH_DAYS = 7
RETRY_HOURS = 24
POST_LIMIT = 80
CACHE_FILE = "instagram-public-evidence.json"
CACHE_FORMAT = 2
_THREAD_LOCK = threading.Lock()


class CollectionError(Exception):
    """A deliberately credential-free error, safe to display or log."""

    def __init__(self, message, fresh_retry=False):
        super().__init__(message)
        self.fresh_retry = fresh_retry


def utcnow():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _date(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _count(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if 0 <= value <= 10**10 and int(value) == value else None


def _public(profile):
    if profile.get("error") or profile.get("isRestrictedProfile") is True:
        return False
    flags = [profile.get(key) for key in ("private", "isPrivate") if key in profile]
    return bool(flags) and any(flag is False for flag in flags) and all(flag is False or flag is None for flag in flags)


def account_for(boutique):
    account = ACCOUNTS.get(boutique.get("boutique_id"))
    # Do not attach a familiar ID to a differently named business.
    if account and str(boutique.get("boutique_name", "")).strip().casefold() == account[0].casefold():
        return {"name": account[0], "handle": account[1],
                "url": "https://www.instagram.com/" + account[1] + "/"}
    return None


def _local_path(root, name, create=False):
    root = Path(root).resolve()
    folder = root / "instance"
    if not folder.resolve().is_relative_to(root):
        raise CollectionError("Local Instagram settings must stay inside the project.")
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    result = folder / name
    if not result.resolve().is_relative_to(folder.resolve()):
        raise CollectionError("The local Instagram file has an invalid path.")
    return result


def _read_json(path, limit=250000):
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            return {}
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def _write_json(path, value):
    data = json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".instagram-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicPageError(CollectionError):
    def __init__(self, status):
        super().__init__("Public Instagram data is unavailable.")
        self.status = status


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.scripts = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta":
            key = values.get("property", values.get("name"))
            if key in {"og:title", "og:url", "og:description", "description"}:
                self.meta[key] = (values.get("content") or "")[:2000]
        if tag == "script" and values.get("type") in {"application/json", "application/ld+json"}:
            self._script = []

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None


def _objects(value):
    pending = [(value, 0)]
    visited = 0
    while pending and visited < 20000:
        item, depth = pending.pop()
        visited += 1
        if depth > 60:
            continue
        if isinstance(item, dict):
            yield item
            pending.extend((v, depth + 1) for v in item.values() if isinstance(v, (list, dict)))
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item if isinstance(v, (list, dict)))


def _edge_count(node, *names):
    for name in names:
        edge = node.get(name)
        if isinstance(edge, dict) and _count(edge.get("count")) is not None:
            return _count(edge["count"])
    return None


def _legacy_posts(user, handle):
    timeline = user.get("edge_owner_to_timeline_media")
    if not isinstance(timeline, dict):
        return [], False, False
    edges = timeline.get("edges")
    if not isinstance(edges, list):
        return [], False, True
    posts = []
    incomplete = False
    for edge in edges[:POST_LIMIT]:
        node = edge.get("node") if isinstance(edge, dict) else None
        if not isinstance(node, dict):
            incomplete = True
            continue
        owner = node.get("owner")
        if not isinstance(owner, dict):
            incomplete = True
            continue
        if (str(owner.get("username", "")).casefold() != handle
                and not (user.get("id") and str(owner.get("id")) == str(user["id"]))):
            incomplete = True
            continue
        code = node.get("shortcode")
        timestamp = _count(node.get("taken_at_timestamp"))
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", code) or timestamp is None:
            incomplete = True
            continue
        try:
            published = datetime.fromtimestamp(timestamp, timezone.utc)
        except (ValueError, OSError, OverflowError):
            incomplete = True
            continue
        caption = ""
        caption_edge = node.get("edge_media_to_caption", {})
        if isinstance(caption_edge, dict):
            entries = caption_edge.get("edges", [])
            if isinstance(entries, list) and entries and isinstance(entries[0], dict):
                child = entries[0].get("node", {})
                if isinstance(child, dict) and isinstance(child.get("text"), str):
                    caption = child["text"][:3000]
        posts.append({"ownerUsername": handle, "url": "https://www.instagram.com/p/" + code + "/",
                      "timestamp": _iso(published), "caption": caption,
                      "likesCount": _edge_count(node, "edge_liked_by", "edge_media_preview_like"),
                      "commentsCount": _edge_count(node, "edge_media_to_comment", "edge_media_preview_comment"),
                      "isPinned": node.get("is_pinned") is True,
                      "isSponsored": node.get("is_ad") is True,
                      "isPaidPartnership": node.get("is_paid_partnership") is True})
    page = timeline.get("page_info", {})
    more = len(edges) > POST_LIMIT or (isinstance(page, dict) and page.get("has_next_page") is True)
    return posts, more, incomplete


def parse_public_page(handle, html):
    if handle not in HANDLES or not isinstance(html, str) or len(html) > 2000000:
        raise PublicPageError("unavailable")
    page = _Page()
    page.feed(html)
    expected = "https://www.instagram.com/" + handle + "/"
    canonical = page.meta.get("og:url", "").split("?", 1)[0].rstrip("/") + "/"
    title = page.meta.get("og:title", "")
    description = page.meta.get("og:description", page.meta.get("description", ""))
    if canonical != expected or not re.search(r"\(@" + re.escape(handle) + r"\)", title + description, re.I):
        text = (title + " " + description).casefold()
        raise PublicPageError("login_required" if any(x in text for x in ("log in", "login", "create an account")) else "unavailable")
    profile = {"username": handle}
    found = re.search(r"\b([0-9][0-9,.]*[KMB]?)\s+Followers\b", description, re.I)
    if found:
        label = found[1].upper()
        if re.fullmatch(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?[KMB]?", label):
            approximate = label[-1] in "KMB" or "." in label
            profile.update(followers_display=label, followers_approximate=approximate,
                           followersCount=None if approximate else _count(int(label.replace(",", ""))))
    matches = []
    for script in page.scripts:
        try:
            value = json.loads(script)
        except (ValueError, RecursionError):
            continue
        for obj in _objects(value):
            if (str(obj.get("username", "")).casefold() == handle
                    and isinstance(obj.get("edge_followed_by"), dict)
                    and isinstance(obj.get("is_private"), bool)):
                matches.append(obj)
    if not matches:
        return profile, []
    # Conflicting profile snapshots must not be combined into a synthetic result.
    signatures = {(obj.get("id"), _edge_count(obj, "edge_followed_by"), obj["is_private"]) for obj in matches}
    if len(signatures) != 1:
        return profile, []
    user = matches[0]
    profile.update(private=user["is_private"], followersCount=_edge_count(user, "edge_followed_by"))
    if profile["followersCount"] is not None:
        profile.update(followers_display=str(profile["followersCount"]), followers_approximate=False)
    if user["is_private"]:
        return profile, []
    posts, more, incomplete = _legacy_posts(user, handle)
    profile["feed_has_more"] = more
    profile["feed_incomplete"] = incomplete
    return profile, posts


class PublicInstagramClient:
    """Read only the public HTML response. Stop at login, throttling or a redirect."""
    def __init__(self):
        self.opener = build_opener(_NoRedirect())

    def fetch(self, handle):
        if handle not in HANDLES:
            raise PublicPageError("unavailable")
        request = Request("https://www.instagram.com/" + handle + "/", headers={
            "User-Agent": "CultureLink/1.0 (student public-profile snapshot)",
            "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with self.opener.open(request, timeout=15) as response:
                if "text/html" not in response.headers.get("Content-Type", "").lower():
                    raise PublicPageError("unavailable")
                raw = response.read(2000001)
            if len(raw) > 2000000:
                raise PublicPageError("unavailable")
            return parse_public_page(handle, raw.decode("utf-8", "replace"))
        except HTTPError as error:
            raise PublicPageError("rate_limited" if error.code == 429 else "unavailable") from None
        except (URLError, TimeoutError, OSError, ValueError, RecursionError):
            raise PublicPageError("unavailable") from None


def _post_url(value):
    if not isinstance(value, str) or len(value) > 500:
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme != "https" or parts.netloc not in {"instagram.com", "www.instagram.com"}
                or not re.fullmatch(r"/(?:p|reel|tv)/[A-Za-z0-9_-]+/?", parts.path)):
            return None
    except ValueError:
        return None
    return "https://www.instagram.com" + parts.path.rstrip("/") + "/"


def calculate_snapshot(handle, profile, posts, collected_at):
    """Score visible activity only. No bot, identity, comment-quality or sales claim."""
    if handle not in HANDLES:
        raise ValueError("Choose a configured boutique.")
    if collected_at.tzinfo is None:
        raise ValueError("Use an aware collection timestamp.")
    record = {"handle": handle, "collected_at": _iso(collected_at), "status": "unavailable",
              "followers": None, "score": None, "engagement_rate": None,
              "sample_count": 0, "posts": [], "components": {},
              "source": "Instagram public page", "followers_display": None, "followers_approximate": False,
              "customer_evidence": "Not reviewed", "verification": "Not reviewed"}
    if not isinstance(profile, dict) or str(profile.get("username", "")).casefold() != handle:
        return record
    if profile.get("private") is True or profile.get("isPrivate") is True:
        record["status"] = "private"
        return record
    if profile.get("isRestrictedProfile") is True:
        record["status"] = "restricted"
        return record
    followers = None if profile.get("followers_approximate") is True else _count(profile.get("followersCount"))
    label = profile.get("followers_display")
    if isinstance(label, str) and re.fullmatch(r"[0-9][0-9,.]*[KMB]?", label):
        record["followers_display"] = label
        record["followers_approximate"] = profile.get("followers_approximate") is True
    record["followers"] = followers
    if not _public(profile):
        record["status"] = "partial" if label else "unavailable"
        return record
    candidates, seen = [], {}
    for post in posts:
        if not isinstance(post, dict) or str(post.get("ownerUsername", "")).casefold() != handle:
            continue
        published, url = _date(post.get("timestamp")), _post_url(post.get("url"))
        if not published or not url:
            record["status"] = "incomplete"
            return record
        if not timedelta(days=7) <= collected_at - published <= timedelta(days=90):
            continue
        caption = post.get("caption") or ""
        if not isinstance(caption, str):
            record["status"] = "incomplete"
            return record
        if (post.get("isPinned") is True or post.get("isSponsored") is True
                or post.get("isPaidPartnership") is True or re.search(r"\bgive\s*away\b", caption, re.I)):
            continue
        item = {"url": url, "published_at": _iso(published),
                "likes": _count(post.get("likesCount")), "comments": _count(post.get("commentsCount"))}
        if url in seen:
            if seen[url] != item:
                record["status"] = "incomplete"
                return record
            continue
        seen[url] = item
        candidates.append(item)
    sample = sorted(candidates, key=lambda item: (item["published_at"], item["url"]), reverse=True)[:10]
    record.update(posts=sample, sample_count=len(sample), status="insufficient")
    if profile.get("feed_incomplete") is True:
        record["status"] = "incomplete"
        return record
    if not followers or len(sample) < 6:
        if record["followers_display"] and not followers:
            record["status"] = "partial"
        return record
    if profile.get("feed_has_more") is True and len(sample) < 10:
        record["status"] = "incomplete"
        return record
    if any(item["likes"] is None or item["comments"] is None for item in sample):
        record["status"] = "incomplete"
        return record
    rates = [(Decimal(item["likes"] + item["comments"]) / followers * 100) for item in sample]
    median = statistics.median(rates)
    engagement_points = next(points for minimum, points in [
        (Decimal("3"), 60), (Decimal("2"), 45), (Decimal("1"), 30), (Decimal("0.5"), 15), (Decimal("0"), 0)
    ] if median >= minimum)
    # Comment count is observable; comment authenticity and quality are not inferred.
    commented = sum(item["comments"] > 0 for item in sample)
    conversation_points = int((Decimal(commented) * 25 / len(sample)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    activity_points = 15 if len(sample) == 10 else 10
    record.update(status="measured", engagement_rate=float(median.quantize(Decimal("0.0001"))),
                  score=engagement_points + conversation_points + activity_points,
                  components={"engagement": engagement_points, "conversation": conversation_points,
                              "activity": activity_points, "commented_posts": commented})
    return record


def _empty_record(handle, status, now):
    return {"handle": handle, "collected_at": _iso(now), "status": status,
            "followers": None, "followers_display": None, "followers_approximate": False,
            "score": None, "engagement_rate": None, "sample_count": 0, "posts": [], "components": {},
              "source": "Instagram public page", "followers_display": None, "followers_approximate": False,
            "source": "Instagram public page", "customer_evidence": "Not reviewed", "verification": "Not reviewed"}


def _load_state(root):
    state = _read_json(_local_path(root, CACHE_FILE))
    return state if state.get("format") == CACHE_FORMAT else {}


def _due_handles(state, now):
    until = _date(state.get("retry_after"))
    if until and timedelta(0) < until - now <= timedelta(days=1):
        return []
    attempts = state.get("attempts", {})
    if not isinstance(attempts, dict):
        attempts = {}
    due = []
    for handle in sorted(HANDLES):
        attempt = attempts.get(handle, {})
        if not isinstance(attempt, dict):
            attempt = {}
        checked = _date(attempt.get("checked_at"))
        wait = timedelta(days=REFRESH_DAYS) if attempt.get("status") in {"measured", "partial", "insufficient", "incomplete"} else timedelta(hours=RETRY_HOURS)
        if not checked or checked > now or now - checked >= wait:
            due.append(handle)
    return due


def collect(root, state=None, client=None):
    """A maximum of six public GETs, without credentials or any paid fallback."""
    cache_path = _local_path(root, CACHE_FILE, create=True)
    state = state if isinstance(state, dict) and state.get("format") == CACHE_FORMAT else _load_state(root)
    now = utcnow()
    due = _due_handles(state, now)
    if not due:
        return state
    state.setdefault("records", {})
    state.setdefault("attempts", {})
    if not isinstance(state["records"], dict) or not isinstance(state["attempts"], dict):
        state = {"records": {}, "attempts": {}}
    state.update(format=CACHE_FORMAT, status="running", checked_at=_iso(now), retry_after=None)
    _write_json(cache_path, state)
    client = client or PublicInstagramClient()
    for handle in due:
        try:
            profile, posts = client.fetch(handle)
            record = calculate_snapshot(handle, profile, posts, now)
        except PublicPageError as error:
            record = _empty_record(handle, error.status, now)
        except (CollectionError, OSError, TypeError, ValueError, AttributeError):
            record = _empty_record(handle, "unavailable", now)
        state["attempts"][handle] = {"checked_at": _iso(now), "status": record["status"]}
        previous = state["records"].get(handle, {})
        if not (record["score"] is None and record["status"] not in {"private", "restricted"}
                and isinstance(previous, dict) and previous.get("status") == "measured"):
            state["records"][handle] = record
        if record["status"] == "rate_limited":
            state["retry_after"] = _iso(now + timedelta(hours=RETRY_HOURS))
            break
        _write_json(cache_path, state)
    state["status"] = "complete"
    _write_json(cache_path, state)
    return state


def _worker(root):
    lock = _local_path(root, "instagram-public-refresh.lock", create=True)
    descriptor = None
    try:
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if time.time() - lock.stat().st_mtime < 900:
                return
            lock.unlink()
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        collect(root)
    except (OSError, CollectionError):
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)
            lock.unlink(missing_ok=True)


def maybe_refresh():
    if current_app.config.get("INSTAGRAM_REVIEW_ENABLED") is False:
        return
    if current_app.testing and current_app.config.get("INSTAGRAM_REVIEW_TEST_NETWORK") is not True:
        return
    root = current_app.root_path
    if not _due_handles(_load_state(root), utcnow()):
        return
    with _THREAD_LOCK:
        thread = current_app.extensions.get("instagram_refresh_thread")
        if thread and thread.is_alive():
            return
        thread = threading.Thread(target=_worker, args=(root,), daemon=True, name="culturelink-instagram-public")
        current_app.extensions["instagram_refresh_thread"] = thread
        thread.start()


def snapshot_for(boutique):
    account = account_for(boutique)
    if not account:
        return None
    result = dict(_empty_record(account["handle"], "pending", utcnow()), **account, stale=False)
    result["collected_at"] = None
    try:
        state = _load_state(current_app.root_path)
        record = state.get("records", {}).get(account["handle"], {})
        collected = _date(record.get("collected_at"))
        if collected and timedelta(0) <= utcnow() - collected <= timedelta(days=90):
            stored_status = record.get("status")
            profile = {"username": account["handle"], "followersCount": record.get("followers"),
                       "followers_display": record.get("followers_display"),
                       "followers_approximate": record.get("followers_approximate") is True,
                       "private": stored_status == "private", "isRestrictedProfile": stored_status == "restricted"}
            posts = [{"ownerUsername": account["handle"], "timestamp": item.get("published_at"),
                      "url": item.get("url"), "likesCount": item.get("likes"),
                      "commentsCount": item.get("comments")} for item in record.get("posts", [])[:10]]
            computed = calculate_snapshot(account["handle"], profile, posts, collected)
            if stored_status != "measured":
                computed["score"] = None
                computed["status"] = stored_status if stored_status in {
                    "private", "restricted", "partial", "login_required", "unavailable", "rate_limited", "incomplete", "insufficient"
                } else "unavailable"
            result.update(computed)
            result["stale"] = utcnow() - collected >= timedelta(days=REFRESH_DAYS)
        elif collected:
            result["status"] = "outdated"
        maybe_refresh()
    except (CollectionError, OSError, ValueError, TypeError, AttributeError):
        result.update(status="unavailable", score=None)
    return result
