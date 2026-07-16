"""OpenAI-compatible transcription and translation endpoints."""

import logging
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

from server import activity, config, model_manager
from server.model_status import require_model_ready

try:
    from faster_whisper.tokenizer import _LANGUAGE_CODES
except ImportError:  # private attribute — skip validation if it moves
    _LANGUAGE_CODES = None

LOGGER = logging.getLogger("faster_whisper_api")

# Inference routes are gated on model readiness at the router level: while the
# background warmup is running they return 503 model_warming instead of racing an
# unloaded backend. (Auth is applied a layer up, at include_router time in
# main.py, so a 401 for a missing key still beats the 503.)
router = APIRouter(dependencies=[Depends(require_model_ready)])

# Read the upload in bounded chunks so a large body is never buffered whole in RAM.
_CHUNK_SIZE = 1024 * 1024


# The model lifecycle lives in server.model_manager (load/unload/switch/persist).
# ``get_model`` stays exported here so existing call sites — and tests that patch
# ``server.transcription.get_model`` — keep working unchanged.
def get_model():
    """Thread-safe accessor for the resident model (delegates to model_manager)."""
    return model_manager.get_model()


async def _spool_upload(file: UploadFile, suffix: str) -> str:
    """Stream the upload to a temp file, enforcing the size cap. Returns the path."""
    # Fast path: reject up front when the client declared an oversized body.
    if config.MAX_UPLOAD_BYTES and file.size and file.size > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")

    written = 0
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    audio_path = tmp_file.name
    try:
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if config.MAX_UPLOAD_BYTES and written > config.MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Uploaded file is too large")
            tmp_file.write(chunk)
    except BaseException:
        # ANY failure (client disconnect/CancelledError included) must not leave
        # an orphaned temp file behind.
        tmp_file.close()
        _safe_remove(audio_path)
        raise
    tmp_file.close()
    return audio_path


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        LOGGER.warning("Unable to remove temporary file: %s", path)


def _run_inference(audio_path: str, language: Optional[str], prompt: Optional[str],
                   want_words: bool, task: str):
    """Blocking inference — the segments generator does the real work on iteration."""
    whisper_model = get_model()
    segments, info = whisper_model.transcribe(
        audio_path,
        task=task,
        beam_size=config.BEAM_SIZE,
        language=language,
        initial_prompt=prompt,
        vad_filter=config.ENABLE_VAD_FILTER,
        word_timestamps=want_words,
    )
    return list(segments), info


def _word_dicts(segment) -> Optional[List[dict]]:
    if not segment.words:
        return None
    return [
        {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
        for w in segment.words
    ]


def _subtitle_timestamp(seconds: float, decimal_sep: str) -> str:
    ms = round(seconds * 1000)
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milli = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal_sep}{milli:03d}"


def to_srt(segments) -> str:
    """SRT subtitle document (sequence number, HH:MM:SS,mmm cue times)."""
    return "\n".join(
        f"{i}\n"
        f"{_subtitle_timestamp(segment.start, ',')} --> "
        f"{_subtitle_timestamp(segment.end, ',')}\n"
        f"{segment.text.strip()}\n"
        for i, segment in enumerate(segments, start=1)
    )


def to_vtt(segments) -> str:
    """WebVTT subtitle document (WEBVTT header, HH:MM:SS.mmm cue times)."""
    body = "\n".join(
        f"{_subtitle_timestamp(segment.start, '.')} --> "
        f"{_subtitle_timestamp(segment.end, '.')}\n"
        f"{segment.text.strip()}\n"
        for segment in segments
    )
    return f"WEBVTT\n\n{body}"


