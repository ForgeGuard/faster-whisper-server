#!/usr/bin/env python3
"""Repository-owned documentation validator for the ForgeGuard docs contract.

Validates the README, the `.forgeguard/docs.yml` manifest, and the published
documentation under `docs/site/` without any third-party dependencies, network
access, GPU, or model downloads. Run from the repository root:

    python scripts/docs/validate_docs.py

Exit code 0 means all checks passed; 1 means one or more errors were found.

Checks (see .github/workflows/docs-validate.yml):
  * manifest schema and exact repository identity;
  * docs/site/index.md presence;
  * required front matter and allowed status values;
  * unique routes and unique navigation order;
  * internal links / anchors and image existence;
  * no publication-root escapes and no symlinks under docs/site;
  * no site links into maintainer-only content;
  * basic Markdown hygiene;
  * banner type / path / dimensions (2172x724) and reasonable size;
  * README banner and docs-index references;
  * a conservative secret scan.

Optional external-link checking is opt-in via --check-external (kept off by
default so the docs CI never depends on the network).
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE_ROOT = os.path.join("docs", "site")
MAINTAINERS_ROOT = os.path.join("docs", "maintainers")
MANIFEST_PATH = os.path.join(".forgeguard", "docs.yml")
README_PATH = "README.md"
BANNER_PATH = os.path.join(SITE_ROOT, "assets", "repository", "banner-dark.png")

EXPECTED_IDENTITY = {
    "owner": "forgeguard-ai",
    "name": "faster-whisper-server",
    "content_root": "docs/site",
    "entrypoint": "index.md",
}
ALLOWED_STATUS = {"stable", "beta", "experimental", "deprecated"}
REQUIRED_FRONT_MATTER = ("title", "description", "order", "status")
BANNER_DIMENSIONS = (2172, 724)
BANNER_MAX_BYTES = 5 * 1024 * 1024

# Placeholder secrets that are intentionally present in the docs.
SECRET_ALLOWLIST = {"change-me", "test-key", "not-needed", "<key>", "api-key"}
SECRET_PATTERNS = [
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghs|ghr|github_pat)_[0-9A-Za-z_]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("AWS secret access key", re.compile(r"aws_secret_access_key\s*[:=]\s*[0-9A-Za-z/+]{40}")),
]


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# --------------------------------------------------------------------------- #
# Minimal YAML-subset parser for the manifest and front matter.
# --------------------------------------------------------------------------- #
def _coerce(value: str):
    value = value.strip()
    if value == "":
        return ""
    if (value[0] == value[-1]) and value[0] in "\"'":
        return value[1:-1]
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_nested_yaml(text: str) -> dict:
    """Parse a 2-space-indented mapping-of-mappings of scalars (no lists)."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if rest.strip() == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce(rest)
    return root


def parse_front_matter(text: str) -> tuple[dict | None, str]:
    """Return (front_matter_dict, body). front_matter is None when absent."""
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_text = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            fm: dict = {}
            for raw in fm_text.splitlines():
                if not raw.strip() or raw.lstrip().startswith("#"):
                    continue
                if ":" not in raw:
                    continue
                key, _, val = raw.partition(":")
                fm[key.strip()] = _coerce(val)
            return fm, body
    return None, text


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def read(path: str) -> str:
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def iter_site_markdown() -> list[str]:
    out: list[str] = []
    base = os.path.join(REPO_ROOT, SITE_ROOT)
    for dirpath, _dirs, files in os.walk(base):
        for name in files:
            if name.endswith(".md"):
                out.append(os.path.relpath(os.path.join(dirpath, name), REPO_ROOT))
    return sorted(out)


