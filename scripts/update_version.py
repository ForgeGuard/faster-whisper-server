#!/usr/bin/env python3
"""
Version Update Script

This script reads the version from the VERSION file and updates references
in pyproject.toml, the Helm chart, and README.md.
"""

import json
import re
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent

# --- Configuration ---
VERSION_FILE = ROOT_DIR / "VERSION"
PYPROJECT_FILE = ROOT_DIR / "pyproject.toml"
HELM_CHART_FILE = ROOT_DIR / "charts" / "faster-whisper-server" / "Chart.yaml"
README_FILE = ROOT_DIR / "README.md"
WEBUI_PACKAGE_FILE = ROOT_DIR / "webui" / "package.json"
# --- End Configuration ---


def update_pyproject(version: str):
    """Updates the version in pyproject.toml"""
    if not PYPROJECT_FILE.exists():
        print(f"Skipping: {PYPROJECT_FILE} not found.")
        return

    try:
        content = PYPROJECT_FILE.read_text()
        # Regex to find and capture current version = "X.Y.Z" under [project]
        pattern = r'(^\[project\]\s*(?:.*\s)*?version\s*=\s*)"([^"]+)"'
        match = re.search(pattern, content, flags=re.MULTILINE)

        if not match:
            print(f"Warning: Version pattern not found in {PYPROJECT_FILE}")
            return

        current_version = match.group(2)
        if current_version == version:
            print(f"Already up-to-date: {PYPROJECT_FILE} (version {version})")
        else:
            # Perform replacement
            new_content = re.sub(
                pattern, rf'\1"{version}"', content, count=1, flags=re.MULTILINE
            )
            PYPROJECT_FILE.write_text(new_content)
            print(f"Updated {PYPROJECT_FILE} from {current_version} to {version}")

    except Exception as e:
        print(f"Error processing {PYPROJECT_FILE}: {e}")


def update_helm_chart(version: str):
    """Updates the version and appVersion in the Helm chart"""
    if not HELM_CHART_FILE.exists():
        print(f"Skipping: {HELM_CHART_FILE} not found.")
        return

    try:
        content = HELM_CHART_FILE.read_text()
        original_content = content
        updated_count = 0

        # Update 'version:' line (unquoted)
        # Looks for 'version:' followed by optional whitespace and the version number
        version_pattern = r"^(version:\s*)(\S+)"
        current_version_match = re.search(version_pattern, content, flags=re.MULTILINE)
        if current_version_match and current_version_match.group(2) != version:
            content = re.sub(
                version_pattern,
                rf"\g<1>{version}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            print(
                f"Updating 'version' in {HELM_CHART_FILE} from {current_version_match.group(2)} to {version}"
            )
            updated_count += 1
        elif current_version_match:
            print(f"Already up-to-date: 'version' in {HELM_CHART_FILE} is {version}")
        else:
            print(f"Warning: 'version:' pattern not found in {HELM_CHART_FILE}")

        # Update 'appVersion:' line — always normalized to a quoted value.
        app_version_pattern = r"^appVersion:.*$"
        app_version_line = f'appVersion: "{version}"'
        current_app_version_match = re.search(
            app_version_pattern, content, flags=re.MULTILINE
        )
        if not current_app_version_match:
            print(f"Warning: 'appVersion:' pattern not found in {HELM_CHART_FILE}")
        elif current_app_version_match.group(0) == app_version_line:
            print(
                f"Already up-to-date: 'appVersion' in {HELM_CHART_FILE} is \"{version}\""
            )
        else:
            content = re.sub(
                app_version_pattern, app_version_line, content, count=1, flags=re.MULTILINE
            )
            print(
                f"Updating 'appVersion' in {HELM_CHART_FILE} from "
                f"{current_app_version_match.group(0)!r} to \"{version}\""
            )
            updated_count += 1

        # Write back only if changes were made
        if content != original_content:
            HELM_CHART_FILE.write_text(content)
        elif updated_count == 0 and current_version_match and current_app_version_match:
            print(f"Already up-to-date: {HELM_CHART_FILE} (version {version})")

    except Exception as e:
        print(f"Error processing {HELM_CHART_FILE}: {e}")


def update_readme(version: str):
    """Updates pinned image tags and the helm --version example in README.md"""
    if not README_FILE.exists():
        print(f"Skipping: {README_FILE} not found.")
        return

    try:
        content = README_FILE.read_text()
        original_content = content
        # Pinned ghcr.io/forgeguard-ai/faster-whisper-server[-variant]:X.Y.Z tags —
        # release tags are plain X.Y.Z (no leading v); ':latest' is left alone.
        pattern = (
            r"(ghcr\.io/forgeguard-ai/faster-whisper-server[\w-]*):(v?\d+\.\d+\.\d+)"
        )
        matches = list(re.finditer(pattern, content))

        if not matches:
            print(f"Warning: Docker image tag pattern not found in {README_FILE}")
        elif any(m.group(2) != version for m in matches):
            content = re.sub(pattern, rf"\1:{version}", content)
            print(f"Updated Docker image tags in {README_FILE} to {version}")
        else:
            print(
                f"Already up-to-date: Docker image tags in {README_FILE} (version {version})"
            )

        # The `helm install ... --version X.Y.Z` example.
        helm_pattern = r"(--version )(\d+\.\d+\.\d+)"
        helm_matches = list(re.finditer(helm_pattern, content))
        if helm_matches and any(m.group(2) != version for m in helm_matches):
            content = re.sub(helm_pattern, rf"\g<1>{version}", content)
            print(f"Updated helm --version example in {README_FILE} to {version}")

        if content != original_content:
            README_FILE.write_text(content)

        if ":latest" in content:
            print(
                f"Warning: Found ':latest' tag in {README_FILE}. Consider updating manually if needed."
            )

    except Exception as e:
        print(f"Error processing {README_FILE}: {e}")


def update_webui_package(version: str):
    """Updates the version field in webui/package.json"""
    if not WEBUI_PACKAGE_FILE.exists():
        print(f"Skipping: {WEBUI_PACKAGE_FILE} not found.")
        return

    try:
        data = json.loads(WEBUI_PACKAGE_FILE.read_text())
        current_version = data.get("version")
        if current_version == version:
            print(f"Already up-to-date: {WEBUI_PACKAGE_FILE} (version {version})")
            return
        data["version"] = version
        WEBUI_PACKAGE_FILE.write_text(json.dumps(data, indent=2) + "\n")
        print(f"Updated {WEBUI_PACKAGE_FILE} from {current_version} to {version}")
    except Exception as e:
        print(f"Error processing {WEBUI_PACKAGE_FILE}: {e}")


def main():
    if not VERSION_FILE.exists():
        print(f"Error: {VERSION_FILE} not found.")
        return

    try:
        version = VERSION_FILE.read_text().strip()
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            print(
                f"Error: Invalid version format '{version}' in {VERSION_FILE}. Expected X.Y.Z"
            )
            return
    except Exception as e:
        print(f"Error reading {VERSION_FILE}: {e}")
        return

    print(f"Read version: {version} from {VERSION_FILE}")
    print("-" * 20)

    update_pyproject(version)
    update_helm_chart(version)
    update_readme(version)
    update_webui_package(version)

    print("-" * 20)
    print("Version update script finished.")


if __name__ == "__main__":
    main()