async def _handle_audio_request(
    file: UploadFile,
    *,
    language: Optional[str],
    prompt: Optional[str],
    response_format: str,
    timestamp_granularities: Optional[List[str]],
    task: str,
):
    """Shared body for transcription (task=transcribe) and translation (task=translate)."""
    if response_format not in {"text", "json", "verbose_json", "srt", "vtt"}:
        raise HTTPException(status_code=400, detail="Unsupported response_format")

    if (
        language
        and _LANGUAGE_CODES is not None
        and language.lower() not in _LANGUAGE_CODES
    ):
        raise HTTPException(
            status_code=400, detail=f"Unsupported language: {language}"
        )

    wants_word_timestamps = (
        bool(timestamp_granularities) and "word" in timestamp_granularities
    )

    suffix = os.path.splitext(file.filename or "audio.wav")[1]
    audio_path = await _spool_upload(file, suffix)

    try:
        # Offload the blocking, CPU/GPU-bound inference off the event loop so
        # concurrent requests and the health probe are not stalled. The gate
        # bounds concurrency and feeds the /system activity meter; under heavy
        # load it sheds with a 503 instead of queueing without bound.
        try:
            async with activity.gate.slot():
                segment_list, info = await run_in_threadpool(
                    _run_inference,
                    audio_path,
                    language,
                    prompt,
                    wants_word_timestamps,
                    task,
                )
        except activity.QueueFullError as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": "queue_full", "message": str(exc), "type": "server_error"},
                headers={"Retry-After": "5"},
            ) from exc
        except activity.QueueTimeoutError as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": "queue_timeout", "message": str(exc), "type": "server_error"},
                headers={"Retry-After": "10"},
            ) from exc
        transcript = "".join(segment.text for segment in segment_list).strip()
        # Transcripts are sensitive PII: never logged unless LOG_INPUT_TEXT is
        # explicitly enabled (default off). Length/timing only, otherwise.
        if config.LOG_INPUT_TEXT:
            LOGGER.info("transcript (%s): %s", task, transcript)
        else:
            LOGGER.debug(
                "transcription complete (task=%s, chars=%d)", task, len(transcript)
            )

        # OpenAI: `text` is a raw text/plain body, not a JSON wrapper.
        if response_format == "text":
            return PlainTextResponse(transcript)

        if response_format == "srt":
            return PlainTextResponse(to_srt(segment_list))

        if response_format == "vtt":
            return PlainTextResponse(to_vtt(segment_list))

        if response_format == "json":
            return {"text": transcript}

        # verbose_json — full detail per the OpenAI schema. Word timings live
        # only in the flattened top-level `words` list (OpenAI segments carry
        # no per-word entries).
        return {
            "task": task,
            "language": info.language,
            "duration": info.duration,
            "text": transcript,
            "segments": [
                {
                    "id": segment.id,
                    "seek": segment.seek,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "tokens": segment.tokens,
                    "temperature": segment.temperature,
                    "avg_logprob": segment.avg_logprob,
                    "compression_ratio": segment.compression_ratio,
                    "no_speech_prob": segment.no_speech_prob,
                }
                for segment in segment_list
            ],
            **(
                {
                    "words": [
                        w
                        for segment in segment_list
                        for w in (_word_dicts(segment) or [])
                    ]
                }
                if wants_word_timestamps
                else {}
            ),
        }
    finally:
        _safe_remove(audio_path)


@router.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0.0),
    timestamp_granularities: Optional[List[str]] = Form(None),
    # The OpenAI wire name is `timestamp_granularities[]` (array-style form
    # field); FastAPI binds Form params by exact name, so accept both.
    timestamp_granularities_bracketed: Optional[List[str]] = Form(
        None, alias="timestamp_granularities[]"
    ),
):
    del model, temperature
    granularities = (timestamp_granularities or []) + (
        timestamp_granularities_bracketed or []
    )
    return await _handle_audio_request(
        file,
        language=language or config.DEFAULT_LANGUAGE,
        prompt=prompt,
        response_format=response_format,
        timestamp_granularities=granularities or None,
        task="transcribe",
    )


@router.post("/v1/audio/translations")
async def create_translation(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    prompt: Optional[str] = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0.0),
):
    # OpenAI's translation endpoint always translates into English and takes no
    # source `language` or `timestamp_granularities`; Whisper auto-detects the
    # source language when language is None.
    del model, temperature
    return await _handle_audio_request(
        file,
        language=None,
        prompt=prompt,
        response_format=response_format,
        timestamp_granularities=None,
        task="translate",
    )
