"""Model resolution and pin-table tests (no network, no model load)."""

import os

from server import provisioning


def test_baked_dir_used_when_model_bin_present(tmp_path):
    baked = tmp_path / "tiny"
    baked.mkdir()
    (baked / "model.bin").write_bytes(b"x")
    resolved = provisioning.resolve_model("tiny", str(tmp_path), None)
    assert resolved.source == "baked"
    assert resolved.model_path_or_id == str(baked)
    assert resolved.revision is None


def test_empty_baked_dir_falls_back_to_hub(tmp_path):
    """A dir without model.bin (e.g. a volume mounted over it) must not be handed
    to WhisperModel — fall through to a hub download instead."""
    (tmp_path / "tiny").mkdir()  # present but empty
    resolved = provisioning.resolve_model("tiny", str(tmp_path), None)
    assert resolved.source == "hub"
    assert resolved.model_path_or_id == "tiny"


def test_no_model_dir_uses_hub():
    resolved = provisioning.resolve_model("large-v3", "", None)
    assert resolved.source == "hub"
    assert resolved.model_path_or_id == "large-v3"
    # canonical Systran repo -> pinned revision applied
    assert resolved.revision == provisioning.PINNED_REVISIONS[
        "Systran/faster-whisper-large-v3"
    ]


def test_pin_applied_for_canonical_and_alias():
    rev = provisioning.PINNED_REVISIONS["Systran/faster-whisper-large-v3"]
    assert provisioning.resolve_revision("large-v3") == rev
    assert provisioning.resolve_revision("large") == rev  # alias resolves to same repo


def test_revision_override_wins():
    assert provisioning.resolve_revision("large-v3", "deadbeef") == "deadbeef"


def test_custom_repo_is_unpinned():
    assert provisioning.resolve_revision("my-org/custom-whisper-ct2") is None
    # non-Systran community repos are intentionally excluded from the pin table
    assert provisioning.resolve_revision("mobiuslabsgmbh/faster-whisper-large-v3-turbo") is None


def test_canonical_repo_lookup():
    assert provisioning.canonical_repo("small") == "Systran/faster-whisper-small"
    assert provisioning.canonical_repo("Systran/faster-whisper-tiny") == (
        "Systran/faster-whisper-tiny"
    )
    assert provisioning.canonical_repo("unknown-model") is None


def test_baked_model_dir_name_matches_size(tmp_path):
    """The baked dir must be <model_dir>/<size>, i.e. named exactly MODEL_SIZE."""
    for size in ("tiny", "small", "large-v3"):
        d = tmp_path / size
        d.mkdir()
        (d / "model.bin").write_bytes(b"x")
        resolved = provisioning.resolve_model(size, str(tmp_path), None)
        assert resolved.model_path_or_id == os.path.join(str(tmp_path), size)