def png_dimensions(path: str) -> tuple[int, int] | None:
    with open(os.path.join(REPO_ROOT, path), "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def slugify_heading(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"`|\*|_", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def headings_of(body: str) -> set[str]:
    slugs: set[str] = set()
    in_fence = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            slugs.add(slugify_heading(m.group(1)))
    return slugs


LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def check_manifest(rep: Report) -> None:
    if not os.path.exists(os.path.join(REPO_ROOT, MANIFEST_PATH)):
        rep.error(f"{MANIFEST_PATH}: manifest is missing")
        return
    data = parse_nested_yaml(read(MANIFEST_PATH))
    if data.get("version") != 1:
        rep.error(f"{MANIFEST_PATH}: version must be 1")
    if data.get("enabled") is not True:
        rep.error(f"{MANIFEST_PATH}: enabled must be true")
    project = data.get("project", {})
    if project.get("kind") != "original":
        rep.error(f"{MANIFEST_PATH}: project.kind must be 'original'")
    for field_name in ("slug", "title", "summary"):
        if not project.get(field_name):
            rep.error(f"{MANIFEST_PATH}: project.{field_name} is required")
    repository = data.get("repository", {})
    if repository.get("owner") != EXPECTED_IDENTITY["owner"]:
        rep.error(f"{MANIFEST_PATH}: repository.owner must be {EXPECTED_IDENTITY['owner']!r}")
    if repository.get("name") != EXPECTED_IDENTITY["name"]:
        rep.error(f"{MANIFEST_PATH}: repository.name must be {EXPECTED_IDENTITY['name']!r}")
    source = data.get("source", {})
    if source.get("content_root") != EXPECTED_IDENTITY["content_root"]:
        rep.error(f"{MANIFEST_PATH}: source.content_root must be 'docs/site'")
    if source.get("entrypoint") != EXPECTED_IDENTITY["entrypoint"]:
        rep.error(f"{MANIFEST_PATH}: source.entrypoint must be 'index.md'")
    publishing = data.get("publishing", {})
    if publishing.get("include_generated") is not False:
        rep.error(f"{MANIFEST_PATH}: publishing.include_generated must be false")
    if publishing.get("versions") not in ("both", "releases", "default-branch"):
        rep.error(f"{MANIFEST_PATH}: publishing.versions is invalid")
    # No maintained-fork fields on an original.
    if "upstream" in data:
        rep.error(f"{MANIFEST_PATH}: original project must not declare an 'upstream' block")


def check_index_present(rep: Report) -> None:
    if not os.path.exists(os.path.join(REPO_ROOT, SITE_ROOT, "index.md")):
        rep.error(f"{SITE_ROOT}/index.md is required but missing")


def check_no_symlinks(rep: Report) -> None:
    base = os.path.join(REPO_ROOT, SITE_ROOT)
    for dirpath, dirs, files in os.walk(base):
        for name in list(dirs) + files:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                rep.error(f"{os.path.relpath(full, REPO_ROOT)}: symlinks are not allowed under docs/site")


def check_front_matter_and_links(rep: Report) -> None:
    pages = iter_site_markdown()
    orders: dict[int, str] = {}
    site_abs = os.path.join(REPO_ROOT, SITE_ROOT)

    # Pre-compute headings per site page for anchor validation.
    heading_cache: dict[str, set[str]] = {}
    for page in pages:
        _fm, body = parse_front_matter(read(page))
        heading_cache[os.path.normpath(page)] = headings_of(body)

    for page in pages:
        text = read(page)
        fm, body = parse_front_matter(text)
        if fm is None:
            rep.error(f"{page}: missing YAML front matter")
            continue
        for key in REQUIRED_FRONT_MATTER:
            if key not in fm or fm[key] in ("", None):
                rep.error(f"{page}: front matter missing required key '{key}'")
        if "status" in fm and fm["status"] not in ALLOWED_STATUS:
            rep.error(
                f"{page}: front matter status {fm['status']!r} not in {sorted(ALLOWED_STATUS)}"
            )
        if "order" in fm:
            order = fm["order"]
            if not isinstance(order, int):
                rep.error(f"{page}: front matter 'order' must be an integer")
            elif order in orders:
                rep.error(
                    f"{page}: duplicate navigation order {order} (also {orders[order]})"
                )
            else:
                orders[order] = page

        page_dir = os.path.dirname(os.path.join(REPO_ROOT, page))

        # Internal links.
        for target in LINK_RE.findall(body):
            _check_target(rep, page, page_dir, site_abs, target, heading_cache, is_image=False)
        for target in IMAGE_RE.findall(body):
            _check_target(rep, page, page_dir, site_abs, target, heading_cache, is_image=True)

        _check_markdown_hygiene(rep, page, body)


def _check_target(rep, page, page_dir, site_abs, target, heading_cache, is_image):
    target = target.strip()
    if not target:
        rep.error(f"{page}: empty link target")
        return
    # External and non-file schemes are left to the optional external checker.
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target) or target.startswith("mailto:"):
        return
    if target.startswith("#"):
        anchor = target[1:]
        if anchor and anchor not in heading_cache.get(os.path.normpath(page), set()):
            rep.error(f"{page}: anchor '{target}' does not match a heading")
        return

    path_part, _, anchor = target.partition("#")
    if path_part == "":
        return
    resolved = os.path.normpath(os.path.join(page_dir, path_part))

    # Publication-root boundary: no escapes out of docs/site.
    if not (resolved == site_abs or resolved.startswith(site_abs + os.sep)):
        rep.error(f"{page}: link '{target}' escapes the publication root (docs/site)")
        return
    rel = os.path.relpath(resolved, REPO_ROOT)
    # No site links into maintainer-only content (defensive; maintainers is outside site anyway).
    if rel.startswith(MAINTAINERS_ROOT + os.sep):
        rep.error(f"{page}: link '{target}' points into maintainer-only content")
        return
    if not os.path.exists(resolved):
        kind = "image" if is_image else "link"
        rep.error(f"{page}: {kind} target does not exist: {target}")
        return
    # Cross-file anchor validation for markdown targets.
    if anchor and resolved.endswith(".md"):
        slugs = heading_cache.get(os.path.normpath(rel))
        if slugs is not None and anchor not in slugs:
            rep.error(f"{page}: anchor '#{anchor}' not found in {rel}")


def _check_markdown_hygiene(rep: Report, page: str, body: str) -> None:
    in_fence = False
    for i, line in enumerate(body.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.rstrip() != line and line.strip():
            rep.warn(f"{page}:{i}: trailing whitespace")
        if "\t" in line:
            rep.warn(f"{page}:{i}: tab character (use spaces)")
        if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", line):
            rep.error(f"{page}:{i}: TODO/FIXME/XXX marker in published docs")
    if in_fence:
        rep.error(f"{page}: unbalanced code fence (```)")


