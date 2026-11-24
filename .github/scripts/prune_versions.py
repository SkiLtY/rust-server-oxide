#!/usr/bin/env python3
"""Decide which GHCR package versions of this image to delete.

Reads the JSON from `gh api .../packages/container/<name>/versions --paginate`
on stdin and prints one line per version:

    KEEP   <id> <created_at> <tags>
    DELETE <id> <created_at> <tags>

It never deletes anything itself.

Why this works on whole builds rather than single versions: one `docker
buildx build --push` creates several package versions at once (the index
manifest, the image manifest, and attestation manifests), and only the index
carries the tags. Deleting an "untagged" version can therefore delete a child
of the image you are running. So versions are grouped into builds (versions
created within GAP seconds of each other are one build), and a build is kept
or deleted as a unit.

A build is kept if it is:
  * the one holding the `latest` tag, or
  * the newest build overall (may be mid-publish), or
  * one of the newest KEEP builds that still hold a release tag
    `rust-<steam build>-oxide-<oxide version>`.

A nightly rebuild of an unchanged release moves the release tag to the new
build, so superseded duplicates lose their tag and are deleted, while the
previous *releases* keep theirs and are retained. KEEP therefore counts
distinct Rust/Oxide releases, not nights.

Exits non-zero (and prints nothing to delete) if the data looks wrong, e.g.
no build holds `latest`, rather than guessing.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

GAP = 120  # seconds between versions of the same build
KEEP = int(os.environ.get("KEEP", "3"))
RELEASE_TAG = re.compile(r"^rust-.+-oxide-.+$")


def read_json_documents(text):
    """gh --paginate prints one JSON array per page, concatenated."""
    decoder = json.JSONDecoder()
    pos, items = 0, []
    text = text.strip()
    while pos < len(text):
        doc, end = decoder.raw_decode(text, pos)
        items.extend(doc if isinstance(doc, list) else [doc])
        pos = end
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return items


def ts(created_at):
    return datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def main():
    versions = read_json_documents(sys.stdin.read())
    if not versions:
        print("ERROR: no package versions returned", file=sys.stderr)
        return 2

    rows = []
    for v in versions:
        tags = (v.get("metadata", {}).get("container", {}) or {}).get("tags") or []
        rows.append({"id": v["id"], "created": v["created_at"], "t": ts(v["created_at"]), "tags": tags})
    rows.sort(key=lambda r: r["t"])

    builds = []
    for r in rows:
        if builds and r["t"] - builds[-1]["last"] <= GAP:
            builds[-1]["members"].append(r)
            builds[-1]["last"] = r["t"]
        else:
            builds.append({"members": [r], "last": r["t"]})
    for b in builds:
        b["tags"] = sorted({t for m in b["members"] for t in m["tags"]})
        b["latest"] = "latest" in b["tags"]
        b["release"] = any(RELEASE_TAG.match(t) for t in b["tags"])

    if not any(b["latest"] for b in builds):
        print("ERROR: no build holds the 'latest' tag; refusing to prune", file=sys.stderr)
        return 2

    keep = {id(b) for b in builds if b["latest"]}
    keep.add(id(builds[-1]))
    releases = [b for b in builds if b["release"]]  # oldest -> newest
    keep.update(id(b) for b in releases[-KEEP:])

    kept = deleted = 0
    for b in builds:
        verdict = "KEEP" if id(b) in keep else "DELETE"
        for m in b["members"]:
            print(f"{verdict} {m['id']} {m['created']} {','.join(m['tags']) or '-'}")
        if verdict == "KEEP":
            kept += 1
        else:
            deleted += 1
    print(f"# builds: {len(builds)} total, {kept} kept, {deleted} to delete (KEEP={KEEP} releases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