def check_banner(rep: Report) -> None:
    if not os.path.exists(os.path.join(REPO_ROOT, BANNER_PATH)):
        rep.error(f"{BANNER_PATH}: banner is missing")
        return
    dims = png_dimensions(BANNER_PATH)
    if dims is None:
        rep.error(f"{BANNER_PATH}: not a valid PNG")
        return
    if dims != BANNER_DIMENSIONS:
        rep.error(
            f"{BANNER_PATH}: dimensions {dims[0]}x{dims[1]} != required "
            f"{BANNER_DIMENSIONS[0]}x{BANNER_DIMENSIONS[1]}"
        )
    size = os.path.getsize(os.path.join(REPO_ROOT, BANNER_PATH))
    if size > BANNER_MAX_BYTES:
        rep.error(f"{BANNER_PATH}: {size} bytes exceeds {BANNER_MAX_BYTES}")
    # A repository banner-light.png must not exist (central site owns it).
    light = os.path.join(SITE_ROOT, "assets", "repository", "banner-light.png")
    if os.path.exists(os.path.join(REPO_ROOT, light)):
        rep.error(f"{light}: must not exist (the central website owns the light banner)")


def check_readme(rep: Report) -> None:
    if not os.path.exists(os.path.join(REPO_ROOT, README_PATH)):
        rep.error("README.md is missing")
        return
    text = read(README_PATH)
    banner_ref = "docs/site/assets/repository/banner-dark.png"
    if banner_ref not in text:
        rep.error(f"README.md: does not reference the banner ({banner_ref})")
    if "docs/site/index.md" not in text:
        rep.error("README.md: does not link to docs/site/index.md")
    # The banner must have descriptive alt text.
    if re.search(r"banner-dark\.png", text) and 'alt=""' in text:
        rep.warn("README.md: banner image appears to have empty alt text")


def check_secrets(rep: Report) -> None:
    targets = [README_PATH, MANIFEST_PATH] + iter_site_markdown()
    targets += [
        os.path.relpath(os.path.join(dp, f), REPO_ROOT)
        for dp, _d, fs in os.walk(os.path.join(REPO_ROOT, MAINTAINERS_ROOT))
        for f in fs
        if f.endswith(".md")
    ]
    for path in targets:
        if not os.path.exists(os.path.join(REPO_ROOT, path)):
            continue
        text = read(path)
        for label, pattern in SECRET_PATTERNS:
            for m in pattern.finditer(text):
                snippet = m.group(0)
                if snippet in SECRET_ALLOWLIST:
                    continue
                rep.error(f"{path}: possible {label} committed: {snippet[:12]}…")


def check_external_links(rep: Report) -> None:
    """Opt-in. Best-effort HEAD/GET with one retry; only warns on failure."""
    urls: set[str] = set()
    for page in iter_site_markdown() + [README_PATH]:
        _fm, body = parse_front_matter(read(page))
        for target in LINK_RE.findall(body) + IMAGE_RE.findall(body):
            if target.startswith(("http://", "https://")):
                urls.add(target.split("#", 1)[0])
    for url in sorted(urls):
        ok = False
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "docs-validate"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status < 400:
                        ok = True
                        break
            except (urllib.error.URLError, TimeoutError, ValueError):
                continue
        if not ok:
            rep.warn(f"external link unreachable (non-blocking): {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ForgeGuard documentation.")
    parser.add_argument(
        "--check-external",
        action="store_true",
        help="Also check external links (network required; only warns).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    args = parser.parse_args()

    rep = Report()
    check_manifest(rep)
    check_index_present(rep)
    check_no_symlinks(rep)
    check_front_matter_and_links(rep)
    check_banner(rep)
    check_readme(rep)
    check_secrets(rep)
    if args.check_external:
        check_external_links(rep)

    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")

    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    print()
    print(
        f"Documentation validation: {len(rep.errors)} error(s), "
        f"{len(rep.warnings)} warning(s)."
    )
    if failed:
        print("FAILED")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
