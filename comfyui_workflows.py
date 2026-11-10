"""
title: OI-ComfyUI-Workflows
author: Wolfgang Weber (WolfgangW77)
version: 0.13.2
license: MIT
description: Exposes every API-format workflow in a directory as its own
model. Controlled via flags in the prompt (--ar, --no, --steps ...),
optional translation of non-English prompts via Ollama. Serialises GPU
access with the Alpaka Ollama Log Proxy (v5.3+) via a slot mechanism.
requirements: aiohttp

Written with AI assistance (Claude by Anthropic); reviewed and maintained
by the author.

Version history
(before v0.4.0 there was no versioning - one file, overwritten continuously)

v0.4.0
- First versioned release
- Help (--help): commands additionally shown as copyable blocks

v0.4.1
- Copyable commands as inline fields instead of full-width blocks
- Error messages end with a hint to `--reset`

v0.5.0
- Markers can point at model files (PIPE_VAE:vae_name,
  PIPE_MODEL:unet_name, PIPE_CLIP:clip_name); a fragment of the name is
  enough, the pipe matches it against ComfyUI's option list
- Ambiguous or unknown names are reported instead of guessed

v0.6.0
- One shared validation stage (_normalize) for saving AND rendering:
  no more values that are accepted in one place and rejected in the other
- --ar is therefore validated when saving defaults as well

v0.7.0
- A flag without a value resets exactly that entry (permanently when
  saving, once when rendering); booleans now need an explicit value:
  --refine 1 / --refine 0
- Flag + "s" lists the possible values, a search term filters
  (--vaes, --models, --clips, --loras, --ars) - generated automatically
  from the workflow's markers
- Feedback when saving repaired (stayed empty if nothing was accepted)

v0.7.1
- Additions to the help output (--help): notes on refine and
  enablelora, copyable commands

v0.7.2
- Bug fix: an aspect ratio from the chat controls went to ComfyUI
  unvalidated ("1:1" instead of "1:1 (Square)") and made the job fail.
  All sources now pass through the same validation.
- Help: the note per marker depends on the data type
- Help: the copyable commands are derived from the workflow itself

v0.7.3
- Bug fix: Open WebUI describes attached files with an <attached_files>
  block inside the message text. That block silently ended up in the
  prompt (and thus in PIPE_PROMPT_RESULT). Such blocks are now removed
  before prompt and flags are separated.

v0.8.0
- If ComfyUI aborts during execution (typically a sporadic RuntimeError
  in the KSampler on first load), the pipe retries the job exactly once.
  If the second attempt fails as well, the usual error output follows.
  Can be disabled via the retry_on_error valve.

v0.8.1
- Fixed: v0.8.0 shipped the valve but the retry itself was missing from
  the released file.

v0.8.2
- Editing workflows run without a prompt again: attach an image and, if
  the workflow has an image input, the image alone is enough.
  (Since v0.7.3 an empty text remained after stripping the
  <attached_files> block, and the pipe showed the help instead.)
- Error output: long tracebacks are now clipped in the middle instead of
  at the end - the actual cause is at the very bottom.

v0.8.3
- Bug fix: image uploads were always named the same (owui_upload_1.png)
  and uploaded with overwrite=true. With several jobs queued, every new
  upload overwrote the file of the jobs still waiting - when executed,
  all of them read the most recently uploaded image. Every job now gets
  a unique file name (timestamp + random part); which one it was is
  shown in the info line as before (Bild: ...).

v0.9.0
- The system prompt of the workspace model (Open WebUI: edit model ->
  System Prompt) is prepended to the prompt permanently. Typed text
  extends it ("system prompt, typed text"); without typed text the
  system prompt is used on its own - for editing workflows the attached
  image is then enough. The combined text passes through translation
  and trigger words as usual.
- Flags (--...) inside the system prompt are not evaluated; they end up
  literally in the image prompt - persistent defaults still belong in a
  flags-only message.

v0.10.0
- Chats without a typed prompt (image only, possibly a system prompt)
  now get a title in the format "YYYYMMDD HH:MM model name". The pipe
  sets it itself via Open WebUI's internal chat storage, because the
  usual title fallback (first message = title) stays empty for empty
  text. Chats WITH a typed prompt are left untouched.
- The model name comes from the metadata (display name of the workspace
  model, so variants work too), falling back to the workflow name.
- If setting the title fails, the image job continues normally; the
  reason is shown in the info line (show_prompt on). The time comes from
  the container clock - if that runs on UTC, the title is off.

v0.10.1
- The automatic title is only set if the chat has none yet. Empty
  string and Open WebUI's placeholders "New Chat" / "Neuer Chat" count
  as "no title". Custom titles and previously set timestamps are kept
  (v0.10.0 overwrote on every job without a typed prompt).
- The info line now distinguishes "Titel gesetzt" (set), "Titel
  behalten" (kept) and "Titel nicht gesetzt (reason)". If the title
  field cannot be read, nothing is set when in doubt.

v0.11.0
- The stop button in Open WebUI now reaches ComfyUI: when Open WebUI
  cancels the pipe (CancelledError in the polling loop), the pipe
  queries ComfyUI's queue and withdraws its own job - pending: deleted
  from the queue (POST /queue delete), running: interrupted
  (POST /interrupt). /interrupt is only fired if it is really our own
  prompt_id that is running, because it would otherwise hit another
  user's job.
- The cleanup runs through asyncio.shield with its own short connection
  (5 s) so that it completes even on a second cancel. If it fails,
  ComfyUI keeps rendering as before - nothing breaks.
- Status line after stopping: "Abgebrochen - ..." with the cleanup
  result instead of the misleading "Fertig in ...".
- Cancelling BEFORE the job is submitted (upload, translation) needs
  nothing on the ComfyUI side and stays as it was.

v0.11.1
- Comments, docstrings and version history translated to English for
  publication; MIT license notice added to the header. No functional
  change. User-facing texts (help, manual, status and error messages)
  remain in German.

v0.12.0
- Automatic aspect ratio from the attached image: for workflows with an
  image input (PIPE_IMAGE / LoadImage) the pipe reads the dimensions of
  the attached image and picks the aspect ratio closest to it - from the
  ResolutionSelector's option list if the workflow has one, otherwise
  directly as width:height for plain width/height nodes. Only applies
  when no --ar was given (message or saved defaults); an explicit --ar
  always wins, and so does the image over the aspect_ratio user valve.
  Switchable: admin valve auto_ar_from_image (global), user valve
  auto_ar, flag --arauto 0/1 (message or saved default). The info line
  marks the result with "(aus Bild WxH)".
- Image dimensions are read from the file header (PNG, JPEG, WebP) with
  Pillow as the first choice if available; no new dependency.

v0.12.1
- Open WebUI's memory feature appends a <memory_context>...</memory_context>
  block to the system message (utils/memory.py, present since 0.11.0).
  The pipe prepends the system message to the image prompt, so the
  memories ended up in the prompt unless memory was switched off per
  model. The block is now stripped like the other wrapper blocks; the
  info line reports it ("Gedächtnis-Block aus dem Systemprompt entfernt").

v0.12.2
- New marker PIPE_INTERNAL: a node with this title prefix is removed
  from the job before it is sent to ComfyUI. Meant for preview/debug
  outputs (e.g. a depth-map preview) that belong in the ComfyUI canvas
  but not in the chat - ComfyUI does not even compute them. Only nodes
  no other node depends on may be marked; otherwise the node stays in
  the job and --help shows a warning. --help lists the removed nodes.

v0.12.3
- Fix: --help failed with a KeyError (e.g. '30:62') on workflows with a
  PIPE_INTERNAL node. The node is removed from the job right after the
  analysis, but the help text looked it up in the job again. The class
  type is now recorded during the analysis instead.

v0.12.4
- Open WebUI's Context Compaction (Admin Settings -> Interface, since
  0.10.2) writes the chat summary into the system message, prefixed
  with "[CONVERSATION SUMMARY]" - either replacing the model's system
  prompt or appended to it (open-webui issue #26710). The pipe treated
  it as a system prompt and prepended the whole summary to the image
  prompt. Everything from the marker to the end of the system message
  is now discarded; text before it (the real system prompt, in the
  "appended" case) survives. If nothing is left, the next system
  message is checked. The info line reports it ("Chat-Zusammenfassung
  (Context Compaction) aus dem Systemprompt entfernt").
- Image rendering itself was never affected: the pipe only reads the
  last user message, and compaction only summarises older ones.

v0.13.0
- GPU slot client for the Alpaka Ollama Log Proxy (v5.3+), per the slot
  specification: before the translation step the pipe acquires the GPU
  slot at POST /proxy/acquire (blocking long-poll, label = workflow
  name, tag = chat id) and holds it across translation, ComfyUI job and
  rendering; released in every end path (success, error, timeout, stop
  button) from the pipe() wrapper, so no path can leak a slot. While
  waiting, the pipe polls /proxy/status and shows its queue position
  ("wartet auf freie GPU — Position N"); a user abort simply cancels
  the acquire request and Alpaka's socket peek removes the entry.
  Waiting does NOT count against timeout_seconds. A background task
  sends a heartbeat every 10 s from grant to release; if the lease is
  reported unknown (e.g. Alpaka restart), the job continues and the
  info line notes it - no re-acquire. Uploads and option queries run
  BEFORE the slot is taken (they need no GPU).
- Translation requests carry the smuggled marker x_owui_slot with the
  slot id, so Alpaka forwards them immediately although the slot holder
  is the pipe itself.
- New admin valves: proxy_url (Alpaka base URL), use_alpaka_proxy
  (off = behave like v0.12.4, e.g. environments without Alpaka;
  Alpaka unreachable while ON gives a clear error instead of silently
  rendering without the gate) and unload_ollama_before_job (after the
  grant, POST /proxy/unload evicts all loaded Ollama models before the
  image job - costs the reload of the chat model afterwards, saves the
  driver's VRAM eviction; default off).
- Admin clean-up flags --kill-ollama-tasks and --unload-ollama [name]:
  thin remote controls for Alpaka's admin endpoints, handled locally
  like --help (no slot, no translation, no ComfyUI job - the emergency
  broom must not wait in the very queue it is meant to sweep). They
  only need proxy_url and work with use_alpaka_proxy off; restricted to
  the OWUI role "admin" and listed in --help/--anleitung for admins
  only. Flag names may contain hyphens now (FLAG_RE extended).

v0.13.1
- timeout_seconds is now a pure compute cap and 0 disables it: the
  history loop stops capping, mirroring the removal of Alpaka's queue
  timeout — the user sees the elapsed time and has the stop button.
  Transport timeouts are hard-coded instead of riding on the valve
  (connect 10 s, sock_read 120 s): they detect a dead socket, they do
  not give up on a long render, and they stay active at 0.
- New valve unload_comfy_after_job (default off): after a finished
  image job — success, ComfyUI error or user abort, but not on a
  compute-cap timeout, where the job may still be running — the pipe
  POSTs ComfyUI's native /free with unload_models + free_memory, so
  the GPU is handed back clean BEFORE the slot is released and the
  returning chat model does not trigger the reverse VRAM eviction.
  Costs the checkpoint reload on the next image job.
- New admin flag --unload-comfy: manual counterpart, same /free call,
  handled pipe-locally like the other clean-up flags (admin role only,
  needs only comfy_url). The broom cupboard is now complete:
  --kill-ollama-tasks (running Ollama work), --unload-ollama (Ollama
  VRAM), --unload-comfy (ComfyUI VRAM).

v0.13.2
- The automatic VRAM clean-up moves to Alpaka v5.4 ("clean handover"):
  freeing the other side's memory belongs right BEFORE the task that
  needs it, not after the one that used it — an image series would
  otherwise evict its own checkpoint between two renders, and only the
  proxy sees chats coming. The valves unload_ollama_before_job and
  unload_comfy_after_job are removed; configure CLEAN_HANDOVER
  ("off"/"on"/"custom" with two per-direction sub-switches) in the
  proxy instead. The manual admin flags (--kill-ollama-tasks,
  --unload-ollama, --unload-comfy) stay in the pipe unchanged.
- New admin flags for Alpaka's clean handover (switch it from the
  chat, no proxy restart): --handover shows the current state,
  --handover on|off|custom sets the mode, --handover-comfy 0/1 and
  --handover-ollama 0/1 set the per-direction switches (which flips
  the mode to "custom" automatically, proxy-side). Handled
  pipe-locally like the other admin flags; the proxy persists changes
  in alpaka_settings.json.
"""

import asyncio
import base64
import inspect
import json
import math
import random
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional

import aiohttp
from pydantic import BaseModel, Field

WORKFLOW_DIR = Path("/app/backend/data/comfy_workflows")
DEFAULTS_FILE = Path("/app/backend/data/comfy_pipe_defaults.json")

# Node titles you assign in ComfyUI
TITLE_PROMPT = "PIPE_PROMPT"
TITLE_NEGATIVE = "PIPE_NEGATIVE"
TITLE_IMAGE = "PIPE_IMAGE"
TITLE_LOCK = "PIPE_LOCK"
TITLE_RESULT = "PIPE_PROMPT_RESULT"
TITLE_INTERNAL = "PIPE_INTERNAL"  # node is dropped from the job (dead ends only)
TITLE_PREFIX = "PIPE_"

DEFAULT_TRANSLATE_SYSTEM = (
    "You are a translator. The text you receive is an image generation prompt in any "
    "language. Always output an English version of it, even if parts are already "
    "English. Keep every subject, action, colour, material and spatial relation. Add "
    "nothing, remove nothing, explain nothing, do not comment. Leave any marker of the "
    "form <<0>>, <<1>> exactly as it is. Output only the English text, on one line."
)

# Nodes recognised by their class_type: class_type -> input field
SEED_FIELDS = {
    "RandomNoise": "noise_seed",
    "KSampler": "seed",
    "KSamplerAdvanced": "noise_seed",
    "SamplerCustom": "noise_seed",
}
STEP_FIELDS = {
    "BasicScheduler": "steps",
    "KSampler": "steps",
    "KSamplerAdvanced": "steps",
}
LATENT_TYPES = {"EmptyLatentImage", "EmptySD3LatentImage", "EmptyLatentImagePresets"}
LORA_TYPES = {"LoraLoader", "LoraLoaderModelOnly"}
MODEL_EXTS = (".safetensors", ".gguf", ".ckpt", ".pt", ".sft", ".bin")
IMAGE_OUTPUT_TYPES = {
    "SaveImage",
    "PreviewImage",
    "SaveImageWebsocket",
    "SaveAnimatedWEBP",
    "SaveAnimatedPNG",
    "Image Save",
    "SaveImageExtended",
}
CFG_FIELDS = {"CFGGuider": "cfg", "KSampler": "cfg", "KSamplerAdvanced": "cfg"}

# Blocks that Open WebUI itself writes into the message text (for example
# the description of attached files). They do not belong in the prompt.
WRAPPER_TAGS = (
    "attached_files",
    "context",
    "source",
    "files",
    "file",
    "chat_history",
    "user_context",
    "memory_context",  # Open WebUI memory feature, appended to the system message
)
WRAPPER_RE = re.compile(
    r"<("
    + "|".join(WRAPPER_TAGS)
    + r")\b[^>]*>.*?</\1\s*>|<(?:"
    + "|".join(WRAPPER_TAGS)
    + r")\b[^>]*/?>",
    re.S | re.I,
)

# Open WebUI's Context Compaction puts the chat summary into the system
# message with this prefix. Not an XML block, so handled separately.
COMPACTION_MARKER = "[CONVERSATION SUMMARY]"


def _strip_wrappers(text: str) -> str:
    """Remove the XML blocks inserted by Open WebUI from the raw text."""
    cleaned = WRAPPER_RE.sub(" ", text)
    return re.sub(r"[ \t]*\n[ \t]*\n+", "\n\n", cleaned).strip()


FLAG_RE = re.compile(r"(?:--|[\u2013\u2014])\s*([a-zA-Z][a-zA-Z0-9_-]*)")

# Flags that print something instead of rendering - they need no prompt
COMMAND_FLAGS = {
    "help",
    "loras",
    "reset",
    "anleitung",
    "kill-ollama-tasks",
    "unload-ollama",
    "unload-comfy",
    "handover",
    "handover-comfy",
    "handover-ollama",
}  # admin clean-up + handover

# Chat titles that count as "no title yet" (compared in lower case)
EMPTY_TITLES = {"", "new chat", "neuer chat"}


_RESET_HINT = (
    "\n\nHäufige Ursache sind gespeicherte Vorgaben, die nicht mehr zum Workflow "
    "passen — etwa LoRA-Slots nach einem Umbau. Zum Aufräumen abschicken: `--reset`"
)


def _clip_middle(text: str, limit: int = 2600) -> str:
    """Clip long output in the middle. In tracebacks the actual cause is at
    the very bottom - exactly the part that used to be cut off."""
    if len(text) <= limit:
        return text
    head = int(limit * 0.45)
    tail = limit - head
    return (
        text[:head]
        + f"\n\n… [{len(text) - limit} Zeichen ausgelassen] …\n\n"
        + text[-tail:]
    )


def _duration(seconds: float) -> str:
    """Make seconds readable: '8,4 s' or '2:05 min'."""
    if seconds < 60:
        return f"{seconds:.1f} s".replace(".", ",")
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes}:{rest:02d} min"


def _combo_options(spec) -> list[str]:
    """Extract the selectable values from an object_info entry.

    ComfyUI returns two formats:
      old : [["16:9 (Widescreen)", "1:1 (Square)", ...], {...}]
      new : ["COMBO", {"options": ["16:9 (Widescreen)", ...]}]
    Without this distinction the type name "COMBO" is read as a list
    and falls apart into its letters.
    """
    if not isinstance(spec, (list, tuple)) or not spec:
        return []
    first = spec[0]
    if isinstance(first, (list, tuple)):
        return [str(o) for o in first]
    for part in spec[1:]:
        if isinstance(part, dict):
            opts = part.get("options")
            if isinstance(opts, (list, tuple)):
                return [str(o) for o in opts]
    return []


def _text_field(inputs: dict) -> str:
    """Find the input field the prompt text belongs in.

    Nodes name it differently (text, value, prompt, instruction ...), so try
    the known names first, then the first unconnected string input.
    """
    for candidate in ("text", "value", "prompt", "instruction", "string", "caption"):
        if isinstance(inputs.get(candidate), str):
            return candidate
    for key, value in inputs.items():
        if isinstance(value, str):
            return key
    return "text"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _node_sort_key(node_id: str):
    """Sorts '30:3' before '49' and both before 'abc' - as close to graph order as possible."""
    parts = node_id.split(":")
    try:
        return (0, [int(p) for p in parts])
    except ValueError:
        return (1, [node_id])


class Pipe:
    class Valves(BaseModel):
        comfy_url: str = Field(
            default="http://host.docker.internal:8189",
            description="Basis-URL der ComfyUI-Instanz, ohne abschließenden Schrägstrich.",
        )
        timeout_seconds: int = Field(
            default=900,
            description=(
                "Rechen-Deckel ab Auftragsübermittlung; 0 = kein Deckel "
                "(dann zählen nur Stopp-Knopf und die festen "
                "Transport-Timeouts)."
            ),
        )
        max_batch: int = Field(
            default=8, description="Obergrenze für --batch, schützt vor VRAM-Unfällen."
        )
        retry_on_error: bool = Field(
            default=True,
            description=(
                "Bei einem Ausführungsfehler von ComfyUI den Auftrag genau einmal "
                "wiederholen. Hilft gegen sporadische Abbrüche im KSampler. Aus = "
                "Fehler sofort anzeigen."
            ),
        )
        store_images_as_files: bool = Field(
            default=True,
            description=(
                "Bilder in Open WebUIs Dateiablage speichern und nur verlinken, statt sie "
                "als Base64 in die Nachricht zu schreiben. Fällt bei Problemen automatisch "
                "auf Base64 zurück."
            ),
        )
        ollama_url: str = Field(
            default="http://host.docker.internal:11434",
            description="Ollama-Basis-URL für die Prompt-Übersetzung.",
        )
        proxy_url: str = Field(
            default="http://host.docker.internal:11435",
            description=(
                "Basis-URL des Alpaka-Proxys (Slot- und Aufräum-Endpunkte), "
                "ohne abschließenden Schrägstrich."
            ),
        )
        use_alpaka_proxy: bool = Field(
            default=True,
            description=(
                "Vor jedem Bildauftrag einen GPU-Slot beim Alpaka-Proxy (v5.3+) "
                "ziehen, damit sich Bild- und Chat-Aufträge nicht um die GPU "
                "prügeln. Aus = Verhalten wie v0.12.4 (für Umgebungen ohne "
                "Alpaka). Ist Alpaka bei aktivem Schalter nicht erreichbar, "
                "gibt es eine klare Fehlermeldung statt stillem Direktbetrieb."
            ),
        )
        translate_model: str = Field(
            default="",
            description="Ollama-Modell für die Übersetzung. Leer = Übersetzung nicht verfügbar.",
        )
        translate_keep_alive: str = Field(
            default="5m",
            description="Wie lange das Übersetzungsmodell im VRAM bleibt. '0' lädt es sofort wieder aus.",
        )
        translate_system: str = Field(
            default=DEFAULT_TRANSLATE_SYSTEM,
            description="Systemanweisung für die Übersetzung.",
        )
        lora_triggers: str = Field(
            default="",
            description=(
                "Triggerwörter je LoRA, eine Zeile pro Eintrag im Format "
                "'teil_des_dateinamens | triggerwort'. Wird nach der Übersetzung angehängt, "
                "aber nur für LoRAs mit Stärke ungleich 0."
            ),
        )
        auto_ar_from_image: bool = Field(
            default=True,
            description=(
                "Bei Workflows mit Bildeingang das Seitenverhältnis automatisch aus dem "
                "angehängten Bild ableiten, wenn kein --ar angegeben ist. Aus = Funktion "
                "für alle Benutzer abgeschaltet."
            ),
        )

    class UserValves(BaseModel):
        aspect_ratio: str = Field(
            default="",
            description="Standard-Seitenverhältnis, z.B. 16:9. Leer = wie im Workflow.",
        )
        megapixels: float = Field(
            default=0.0, description="Bildgröße in Megapixeln. 0 = wie im Workflow."
        )
        batch_size: int = Field(
            default=0, description="Bilder pro Anfrage. 0 = wie im Workflow."
        )
        steps: int = Field(
            default=0, description="Sampler-Schritte. 0 = wie im Workflow."
        )
        seed: int = Field(default=-1, description="Fester Seed. -1 = jedes Mal neu.")
        translate: bool = Field(
            default=False,
            description="Prompt vor dem Rendern ins Englische übersetzen lassen.",
        )
        show_prompt: bool = Field(
            default=False,
            description="Verwendete Einstellungen unter das Bild schreiben.",
        )
        auto_ar: bool = Field(
            default=True,
            description=(
                "Seitenverhältnis aus dem angehängten Bild übernehmen, wenn kein --ar "
                "angegeben ist (nur Workflows mit Bildeingang)."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # Workflow directory
    # ------------------------------------------------------------------

    def _list_files(self) -> list[Path]:
        if not WORKFLOW_DIR.is_dir():
            return []
        return sorted(p for p in WORKFLOW_DIR.glob("*.json") if p.is_file())

    def pipes(self):
        files = self._list_files()
        if not files:
            return [
                {
                    "id": "no-workflows",
                    "name": f"ComfyUI (keine Workflows in {WORKFLOW_DIR})",
                }
            ]
        return [{"id": _slug(p.stem), "name": p.stem} for p in files]

    def _load(self, pipe_id: str) -> tuple[dict, str]:
        for path in self._list_files():
            if _slug(path.stem) == pipe_id:
                stat = path.stat().st_mtime
                cached = self._cache.get(pipe_id)
                if not cached or cached[0] != stat:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if "nodes" in data and "links" in data:
                        raise ValueError(
                            f"'{path.name}' ist im UI-Format gespeichert. "
                            "In ComfyUI bitte über 'Workflow -> Export (API)' exportieren."
                        )
                    self._cache[pipe_id] = (stat, data)
                return json.loads(json.dumps(self._cache[pipe_id][1])), path.stem
        raise ValueError(f"Kein Workflow mit der Kennung '{pipe_id}' gefunden.")

    # ------------------------------------------------------------------
    # Finding nodes in the workflow
    # ------------------------------------------------------------------

    def _analyze(self, wf: dict) -> dict:
        h: dict = {"loras": [], "markers": {}, "internal": [], "internal_types": {}}

        # PIPE_INTERNAL first: such nodes must not register as outputs,
        # LoRA slots or markers below. A node that another node depends
        # on cannot be dropped - it stays, with a note for --help.
        for node_id in sorted(wf.keys(), key=_node_sort_key):
            title = (wf[node_id].get("_meta") or {}).get("title", "")
            if not title.startswith(TITLE_INTERNAL):
                continue
            dependants = [
                other_id
                for other_id, other in wf.items()
                if other_id != node_id
                and any(
                    isinstance(v, list) and v and str(v[0]) == str(node_id)
                    for v in other.get("inputs", {}).values()
                )
            ]
            if dependants:
                h.setdefault("marker_errors", []).append(
                    f"Knoten {node_id} ({wf[node_id].get('class_type', '?')}) ist als "
                    f"{TITLE_INTERNAL} markiert, aber Knoten "
                    f"{', '.join(dependants)} hängen davon ab — bleibt im Auftrag"
                )
            else:
                h["internal"].append(node_id)
                h["internal_types"][node_id] = wf[node_id].get("class_type", "?")

        for node_id in sorted(wf.keys(), key=_node_sort_key):
            if node_id in h["internal"]:
                continue
            node = wf[node_id]
            ctype = node.get("class_type", "")
            title = (node.get("_meta") or {}).get("title", "")
            inputs = node.get("inputs", {})

            if title == TITLE_PROMPT:
                h["prompt"] = (node_id, _text_field(inputs))
            elif title == TITLE_NEGATIVE:
                h["negative"] = (node_id, _text_field(inputs))
            elif title == TITLE_RESULT:
                h["prompt_result"] = node_id
            elif title == TITLE_IMAGE:
                h["image"] = (
                    node_id,
                    "image" if "image" in inputs else next(iter(inputs), "image"),
                )
            elif title.startswith(TITLE_LOCK):
                pass  # just a lock marker, no flag
            elif title.startswith(TITLE_PREFIX):
                # "PIPE_BOOST:ref_boost" addresses exactly that field,
                # "PIPE_REFINE" takes the first unconnected field of the node
                rest = title[len(TITLE_PREFIX) :].strip()
                name, _, wanted = rest.partition(":")
                name = name.strip().lower()
                wanted = wanted.strip()
                field = None
                if (
                    wanted
                    and not isinstance(inputs.get(wanted), list)
                    and wanted in inputs
                ):
                    field = wanted
                elif wanted:
                    field = (
                        None  # field does not exist: marker is dropped, note in --help
                    )
                    h.setdefault("marker_errors", []).append(
                        f"Knoten {node_id}: Feld '{wanted}' existiert nicht "
                        f"(vorhanden: {', '.join(k for k, v in inputs.items() if not isinstance(v, list)) or 'keine'})"
                    )
                elif "value" in inputs and not isinstance(inputs["value"], list):
                    field = "value"
                else:
                    for k, v in inputs.items():
                        if not isinstance(v, list):
                            field = k
                            break
                if name and field:
                    h["markers"][name] = (node_id, field)

            if ctype in SEED_FIELDS and "seed" not in h:
                field = SEED_FIELDS[ctype]
                if field in inputs:
                    h["seed"] = (node_id, field)
            if ctype in STEP_FIELDS and "steps" not in h:
                if STEP_FIELDS[ctype] in inputs:
                    h["steps"] = (node_id, STEP_FIELDS[ctype])
            if ctype in LATENT_TYPES and "latent" not in h:
                h["latent"] = node_id
            if (
                not isinstance(inputs.get("width"), list)
                and not isinstance(inputs.get("height"), list)
                and isinstance(inputs.get("width"), (int, float))
                and isinstance(inputs.get("height"), (int, float))
            ):
                # Width/height can have several consumers - e.g. the latent AND
                # ModelSamplingFlux, which derives its shift from them.
                h.setdefault("dimension_nodes", []).append(node_id)
            if ctype == "ResolutionSelector" and "resolution" not in h:
                h["resolution"] = node_id
            if ctype == "FluxGuidance" and "guidance" not in h:
                h["guidance"] = (node_id, "guidance")
            if ctype in CFG_FIELDS and "cfg" not in h:
                if CFG_FIELDS[ctype] in inputs:
                    h["cfg"] = (node_id, CFG_FIELDS[ctype])
            if ctype in LORA_TYPES:
                if title.startswith(TITLE_LOCK):
                    h.setdefault("locked_loras", []).append(node_id)
                else:
                    h["loras"].append(node_id)
            if ctype == "LoadImage" and "image" not in h:
                h["image"] = (node_id, "image")
            if ctype in IMAGE_OUTPUT_TYPES:
                h.setdefault("outputs", []).append(node_id)

        # Fallback: locate the positive prompt via the guider/sampler
        if "prompt" not in h:
            for node in wf.values():
                pos = node.get("inputs", {}).get("positive")
                if isinstance(pos, list) and pos:
                    target = wf.get(str(pos[0]), {})
                    if target.get("class_type") == "CLIPTextEncode" and isinstance(
                        target.get("inputs", {}).get("text"), str
                    ):
                        h["prompt"] = (str(pos[0]), "text")
                    break
        return h

    # ------------------------------------------------------------------
    # Flags from the chat
    # ------------------------------------------------------------------

    def _parse_flags(self, text: str) -> tuple[str, dict]:
        matches = list(FLAG_RE.finditer(text))
        if not matches:
            return text.strip(), {}
        prompt = text[: matches[0].start()].strip()
        flags: dict = {}
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            flags[m.group(1).lower()] = text[m.end() : end].strip()
        return prompt, flags

    def _aspect(self, value: str) -> Optional[float]:
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[:x/]\s*(\d+(?:\.\d+)?)\s*$", value)
        if not m:
            return None
        w, hh = float(m.group(1)), float(m.group(2))
        return w / hh if hh else None

    async def _resolution_options(self, session, base: str) -> list[str]:
        try:
            async with session.get(f"{base}/object_info/ResolutionSelector") as r:
                info = await r.json()
            spec = info["ResolutionSelector"]["input"]["required"]["aspect_ratio"]
            return _combo_options(spec)
        except Exception:
            return []

    def _image_size(self, raw: bytes) -> Optional[tuple[int, int]]:
        """Pixel dimensions of an image file. Pillow first (present in Open
        WebUI), otherwise a minimal header parser for PNG, JPEG and WebP."""
        try:
            from PIL import Image as _Image
            import io as _io

            with _Image.open(_io.BytesIO(raw)) as im:
                w, hh = im.size
                # EXIF orientation 5-8 = rotated by 90 degrees: swap
                try:
                    if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):
                        w, hh = hh, w
                except Exception:
                    pass
                return (int(w), int(hh)) if w and hh else None
        except Exception:
            pass
        try:
            if raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR":
                return int.from_bytes(raw[16:20], "big"), int.from_bytes(
                    raw[20:24], "big"
                )
            if raw[:2] == b"\xff\xd8":
                i = 2
                while i + 9 < len(raw):
                    if raw[i] != 0xFF:
                        i += 1
                        continue
                    marker = raw[i + 1]
                    if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                        i += 2
                        continue
                    length = int.from_bytes(raw[i + 2 : i + 4], "big")
                    if marker in (
                        0xC0,
                        0xC1,
                        0xC2,
                        0xC3,
                        0xC5,
                        0xC6,
                        0xC7,
                        0xC9,
                        0xCA,
                        0xCB,
                        0xCD,
                        0xCE,
                        0xCF,
                    ):
                        hh = int.from_bytes(raw[i + 5 : i + 7], "big")
                        w = int.from_bytes(raw[i + 7 : i + 9], "big")
                        return (w, hh) if w and hh else None
                    i += 2 + length
            if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                chunk = raw[12:16]
                if chunk == b"VP8X":
                    w = 1 + int.from_bytes(raw[24:27], "little")
                    hh = 1 + int.from_bytes(raw[27:30], "little")
                    return w, hh
                if chunk == b"VP8L":
                    b = raw[21:25]
                    w = 1 + (b[0] | ((b[1] & 0x3F) << 8))
                    hh = 1 + ((b[1] >> 6) | (b[2] << 2) | ((b[3] & 0x0F) << 10))
                    return w, hh
                if chunk == b"VP8 ":
                    w = int.from_bytes(raw[26:28], "little") & 0x3FFF
                    hh = int.from_bytes(raw[28:30], "little") & 0x3FFF
                    return (w, hh) if w and hh else None
        except Exception:
            pass
        return None

    def _nearest_ratio_option(
        self, options: list[str], width: int, height: int
    ) -> Optional[str]:
        """The ResolutionSelector entry whose ratio is closest to
        width:height (compared on a log scale, so 2:1 and 1:2 are equally
        far from 1:1)."""
        target = math.log(width / height)
        best, best_d = None, None
        for opt in options:
            ratio = self._aspect(opt.split(" ")[0])
            if not ratio:
                continue
            d = abs(math.log(ratio) - target)
            if best_d is None or d < best_d:
                best, best_d = opt, d
        return best

    # ------------------------------------------------------------------
    # Setting values
    # ------------------------------------------------------------------

    def _coerce(self, text: str, current):
        raw = text.strip()
        low = raw.lower()
        if isinstance(current, bool):
            return low in ("1", "true", "on", "an", "ja", "yes", "y")
        if isinstance(current, int):
            try:
                return int(float(low.replace(",", ".")))
            except ValueError:
                return current
        if isinstance(current, float):
            try:
                return float(low.replace(",", "."))
            except ValueError:
                return current
        return raw

    async def _translate(
        self, session, text: str, slot_id: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        v = self.valves
        url = v.ollama_url.rstrip("/") + "/api/generate"
        base = {
            "model": v.translate_model,
            "stream": False,
            "keep_alive": v.translate_keep_alive,
            "options": {"temperature": 0.2},
        }
        if slot_id:
            # v0.13.0: mark the request as belonging to the slot holder -
            # Alpaka forwards it immediately despite the held slot and
            # strips the marker before Ollama sees it.
            base["x_owui_slot"] = slot_id
        # Anchor format: small models otherwise tend to echo the input back
        anchored = f"Text:\n{text}\n\nEnglish:"
        # Order of attempts:
        # 1. with thinking switched off (saves a lot of time on reasoning models)
        # 2. without the think field, in case the model has no thinking (Ollama then answers with an error)
        # 3. instruction inside the prompt instead of the system role, in case the template has none
        attempts = [
            {**base, "prompt": anchored, "system": v.translate_system, "think": False},
            {**base, "prompt": anchored, "system": v.translate_system},
            {**base, "prompt": f"{v.translate_system}\n\n{anchored}"},
        ]
        last_err = None
        for payload in attempts:
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        last_err = f"HTTP {resp.status}"
                        continue
                    data = await resp.json()
            except Exception as e:
                last_err = str(e)
                continue
            out = data.get("response", "")
            out = re.sub(r"<think>.*?</think>", "", out, flags=re.S)
            out = out.strip().strip('"').strip()
            if out:
                return out, None
            last_err = "leere Antwort"
        return None, last_err

    def _protect(self, text: str) -> tuple[str, list[str]]:
        """Keep text in double quotes out of the translation."""
        for ch in ("\u201c", "\u201d", "\u201e", "\u00ab", "\u00bb"):
            text = text.replace(ch, '"')
        kept: list[str] = []

        def swap(m):
            kept.append(m.group(1))
            return f"<<{len(kept) - 1}>>"

        return re.sub(r'"([^"]+)"', swap, text), kept

    def _restore(self, text: str, kept: list[str]) -> str:
        for i, original in enumerate(kept):
            token = f"<<{i}>>"
            if token in text:
                text = text.replace(token, f'"{original}"')
            else:
                # The placeholder does not always survive - then append at the end
                text = f'{text}, "{original}"'
        return re.sub(r"<<\d+>>", "", text).strip()

    def _triggers_for(self, wf: dict, h: dict) -> list[str]:
        mapping = []
        for line in self.valves.lora_triggers.splitlines():
            if "|" in line:
                frag, trig = line.split("|", 1)
                frag, trig = frag.strip().lower(), trig.strip()
                if frag and trig:
                    mapping.append((frag, trig))
        if not mapping:
            return []
        out: list[str] = []
        for nid in h["loras"]:
            inputs = wf[nid]["inputs"]
            if not inputs.get("strength_model"):
                continue
            name = str(inputs.get("lora_name", "")).lower()
            for frag, trig in mapping:
                if frag in name and trig not in out:
                    out.append(trig)
        return out

    async def _lora_options(self, session, base: str) -> list[str]:
        """Query the available LoRA files from ComfyUI."""
        found: list[str] = []
        for node_type in ("LoraLoader", "LoraLoaderModelOnly"):
            try:
                async with session.get(f"{base}/object_info/{node_type}") as resp:
                    info = await resp.json()
                spec = info[node_type]["input"]["required"]["lora_name"]
            except Exception:
                continue
            for entry in _combo_options(spec):
                if entry not in found:
                    found.append(entry)
        return sorted(found)

    def _parse_lora_value(self, value: str) -> tuple[Optional[str], Optional[float]]:
        """'0.4' -> (None, 0.4) | 'cat_v1' -> ('cat_v1', None) | 'cat_v1:0.8' -> both."""
        raw = value.strip()
        if not raw:
            return None, None
        name, sep, tail = raw.rpartition(":")
        if sep:
            try:
                return (name.strip() or None), float(tail.replace(",", "."))
            except ValueError:
                pass
        try:
            return None, float(raw.replace(",", "."))
        except ValueError:
            return raw, None

    def _extract_images(self, body: dict) -> list:
        """Collect attached images as (bytes, file name) from the last message."""
        import base64 as _b64

        messages = body.get("messages") or []
        if not messages:
            return []
        content = messages[-1].get("content", "")
        found = []
        raw_urls = []
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "image_url":
                    url = part.get("image_url")
                    url = url.get("url") if isinstance(url, dict) else url
                    if url:
                        raw_urls.append(url)
        # Ollama style: list of base64 strings next to the text
        for entry in messages[-1].get("images") or []:
            if isinstance(entry, str):
                raw_urls.append(entry)

        # Unique name part per job (timestamp + random):
        # The file used to be called owui_upload_1.png every time and was
        # uploaded with overwrite=true. LoadImage only reads the file when
        # the job is executed, though - so jobs waiting in the queue all
        # ended up with the most recently uploaded image.
        uniq = time.strftime("%Y%m%d_%H%M%S") + f"_{random.randrange(16**4):04x}"

        for i, url in enumerate(raw_urls, start=1):
            if url.startswith("data:"):
                header, _, payload = url.partition(",")
                mime = header[5:].split(";")[0] or "image/png"
            else:
                continue  # external URLs are deliberately not fetched
            ext = {"image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
            try:
                found.append((_b64.b64decode(payload), f"owui_upload_{uniq}_{i}.{ext}"))
            except Exception:
                continue
        return found

    def _system_prompt(self, body: dict) -> tuple[str, bool, bool]:
        """Fetch the workspace model's system prompt from the messages.

        Assumption (Open WebUI default behaviour): the system prompt stored
        in the model is passed as a message with role 'system' at the start
        of the messages array. The first system message that still has
        content after cleaning is used.

        Two things Open WebUI itself puts into the system message are
        removed:
        - the <memory_context> block of the memory feature (wrapper tag)
        - the chat summary of Context Compaction, prefixed with
          "[CONVERSATION SUMMARY]": everything from the marker to the end
          of the message goes. It either REPLACES the model's system prompt
          (nothing is left, the next system message is tried) or is APPENDED
          to it (the real prompt before the marker survives).

        Returns: (system prompt without those parts, whether the memory
        block was present, whether a compaction summary was present).
        """
        had_memory = False
        had_summary = False
        for msg in body.get("messages") or []:
            if msg.get("role") != "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    p.get("text", "") for p in content if p.get("type") == "text"
                )
            content = str(content)
            if "<memory_context" in content:
                had_memory = True
            idx = content.lower().find(COMPACTION_MARKER.lower())
            if idx >= 0:
                had_summary = True
                content = content[:idx]
            cleaned = _strip_wrappers(content)
            if cleaned:
                return cleaned, had_memory, had_summary
        return "", had_memory, had_summary

    async def _upload_image(self, session, base: str, raw: bytes, filename: str):
        """Upload an image to ComfyUI. Returns: (reference, error text)."""
        import io as _io

        data = aiohttp.FormData()
        data.add_field(
            "image",
            _io.BytesIO(raw),
            filename=filename,
            content_type="application/octet-stream",
        )
        data.add_field("overwrite", "true")
        try:
            async with session.post(f"{base}/upload/image", data=data) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                info = await resp.json()
        except Exception as e:
            return None, str(e)
        name = info.get("name") or filename
        subfolder = info.get("subfolder") or ""
        return (f"{subfolder}/{name}" if subfolder else name), None

    async def _normalize(self, session, base: str, wf: dict, h: dict, values: dict):
        """Validate values against ComfyUI's option lists and bring them into
        their final form. Runs both when saving defaults AND when rendering, so
        there are no values that are accepted in one place and rejected in the
        other. Returns: (validated values, notes)."""
        out = dict(values)
        notes: list[str] = []

        # --- LoRA slots: name fragment -> full file name ---
        lora_options: Optional[list[str]] = None
        for i, nid in enumerate(h["loras"], start=1):
            key = f"lora{i}"
            if key not in out:
                continue
            fragment, strength = self._parse_lora_value(out[key])
            if fragment:
                if lora_options is None:
                    lora_options = await self._lora_options(session, base)
                if not lora_options:
                    notes.append(
                        f"--{key}: ComfyUI nicht erreichbar, '{fragment}' ungeprüft übernommen"
                    )
                else:
                    match, err = self._match_lora(fragment, lora_options)
                    if err:
                        notes.append(f"--{key}: {err} — Name nicht übernommen")
                        fragment = None
                    else:
                        fragment = match
            if fragment and strength is not None:
                out[key] = f"{fragment}:{strength}"
            elif fragment:
                out[key] = fragment
            elif strength is not None:
                out[key] = str(strength)
            else:
                out.pop(key)
                notes.append(f"--{key}: kein verwertbarer Wert")

        # --- Markers that point at a model file ---
        for marker_name, handle in h["markers"].items():
            if marker_name not in out:
                continue
            node_id, field = handle
            current = wf[node_id]["inputs"][field]
            if not (isinstance(current, str) and current.lower().endswith(MODEL_EXTS)):
                continue
            fragment = str(out[marker_name]).strip()
            if not fragment:
                out.pop(marker_name)
                continue
            options = await self._field_options(
                session, base, wf[node_id].get("class_type", ""), field
            )
            if not options:
                notes.append(
                    f"--{marker_name}: '{fragment}' ungeprüft übernommen "
                    "(keine Liste von ComfyUI)"
                )
                continue
            match, err = self._match_option(fragment, options, "Datei")
            if err:
                notes.append(f"--{marker_name}: {err} — nicht übernommen")
                out.pop(marker_name)
            else:
                out[marker_name] = match

        # --- Aspect ratio against the ResolutionSelector ---
        if "ar" in out and h.get("resolution"):
            wanted = str(out["ar"]).strip()
            if wanted:
                options = await self._resolution_options(session, base)
                if options:
                    match = next(
                        (
                            o
                            for o in options
                            if o == wanted or o.split(" ")[0] == wanted
                        ),
                        None,
                    )
                    if match:
                        out["ar"] = match
                    else:
                        notes.append(
                            f"--ar: Format {wanted} unbekannt — möglich wären: "
                            + ", ".join(o.split(" ")[0] for o in options)
                        )
                        out.pop("ar")
        return out, notes

    async def _normalize_standalone(self, wf: dict, h: dict, values: dict):
        """Like _normalize, but opens its own short connection."""
        base = self.valves.comfy_url.rstrip("/")
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                return await self._normalize(session, base, wf, h, values)
        except Exception as e:
            return dict(values), [
                f"ComfyUI nicht erreichbar ({e}) — ungeprüft gespeichert"
            ]

    def _merge_lora_value(self, old: str, new: str) -> str:
        """Merge name and strength separately: whatever the new value does not
        mention is kept from the old one."""
        old_name, old_strength = self._parse_lora_value(old or "")
        new_name, new_strength = self._parse_lora_value(new or "")
        name = new_name or old_name
        strength = new_strength if new_strength is not None else old_strength
        if name and strength is not None:
            return f"{name}:{strength}"
        if name:
            return name
        return str(strength) if strength is not None else ""

    def _match_option(self, fragment: str, options: list[str], was: str = "Datei"):
        """Map a fragment of a file name to exactly one entry of the option
        list. Returns: (match, error text)."""
        frag = fragment.lower()
        exact = [o for o in options if o.lower() == frag]
        if exact:
            return exact[0], None
        hits = [o for o in options if frag in o.lower()]
        if len(hits) == 1:
            return hits[0], None
        if not hits:
            return None, f"keine {was} passt auf '{fragment}'"
        shown = ", ".join(hits[:5])
        if len(hits) > 5:
            shown += f" … und {len(hits) - 5} weitere"
        return None, f"'{fragment}' passt auf mehrere ({len(hits)}): " + shown

    def _match_lora(self, fragment: str, options: list[str]):
        return self._match_option(fragment, options, "LoRA")

    async def _field_options(
        self, session, base: str, class_type: str, field: str
    ) -> list[str]:
        """Ask ComfyUI for the selectable values of an arbitrary node field."""
        try:
            async with session.get(f"{base}/object_info/{class_type}") as resp:
                info = await resp.json()
            spec = info[class_type]["input"]["required"][field]
        except Exception:
            return []
        return _combo_options(spec)

    async def _store_image(
        self, raw: bytes, filename: str, user_id: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Put an image into Open WebUI's file storage. Returns: (URL, error text)."""
        if not user_id:
            return None, "kein Benutzer bekannt"
        try:
            import io
            import uuid as _uuid

            from open_webui.models.files import FileForm, Files
            from open_webui.storage.provider import Storage
        except Exception as e:
            return None, f"interne Module nicht gefunden: {e}"
        try:
            file_id = str(_uuid.uuid4())
            safe = filename or "comfyui.png"
            _contents, path = Storage.upload_file(
                io.BytesIO(raw), f"{file_id}_{safe}", {}
            )
            await Files.insert_new_file(
                user_id,
                FileForm(
                    id=file_id,
                    filename=safe,
                    path=path,
                    meta={
                        "name": safe,
                        "content_type": "image/png",
                        "size": len(raw),
                    },
                ),
            )
            return f"/api/v1/files/{file_id}/content", None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    async def _set_chat_title(
        self, chat_id: Optional[str], title: str
    ) -> tuple[str, str]:
        """Set the chat title directly in Open WebUI's chat storage - but only
        if the chat has none yet (see EMPTY_TITLES).
        Returns: ("gesetzt", title) | ("behalten", existing title)
                 | ("fehler", reason)

        Assumptions (not verified against a running system): the module
        open_webui.models.chats provides a class Chats with get_chat_by_id
        and update_chat_title_by_id; older/other versions are covered via
        update_chat_by_id. Both sync and async variants are tolerated. If
        the existing title cannot be read, nothing is set when in doubt."""
        if not chat_id:
            return "fehler", "keine Chat-ID in den Metadaten"
        try:
            from open_webui.models.chats import Chats
        except Exception as e:
            return "fehler", f"interne Module nicht gefunden: {e}"

        async def _call(func, *args):
            result = func(*args)
            if inspect.isawaitable(result):
                result = await result
            return result

        missing = object()
        try:
            chat = await _call(Chats.get_chat_by_id, chat_id)
            if chat is None:
                return "fehler", "Chat nicht gefunden"
            existing = getattr(chat, "title", missing)
            if existing is missing and isinstance(chat, dict):
                existing = chat.get("title", missing)
            if existing is missing:
                return "fehler", "Titelfeld des Chats nicht gefunden - nichts geändert"
            existing = "" if existing is None else str(existing)
            if existing.strip().lower() not in EMPTY_TITLES:
                return "behalten", existing
            if hasattr(Chats, "update_chat_title_by_id"):
                await _call(Chats.update_chat_title_by_id, chat_id, title)
            else:
                # Fallback for versions without the direct title method
                data = dict(getattr(chat, "chat", None) or {})
                data["title"] = title
                await _call(Chats.update_chat_by_id, chat_id, data)
            return "gesetzt", title
        except Exception as e:
            return "fehler", f"{type(e).__name__}: {e}"

    def _defaults_key(self, user_id, pipe_id: str) -> str:
        return f"{user_id or 'anon'}::{pipe_id}"

    def _load_defaults(self, user_id, pipe_id: str) -> dict:
        try:
            data = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
            return dict(data.get(self._defaults_key(user_id, pipe_id), {}))
        except Exception:
            return {}

    def _save_defaults(self, user_id, pipe_id: str, values: dict):
        try:
            data = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        key = self._defaults_key(user_id, pipe_id)
        if values:
            data[key] = values
        else:
            data.pop(key, None)
        DEFAULTS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def _listers(self, h: dict, wf: dict) -> dict:
        """Build a listing flag for every flag that has an option list:
        --vae -> --vaes. Returns: name -> ("kind", payload)."""
        out: dict = {"loras": ("loras", None)}
        # Not via _known_flags, because that already contains the listing flags
        taken = {
            "help",
            "no",
            "seed",
            "steps",
            "cfg",
            "guidance",
            "batch",
            "ar",
            "mp",
            "translate",
            "triggers",
            "loras",
            "reset",
            "anleitung",
            "arauto",
        }
        taken |= {f"lora{i}" for i in range(1, len(h["loras"]) + 1)}
        taken |= set(h["markers"])
        for marker_name, handle in h["markers"].items():
            lister = marker_name + "s"
            if lister in taken or lister in out:
                continue  # name collision: no listing flag
            node_id, field = handle
            out[lister] = (
                "field",
                (wf[node_id].get("class_type", ""), field, marker_name),
            )
        if h.get("resolution") and "ars" not in taken:
            out["ars"] = ("resolution", None)
        return out

    def _known_flags(self, h: dict) -> set:
        known = {
            "help",
            "no",
            "seed",
            "steps",
            "cfg",
            "guidance",
            "batch",
            "ar",
            "mp",
            "translate",
            "triggers",
            "loras",
            "reset",
            "arauto",
            "kill-ollama-tasks",  # v0.13.0: admin clean-up
            "unload-ollama",  # v0.13.0: admin clean-up
            "unload-comfy",  # v0.13.1: admin clean-up
            "handover",  # v0.13.2: clean handover
            "handover-comfy",  # v0.13.2: clean handover
            "handover-ollama",  # v0.13.2: clean handover
        }
        known |= {f"lora{i}" for i in range(1, len(h["loras"]) + 1)}
        known |= set(h["markers"])
        known |= {m + "s" for m in h["markers"]}
        known |= {"loras", "ars"}
        return known

    # ------------------------------------------------------------------
    # GPU slot at the Alpaka proxy (v0.13.0)
    # ------------------------------------------------------------------

    def _proxy_base(self) -> str:
        return self.valves.proxy_url.rstrip("/")

    async def _proxy_post(self, path: str, payload: dict, timeout_s: float = 10):
        """One short POST to Alpaka over its own connection. Returns
        (data|None, err|None); on an HTTP error the parsed body is still
        returned when possible (unload sends details that way). Never
        raises."""
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(self._proxy_base() + path, json=payload) as resp:
                    data = None
                    try:
                        data = await resp.json()
                    except Exception:
                        pass
                    if resp.status != 200:
                        return data, f"HTTP {resp.status}"
                    return data if data is not None else {}, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    async def _proxy_get(self, path: str, timeout_s: float = 10):
        """One short GET to Alpaka. Returns (data|None, err|None);
        never raises. (v0.13.2)"""
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(self._proxy_base() + path) as resp:
                    data = None
                    try:
                        data = await resp.json()
                    except Exception:
                        pass
                    if resp.status != 200:
                        return data, f"HTTP {resp.status}"
                    return data if data is not None else {}, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    async def _slot_position(self, tag: str):
        """Own position among Alpaka's waiting entries (or None)."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(self._proxy_base() + "/proxy/status") as resp:
                    st = await resp.json()
        except Exception:
            return None
        for entry in st.get("queue") or []:
            if entry.get("kind") == "image" and entry.get("tag") == tag:
                return entry.get("position")
        return None

    async def _acquire_slot(self, emitter, name: str, tag: str):
        """Blocking acquire with position display. Returns (slot_id, err).
        A user abort cancels the request - Alpaka's socket peek then
        removes the waiting entry by itself. Waiting is deliberately NOT
        bounded by timeout_seconds (slot specification)."""
        timeout = aiohttp.ClientTimeout(total=None)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as s:
                post = asyncio.ensure_future(
                    s.post(
                        self._proxy_base() + "/proxy/acquire",
                        json={"label": name, "tag": tag},
                    )
                )
                try:
                    while True:
                        done, _ = await asyncio.wait({post}, timeout=1.5)
                        if post in done:
                            break
                        pos = await self._slot_position(tag)
                        if pos:
                            await self._emit(
                                emitter,
                                f"{name}: wartet auf freie GPU — "
                                f"Position {pos} in der Warteschlange ...",
                            )
                        else:
                            await self._emit(
                                emitter, f"{name}: wartet auf freie GPU ..."
                            )
                    resp = post.result()
                except asyncio.CancelledError:
                    post.cancel()
                    raise
                async with resp:
                    if resp.status != 200:
                        return None, f"HTTP {resp.status}"
                    data = await resp.json()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"
        slot_id = data.get("slot_id")
        if not slot_id:
            return None, "Antwort ohne slot_id"
        return slot_id, None

    async def _heartbeat_loop(self, slot_id: str, state: dict):
        """Background task from grant to release: one heartbeat every
        10 s. An 'unknown' answer means the lease expired (e.g. Alpaka
        restart) - noted in state, the job itself continues, no
        re-acquire (slot specification)."""
        while True:
            await asyncio.sleep(10)
            data, err = await self._proxy_post(
                "/proxy/heartbeat", {"slot_id": slot_id}, timeout_s=8
            )
            if err or not isinstance(data, dict):
                continue  # transient - the next round tries again
            if not data.get("ok"):
                state["lost"] = True
                return

    async def _release_slot(self, slot_id: str):
        """Give the slot back; idempotent on the proxy side, never raises."""
        await self._proxy_post("/proxy/release", {"slot_id": slot_id})

    async def _comfy_free(self):
        """POST ComfyUI's native /free: unload model weights and clear the
        execution cache, so the VRAM really goes back to the driver.
        Returns (ok, err); never raises. (v0.13.1)"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(
                    self.valves.comfy_url.rstrip("/") + "/free",
                    json={"unload_models": True, "free_memory": True},
                ) as resp:
                    if resp.status != 200:
                        return False, f"HTTP {resp.status}"
                    return True, None
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    async def _queue_position(
        self, session, base: str, prompt_id: str
    ) -> Optional[int]:
        """0/None = running or unknown, n > 0 = waiting at position n."""
        try:
            async with session.get(f"{base}/queue") as resp:
                data = await resp.json()
        except Exception:
            return None
        for entry in data.get("queue_running", []) or []:
            if len(entry) > 1 and entry[1] == prompt_id:
                return 0
        for i, entry in enumerate(data.get("queue_pending", []) or [], start=1):
            if len(entry) > 1 and entry[1] == prompt_id:
                return i
        return None

    async def _abort_job(self, base: str, prompt_id: str) -> str:
        """After a stop in Open WebUI, withdraw our own job from ComfyUI. Runs
        over its own short connection because the main session is being torn
        down. Returns: a short text for the status line - no exception ever
        escapes from here.

        Assumption (documented ComfyUI behaviour, not verified against a
        running system): POST /queue {"delete": [id]} removes pending jobs,
        POST /interrupt aborts the one currently running."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{base}/queue") as resp:
                    data = await resp.json()
                running = [
                    e[1] for e in (data.get("queue_running") or []) if len(e) > 1
                ]
                pending = [
                    e[1] for e in (data.get("queue_pending") or []) if len(e) > 1
                ]
                if prompt_id in pending:
                    async with session.post(
                        f"{base}/queue", json={"delete": [prompt_id]}
                    ) as resp:
                        if resp.status != 200:
                            return (
                                "Löschen aus der ComfyUI-Warteschlange fehlgeschlagen "
                                f"(HTTP {resp.status})"
                            )
                    return "ComfyUI-Auftrag aus der Warteschlange gelöscht"
                if prompt_id in running:
                    # Only then: /interrupt hits the running job, whoever it belongs to
                    async with session.post(f"{base}/interrupt") as resp:
                        if resp.status != 200:
                            return f"Unterbrechen bei ComfyUI fehlgeschlagen (HTTP {resp.status})"
                    return "laufender ComfyUI-Auftrag unterbrochen"
                return "ComfyUI-Auftrag war schon fertig"
        except Exception as e:
            return f"Aufräumen bei ComfyUI fehlgeschlagen ({type(e).__name__}: {e})"

    def _set(self, wf: dict, handle, value):
        if not handle:
            return False
        node_id, field = handle
        wf[node_id]["inputs"][field] = value
        return True

    def _manual(self, is_admin: bool = False) -> str:
        text = """# Bildgenerierung -- vollständige Anleitung

**Grundprinzip:** Prompt eintippen (Deutsch ist ok), Kürzel dahinter.
Der Text kommt immer zuerst, die Kürzel danach. `--` und der lange
Gedankenstrich funktionieren beide.

`Eine Katze auf einer Wiese --ar 1:1 --batch 2 --seed 42`

## Kürzel

| Kürzel | Wirkung |
|---|---|
| `--ar 16:9` | Seitenverhältnis |
| `--mp 1.5` | Bildgröße in Megapixeln |
| `--batch 2` | Anzahl Bilder pro Anfrage |
| `--steps 25` | Sampler-Schritte |
| `--seed 42` | Fester Seed -- gleiches Bild reproduzierbar |
| `--no blurry, fog` | Negativ-Prompt (nur wirksam bei cfg > 1) |
| `--cfg 2` | CFG-Wert -- bei Turbo-Modellen auf 1 lassen! |
| `--guidance 2.5` | FluxGuidance (nur Flux) |
| `--translate 0/1` | Übersetzung für diese Nachricht aus/an |
| `--arauto 0/1` | Format aus dem angehängten Bild ableiten aus/an (nur Workflows mit Bildeingang) |
| `--triggers 0/1` | Automatische Triggerwörter aus/an |

Dazu je Workflow eigene Kürzel aus `PIPE_*`-Knoten (z.B. `--refine`,
`--enablelora`, `--trigger`) -- welche es gibt, zeigt `--help`.

## LoRAs

- `--lora1 0.4` -- Stärke setzen
- `--lora1 cat_v1` -- Datei tauschen (Namensfragment reicht)
- `--lora1 cat_v1:0.8` -- beides zugleich
- `--loras` -- alle verfügbaren Dateien, `--loras F_` filtert
- Kürzel + `s` zeigt die Auswahl (`--vaes`, `--models`), Kürzel ohne Wert
  setzt es zurück

Die Slot-Nummern stehen in `--help`.

## Dauerhafte Vorgaben

Eine Nachricht **nur aus Kürzeln** speichert sie als Vorgaben --
pro Benutzer und Workflow, in allen Chats gültig:

`--lora1 0.3 --refine 0 --ar 3:2`

Danach reicht der nackte Prompt. Ein Kürzel in einer normalen
Nachricht übersteuert die Vorgabe einmalig. `--reset` löscht alle
Vorgaben des Workflows.

**Rangfolge:** Nachricht > Vorgaben > Chat-Steuerung > Workflow-Datei.

## Chat-Steuerung (Schieberegler-Symbol)

`translate` (Übersetzung dauerhaft an), `show_prompt` (Info-Zeile
unter dem Bild -- anfangs anschalten!), `auto_ar` (Format aus dem
angehängten Bild), `seed`, `steps`, `aspect_ratio`, `megapixels`,
`batch_size`.

## Gut zu wissen

- Text in Anführungszeichen wird nicht übersetzt -- für Schrift im
  Bild: `Ein Schild mit der Aufschrift "Katzencafe"`.
- Gleicher Seed ergibt nur bei gleichem Prompt-Weg das gleiche Bild:
  beim Krea2 dafür `--refine 0` und `--translate 0` setzen.
- Ein gelungenes Bild reproduzieren: Seed aus der Info-Zeile ablesen
  und per `--seed` wiederverwenden.
- Der Stopp-Knopf zieht den Auftrag auch bei ComfyUI zurück -- wartende
  Aufträge werden gelöscht, laufende unterbrochen.
- Bei Workflows mit Bildeingang folgt das Format dem angehängten Foto
  (nächstliegendes Seitenverhältnis), solange kein `--ar` gesetzt ist.
  `--ar` gewinnt immer; `--arauto 0` schaltet es ab.
- Bild- und Chat-Aufträge teilen sich die Grafikkarte: ist sie belegt,
  wartet der Bildauftrag — die Statuszeile zeigt die Position. Der
  Stopp-Knopf bricht auch das Warten ab."""

        if not is_admin:
            return text

        return text + """

---

# Für Admins

## Neuen Workflow anschließen

1. In ComfyUI den Knoten, der den Prompt-Text aufnimmt, in `PIPE_PROMPT`
   umbenennen. Optional: `PIPE_NEGATIVE`, `PIPE_IMAGE` (Bildeingang),
   `PIPE_LOCK …` (LoRA aus der Nummerierung nehmen), `PIPE_INTERNAL …`
   (Knoten wird vor dem Auftrag entfernt — für Vorschau-Knoten, die nur
   in ComfyUI sichtbar sein sollen; nur an Knoten ohne Abnehmer) und
   beliebige `PIPE_NAME`- bzw. `PIPE_NAME:feldname`-Marker, die zu
   Kürzeln werden.
2. Workflow einmal erfolgreich laufen lassen, dann
   **Workflow → Export (API)** — nicht das normale Speichern.
3. Datei ins Workflow-Verzeichnis legen (siehe Ablageorte unten).
   Der Dateiname wird zum Namen in der Modellauswahl.
4. `--help` im neuen Eintrag: prüfen, ob alles erkannt wurde.

Automatisch erkannt (per `class_type`): Seed (RandomNoise/KSampler),
Schritte (BasicScheduler/KSampler), cfg (CFGGuider/KSampler),
FluxGuidance, Auflösung (EmptyLatentImage/EmptySD3LatentImage/
ResolutionSelector), LoRAs (LoraLoader/LoraLoaderModelOnly),
Bildeingang (LoadImage). Nach jedem Re-Export einmal `--help` —
Knoten-IDs und damit die LoRA-Nummerierung können sich verschieben;
danach ggf. `--reset`.

## Admin-Valves (Zahnrad an der Funktion)

`comfy_url`, `timeout_seconds`, `max_batch` (Obergrenze für `--batch`),
`ollama_url`, `translate_model`, `translate_keep_alive`,
`translate_system` (verträgt ein Glossar), `lora_triggers`
(`fragment | triggerwort` je Zeile), `store_images_as_files`,
`auto_ar_from_image` (Format aus dem angehängten Bild, global an/aus),
`proxy_url` (Alpaka-Basis-URL), `use_alpaka_proxy` (GPU-Slot vor jedem
Bildauftrag; aus = Verhalten wie v0.12.4). Das automatische
VRAM-Freiräumen wohnt seit v0.13.2 im Alpaka-Proxy (Saubere Übergabe) —
zur Laufzeit schaltbar per `--handover`, die Dateikopf-Konstanten sind
nur die Erststart-Vorgaben.

## Aufräum-Kommandos (nur Admins)

| Kürzel | Wirkung |
|---|---|
| `--kill-ollama-tasks` | bricht alle laufenden Ollama-Anfragen über den Alpaka-Proxy ab |
| `--unload-ollama [name]` | entlädt Ollama-Modelle per keep_alive 0 (ohne Name: alle) |
| `--unload-comfy` | gibt ComfyUIs Speicher frei (Modelle entladen, Cache leeren) |
| `--handover [on/off/custom]` | zeigt (ohne Wert) oder setzt Alpakas Saubere Übergabe |
| `--handover-comfy 0/1`, `--handover-ollama 0/1` | Einzelschalter je Richtung (stellt automatisch auf custom) |

Beide laufen pipe-lokal: kein GPU-Slot, keine Übersetzung, kein
ComfyUI-Auftrag — sie funktionieren also auch, wenn alle Chat-Modelle
festhängen, und unabhängig von `use_alpaka_proxy`. Reihenfolge im
Störfall: erst kill (räumt Rechnendes), dann unload (räumt VRAM —
Ollama- und ComfyUI-Seite je nach Bedarf).

## Ablageorte

- Workflows: `/app/backend/data/comfy_workflows`
- Gespeicherte Vorgaben: `/app/backend/data/comfy_pipe_defaults.json`
- Bilder: Open-WebUI-Dateiablage, zusätzlich ComfyUI-Ausgabeordner

## Fester Prompt je Modell (Systemprompt)

In Open WebUI beim Workspace-Modell einen System Prompt hinterlegen —
er wird jedem Auftrag fest vorangestellt. Getippter Text ergänzt ihn
dahinter; bei Bearbeitungs-Workflows genügt dann das Bild allein.
Kürzel im Systemprompt werden nicht ausgewertet, sondern landen
wörtlich im Bild-Prompt. Chats ohne getippten Text bekommen
automatisch einen Titel aus Zeitstempel und Modellname.
Was Open WebUI selbst in die Systemnachricht schreibt (Gedächtnis-Block,
Chat-Zusammenfassung der Context Compaction), wird vorher entfernt und
in der Info-Zeile vermerkt.

## Stolperfallen

- „Kein Prompt angegeben" → Text muss *vor* den Kürzeln stehen.
- Immer dasselbe Bild → fester Seed als Vorgabe; `--reset`.
- Statusmeldungen fehlen → Capability „Status Updates" am Modell aus.
- Krea2-Bilder kaputt → cfg über 1 gedreht.
- LoRA wirkt nicht → Architektur passt nicht zum Bildmodell."""

    def _describe(
        self,
        name: str,
        h: dict,
        wf: dict,
        defaults: Optional[dict] = None,
        listers: Optional[dict] = None,
        is_admin: bool = False,
    ) -> str:
        listers = listers or {}
        lines = [f"**{name}** - erkannte Stellhebel:", ""]
        lines.append(
            f"- Prompt: {'Knoten ' + h['prompt'][0] if h.get('prompt') else 'NICHT GEFUNDEN (PIPE_PROMPT vergeben?)'}"
        )
        lines.append(
            f"- Negativ: {'Knoten ' + h['negative'][0] if h.get('negative') else 'keiner (--no wirkungslos)'}"
        )
        for key, label in (
            ("seed", "Seed"),
            ("steps", "Schritte"),
            ("cfg", "cfg"),
            ("guidance", "FluxGuidance"),
        ):
            lines.append(f"- {label}: {'Knoten ' + h[key][0] if h.get(key) else '-'}")
        if h.get("image"):
            lines.append(
                f"- Bildeingang: Knoten {h['image'][0]} (Foto an die Nachricht anhängen)"
            )
            if self.valves.auto_ar_from_image:
                lines.append(
                    "- `--arauto 1/0` : Seitenverhältnis automatisch aus dem angehängten Bild "
                    "(gilt nur, wenn kein `--ar` angegeben ist)"
                )
        if len(h.get("dimension_nodes", [])) > 1:
            lines.append(
                "- Größe wird gemeinsam gesetzt in: "
                + ", ".join(
                    f"{nid} ({wf[nid].get('class_type', '?')})"
                    for nid in h["dimension_nodes"]
                )
            )
        lines.append(
            f"- Auflösung: {'ResolutionSelector ' + h['resolution'] if h.get('resolution') else ('Latent ' + h['latent'] if h.get('latent') else '-')}"
        )
        for i, nid in enumerate(h["loras"], start=1):
            lname = wf[nid]["inputs"].get("lora_name", "?")
            strength = wf[nid]["inputs"].get("strength_model", "?")
            lines.append(f"- `--lora{i}` : {lname} (aktuell {strength})")
        for nid in h.get("locked_loras", []):
            lname = wf[nid]["inputs"].get("lora_name", "?")
            strength = wf[nid]["inputs"].get("strength_model", "?")
            lines.append(
                f"- (fest) {lname}, Stärke {strength} — für diesen Workflow nicht änderbar"
            )
        for name, (nid, field) in h["markers"].items():
            cur = wf[nid]["inputs"][field]
            if isinstance(cur, bool):
                hinweis = " — 0 oder 1"
            elif isinstance(cur, (int, float)):
                hinweis = " — Zahlenwert"
            elif isinstance(cur, str) and cur.lower().endswith(MODEL_EXTS):
                hinweis = " — Namensteil genügt"
            else:
                hinweis = ""
            lines.append(
                f"- `--{name}` : Knoten {nid}.{field} (aktuell {cur}){hinweis}"
            )
        if h.get("prompt_result"):
            lines.append(
                f"- Ergebnis-Prompt: Knoten {h['prompt_result']} "
                "(wird nach dem Lauf unter das Bild geschrieben)"
            )
        lines.append(
            "- Bildausgabe: "
            + (
                ", ".join(f"Knoten {n}" for n in h["outputs"])
                if h.get("outputs")
                else "⚠ KEINE — Workflow erzeugt so kein Bild"
            )
        )
        for nid in h.get("internal", []):
            ctype = h.get("internal_types", {}).get(nid, "?")
            lines.append(
                f"- (intern) Knoten {nid} ({ctype}) wird vor dem "
                "Auftrag entfernt — nur in ComfyUI sichtbar"
            )
        for problem in h.get("marker_errors", []):
            lines.append(f"- ⚠ {problem}")
        if self.valves.translate_model:
            lines.append(
                f"- `--translate 1/0` : Übersetzung per {self.valves.translate_model}"
            )
        lines += [
            "",
            "**Kürzel:** `--ar 16:9`, `--mp 1.5`, `--batch 2`, `--steps 25`, "
            "`--seed 1234`, `--cfg 2`, `--guidance 2`, `--no text`, `--help`",
            "",
            "**LoRAs:** `--lora1 0.4` setzt die Stärke, `--lora1 cat_v1` tauscht die Datei, "
            "`--lora1 cat_v1:0.8` beides.",
            "",
            "**Anzeigen:** Kürzel + `s` listet die möglichen Werte auf, ein Suchbegriff "
            "filtert — " + ", ".join(f"`--{l}`" for l in sorted(listers)) + ".",
            "",
            "**Zurücksetzen:** Kürzel ohne Wert (z. B. `--vae`) verwirft die gespeicherte "
            "Vorgabe und stellt den Wert aus dem Workflow wieder her. `--reset` verwirft alle.",
            "",
            "**Zum Kopieren:** "
            + " ".join(f"`--{l}`" for l in sorted(listers))
            + "  `--anleitung`  `--reset`",
        ]
        if defaults:
            lines += [
                "",
                "**Gespeicherte Vorgaben** (übersteuern die Datei-Werte oben, `--reset` löscht):",
            ] + [f"- `--{k} {v}`".rstrip() for k, v in defaults.items()]
        if is_admin:
            lines += [
                "",
                "**Aufräum-Kommandos (nur Admins):** `--kill-ollama-tasks` bricht "
                "laufende Ollama-Anfragen über den Alpaka-Proxy ab, "
                "`--unload-ollama [name]` entlädt Ollama-Modelle (ohne Name: alle), "
                "`--unload-comfy` gibt ComfyUIs Speicher frei, `--handover` "
                "zeigt/schaltet Alpakas Saubere Übergabe (on/off/custom, "
                "Einzelschalter --handover-comfy/--handover-ollama 0/1). "
                "Alle laufen pipe-lokal — kein GPU-Slot, keine Übersetzung.",
            ]
        lines += []
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def _emit(self, emitter, text, done=False):
        if not emitter:
            return
        try:
            result = emitter(
                {"type": "status", "data": {"description": text, "done": done}}
            )
            if inspect.isawaitable(result):
                await result
        except Exception:
            pass  # the status display must never make a run fail

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
        __task__: Optional[str] = None,
        __metadata__: Optional[dict] = None,
    ) -> str:
        """Wrapper around _run: makes sure the status display is cleared on
        every path - including early returns and errors."""
        started = time.monotonic()
        cancelled = False
        abort_note = None
        # v0.13.0: slot bookkeeping lives here so that EVERY end path of
        # _run (return, error, stop button) releases the GPU slot.
        slot_ctx = {"slot_id": None, "hb_task": None, "state": {"lost": False}}
        try:
            return await self._run(
                body,
                __user__,
                __event_emitter__,
                __task__,
                __metadata__,
                slot_ctx,
            )
        except asyncio.CancelledError as e:
            # Stop button in Open WebUI. What _run cleaned up at ComfyUI is
            # attached to the exception as an attribute (see polling loop).
            cancelled = True
            abort_note = getattr(e, "comfy_note", None)
            raise
        finally:
            if slot_ctx["hb_task"] is not None:
                slot_ctx["hb_task"].cancel()
            if slot_ctx["slot_id"]:
                # shield: the release must go through even on a second stop
                await asyncio.shield(self._release_slot(slot_ctx["slot_id"]))
            elapsed = time.monotonic() - started
            if cancelled:
                text = "Abgebrochen"
                if abort_note:
                    text += f" — {abort_note}"
                await self._emit(__event_emitter__, text, done=True)
            elif elapsed < 1.5:
                # Pure text output (--help, --loras) needs no duration
                await self._emit(__event_emitter__, "", done=True)
            else:
                await self._emit(
                    __event_emitter__, f"Fertig in {_duration(elapsed)}", done=True
                )

    async def _run(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
        __task__: Optional[str] = None,
        __metadata__: Optional[dict] = None,
        _slot_ctx: Optional[dict] = None,
    ) -> str:
        if __task__:
            return "ComfyUI"
        _slot_ctx = (
            _slot_ctx
            if _slot_ctx is not None
            else {"slot_id": None, "hb_task": None, "state": {"lost": False}}
        )

        pipe_id = str(body.get("model", "")).split(".")[-1]

        messages = body.get("messages") or []
        raw = ""
        if messages:
            content = messages[-1].get("content", "")
            if isinstance(content, list):
                raw = "\n".join(
                    p.get("text", "") for p in content if p.get("type") == "text"
                )
            else:
                raw = str(content)

        user_valves = (__user__ or {}).get("valves") or self.UserValves()

        try:
            wf, name = self._load(pipe_id)
        except Exception as e:
            return f"**Workflow konnte nicht geladen werden**\n\n{e}"

        h = self._analyze(wf)
        raw = _strip_wrappers(raw)
        prompt, flags = self._parse_flags(raw)

        # PIPE_INTERNAL nodes leave the job here; wf is a fresh copy per
        # request, so the workflow file stays untouched. --help still
        # lists them (from h), the job itself never contains them.
        for nid in h.get("internal", []):
            wf.pop(nid, None)

        if "anleitung" in flags:
            is_admin = str((__user__ or {}).get("role", "")).lower() == "admin"
            return self._manual(is_admin)

        # --- Admin clean-up flags (v0.13.0) ---
        # Handled locally like --help: no slot, no translation, no ComfyUI
        # job - the emergency broom must not wait in the very queue it is
        # meant to sweep. Needs only proxy_url; works with
        # use_alpaka_proxy off.
        if (
            "kill-ollama-tasks" in flags
            or "unload-ollama" in flags
            or "unload-comfy" in flags
            or "handover" in flags
            or "handover-comfy" in flags
            or "handover-ollama" in flags
        ):
            if str((__user__ or {}).get("role", "")).lower() != "admin":
                return "Die Aufräum-Kommandos sind Administratoren vorbehalten."
            out: list[str] = []
            if "kill-ollama-tasks" in flags:
                data, err = await self._proxy_post("/proxy/kill-tasks", {})
                if err:
                    out.append(
                        f"**kill-tasks fehlgeschlagen** ({err}) — läuft der "
                        f"Alpaka-Proxy unter `{self._proxy_base()}`?"
                    )
                else:
                    victims = (data or {}).get("killed") or []
                    if victims:
                        out.append(
                            f"**{len(victims)} laufende Ollama-Anfrage(n) "
                            "abgebrochen:**\n"
                            + "\n".join(
                                f"- #{v.get('qid')} {v.get('model')}"
                                + (f" (Tag {v.get('tag')})" if v.get("tag") else "")
                                for v in victims
                            )
                        )
                    else:
                        out.append(
                            "Keine laufende Ollama-Anfrage — nichts abzubrechen."
                        )
            if "unload-ollama" in flags:
                frag = str(flags.get("unload-ollama") or "").strip()
                data, err = await self._proxy_post(
                    "/proxy/unload", {"model": frag} if frag else {}, timeout_s=90
                )
                data = data or {}
                if err and not data:
                    out.append(
                        f"**unload fehlgeschlagen** ({err}) — läuft der "
                        f"Alpaka-Proxy unter `{self._proxy_base()}`?"
                    )
                elif data.get("unloaded"):
                    out.append("**Entladen:** " + ", ".join(data["unloaded"]))
                elif data.get("ok"):
                    out.append("Kein Modell geladen — nichts zu entladen.")
                else:
                    detail = data.get("error") or err or "unbekannter Fehler"
                    if data.get("matches"):
                        detail += " — Treffer: " + ", ".join(data["matches"])
                    if data.get("loaded"):
                        detail += " — geladen: " + ", ".join(data["loaded"])
                    out.append(f"**unload abgelehnt:** {detail}")
            if "unload-comfy" in flags:
                ok_free, err_free = await self._comfy_free()
                if ok_free:
                    out.append(
                        "**ComfyUI-Speicher freigegeben** "
                        "(Modelle entladen, Cache geleert)."
                    )
                else:
                    out.append(
                        f"**ComfyUI-Freigabe fehlgeschlagen** ({err_free}) — "
                        f"läuft ComfyUI unter `{self.valves.comfy_url}`?"
                    )
            if (
                "handover" in flags
                or "handover-comfy" in flags
                or "handover-ollama" in flags
            ):
                payload = {}
                errs = []
                if "handover" in flags:
                    mode = str(flags.get("handover") or "").strip().lower()
                    if mode and mode in ("on", "off", "custom"):
                        payload["mode"] = mode
                    elif mode:
                        errs.append(
                            f"unbekannter Modus `{mode}` — erlaubt: on, off, custom"
                        )
                for fname, key in (
                    ("handover-comfy", "free_comfy"),
                    ("handover-ollama", "unload_ollama"),
                ):
                    if fname in flags:
                        val = str(flags.get(fname) or "").strip()
                        if val in ("0", "1"):
                            payload[key] = val == "1"
                        else:
                            errs.append(f"`--{fname}` erwartet 0 oder 1")
                if errs:
                    out.append("**Saubere Übergabe:** " + "; ".join(errs))
                else:
                    if payload:
                        data, err = await self._proxy_post("/proxy/handover", payload)
                    else:
                        data, err = await self._proxy_get("/proxy/handover")
                    data = data or {}
                    if err and not data:
                        out.append(
                            f"**Saubere Übergabe nicht erreichbar** ({err}) — "
                            f"läuft der Alpaka-Proxy unter `{self._proxy_base()}`?"
                        )
                    elif not data.get("mode"):
                        out.append(
                            "**Saubere Übergabe:** unerwartete Antwort"
                            + (f" ({err})" if err else "")
                            + " — Alpaka v5.4 oder neuer nötig."
                        )
                    else:
                        eff = data.get("effective") or {}
                        txt = (
                            f"**Saubere Übergabe:** Modus **{data['mode']}** — "
                            f"Comfy-Freigabe vor Chats: "
                            f"{'an' if eff.get('free_comfy') else 'aus'}, "
                            f"Ollama-Entladen vor Bildjobs: "
                            f"{'an' if eff.get('unload_ollama') else 'aus'}"
                        )
                        if data.get("note"):
                            txt += f"\n⚠️ {data['note']}"
                        if data.get("save_error"):
                            txt += (
                                f"\n⚠️ Einstellung nicht gespeichert: "
                                f"{data['save_error']}"
                            )
                        out.append(txt)
            return "\n\n".join(out)

        has_image_input = bool(h.get("image")) and bool(self._extract_images(body))
        if "help" in flags or (not raw.strip() and not has_image_input):
            help_defaults = self._load_defaults((__user__ or {}).get("id"), pipe_id)
            is_admin = str((__user__ or {}).get("role", "")).lower() == "admin"
            return self._describe(
                name, h, wf, help_defaults, self._listers(h, wf), is_admin
            )

        if not h.get("prompt"):
            return (
                f"Im Workflow **{name}** ist kein Knoten mit dem Titel `{TITLE_PROMPT}` markiert "
                "und es ließ sich auch keiner herleiten. Bitte in ComfyUI den Knoten umbenennen, "
                "der den Prompt-Text aufnimmt, und neu als API exportieren."
            )
        user_id = (__user__ or {}).get("id")
        defaults = self._load_defaults(user_id, pipe_id)

        if "reset" in flags:
            self._save_defaults(user_id, pipe_id, {})
            return f"Gespeicherte Vorgaben für **{name}** gelöscht."

        listers = self._listers(h, wf)
        command_flags = COMMAND_FLAGS | set(listers)

        if not prompt and flags and not (set(flags) & command_flags):
            known = self._known_flags(h)
            unknown = [k for k in flags if k not in known]
            accepted = {k: v for k, v in flags.items() if k in known}

            # A flag without a value resets exactly that entry
            resets = [k for k, v in accepted.items() if not str(v).strip()]
            notes: list[str] = []
            for k in resets:
                accepted.pop(k)
                if defaults.pop(k, None) is not None:
                    notes.append(
                        f"`--{k}` zurückgesetzt — es gilt wieder der Wert aus dem Workflow."
                    )
                else:
                    notes.append(f"`--{k}` war nicht gesetzt — nichts zu ändern.")

            # Validate the values so that errors show up when saving
            # and not only at the next image
            accepted, more = await self._normalize_standalone(wf, h, accepted)
            notes += more
            for k in list(accepted):
                if re.fullmatch(r"lora\d+", k):
                    merged = self._merge_lora_value(defaults.get(k, ""), accepted[k])
                    if merged:
                        accepted[k] = merged
                    else:
                        accepted.pop(k)
            defaults.update(accepted)
            self._save_defaults(user_id, pipe_id, defaults)

            if defaults:
                lines = [
                    f"Vorgaben für **{name}** (gelten in allen Chats, "
                    "`--reset` löscht alle):",
                    "",
                ]
                lines += [f"- `--{k} {v}`".rstrip() for k, v in defaults.items()]
            else:
                lines = [f"Für **{name}** sind keine Vorgaben gespeichert."]
            if notes:
                lines += [""] + notes
            if unknown:
                lines += [
                    "",
                    "Unbekannt und nicht gespeichert: "
                    + ", ".join("--" + u for u in unknown),
                ]
            return "\n".join(lines)

        if not prompt and not has_image_input and not (set(flags) & command_flags):
            return (
                "Kein Prompt angegeben. Der Text muss **vor** den Kürzeln stehen, "
                "zum Beispiel:\n\n`Eine getigerte Katze auf einer Wiese --lora1 0.3 --seed 42`"
            )

        msg_flags = dict(flags)
        bare = {
            k
            for k, v in msg_flags.items()
            if not str(v).strip() and k not in command_flags
        }
        if defaults:
            merged = {**defaults, **flags}
            for k in flags:
                if k in bare:
                    continue
                if re.fullmatch(r"lora\d+", k) and k in defaults:
                    merged[k] = self._merge_lora_value(defaults[k], flags[k])
            flags = merged
        for k in bare:
            # For this one image the value from the workflow file applies
            flags.pop(k, None)

        base = self.valves.comfy_url.rstrip("/")
        used: list[str] = []
        await self._emit(__event_emitter__, f"{name}: wird vorbereitet ...")

        # --- Set the chat title ourselves if no prompt was typed ---
        # Open WebUI's title fallback (first message = title) produces
        # nothing for empty text. Deliberately BEFORE the system prompt
        # block so that "empty" refers to the typed text only - chats with
        # their own prompt keep their usual title.
        if not prompt:
            meta = __metadata__ or {}
            model_label = (meta.get("model") or {}).get("name") or name or pipe_id
            title = time.strftime("%Y%m%d %H:%M") + f" {model_label}"
            outcome, detail = await self._set_chat_title(meta.get("chat_id"), title)
            if outcome == "gesetzt":
                used.append(f"Titel gesetzt: {detail}")
            elif outcome == "behalten":
                used.append(f"Titel behalten: {detail}")
            else:
                used.append(f"Titel nicht gesetzt ({detail})")

        # --- Prepend the model's system prompt permanently ---
        # Deliberately only here: the branches above (help, saving defaults,
        # "Kein Prompt angegeben") still depend on the typed text alone.
        system_prompt, had_memory, had_summary = self._system_prompt(body)
        if had_memory:
            used.append("Gedächtnis-Block aus dem Systemprompt entfernt")
        if had_summary:
            used.append(
                "Chat-Zusammenfassung (Context Compaction) aus dem Systemprompt entfernt"
            )
        if system_prompt:
            if prompt:
                prompt = f"{system_prompt.rstrip(' ,.')}, {prompt}"
                used.append("Systemprompt vorangestellt")
            else:
                prompt = system_prompt
                used.append("Systemprompt als Prompt verwendet")

        # --- Prompt and negative ---
        self._set(wf, h["prompt"], prompt)
        if "no" in flags:
            if h.get("negative"):
                self._set(wf, h["negative"], flags["no"])
                used.append(f"negativ: {flags['no']}")
            else:
                used.append("negativ: ignoriert (Workflow hat keinen Negativ-Zweig)")

        # --- Seed ---
        seed = user_valves.seed
        if "seed" in flags and flags["seed"].lstrip("-").isdigit():
            seed = int(flags["seed"])
        if seed < 0:
            seed = random.randint(0, 2**53)
        if self._set(wf, h.get("seed"), seed):
            used.append(f"seed {seed}")

        # --- Steps ---
        steps = (
            int(flags["steps"])
            if flags.get("steps", "").isdigit()
            else user_valves.steps
        )
        if steps > 0 and self._set(wf, h.get("steps"), steps):
            used.append(f"{steps} Schritte")

        # --- cfg / guidance ---
        for key in ("cfg", "guidance"):
            if key in flags:
                try:
                    val = float(flags[key].replace(",", "."))
                except ValueError:
                    continue
                if self._set(wf, h.get(key), val):
                    used.append(f"{key} {val}")

        # --- Marker nodes (PIPE_xxx) ---
        file_markers: dict = {}
        for marker_name, handle in h["markers"].items():
            if marker_name not in flags:
                continue
            current = wf[handle[0]]["inputs"][handle[1]]
            if isinstance(current, str) and current.lower().endswith(MODEL_EXTS):
                # File name: match against ComfyUI's option list first (inside the session)
                file_markers[marker_name] = handle
                continue
            value = self._coerce(flags[marker_name], current)
            self._set(wf, handle, value)
            used.append(f"{marker_name}: {value}")

        # --- Batch ---
        batch = (
            int(flags["batch"])
            if flags.get("batch", "").isdigit()
            else user_valves.batch_size
        )
        if batch > 0:
            if not h.get("latent"):
                used.append(
                    "Bildanzahl nicht änderbar: dieser Workflow hat keinen "
                    "Empty-Latent-Knoten"
                )
            else:
                wanted = batch
                batch = min(batch, self.valves.max_batch)
                wf[h["latent"]]["inputs"]["batch_size"] = batch
                if batch < wanted:
                    used.append(
                        f"{batch} Bilder (statt {wanted} — Obergrenze max_batch "
                        f"= {self.valves.max_batch} in den Admin-Valves)"
                    )
                else:
                    used.append(f"{batch} Bilder")

        # --- Report unknown flags instead of swallowing them silently ---
        unknown = [k for k in flags if k not in self._known_flags(h)]
        if unknown:
            used.append(
                "unbekannt und ignoriert: " + ", ".join("--" + u for u in unknown)
            )

        try:
            # v0.13.1: transport timeouts only — they detect a dead
            # socket, they do not give up on a long render. The compute
            # cap lives in the history loop (timeout_seconds, 0 = off).
            timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                for lister, (kind, payload) in listers.items():
                    if lister not in flags:
                        continue
                    needle = str(flags[lister]).strip()
                    if kind == "loras":
                        options = await self._lora_options(session, base)
                        titel = "Verfügbare LoRAs"
                    elif kind == "resolution":
                        options = await self._resolution_options(session, base)
                        titel = "Seitenverhältnisse"
                    else:
                        class_type, field, marker_name = payload
                        options = await self._field_options(
                            session, base, class_type, field
                        )
                        titel = f"Werte für `--{marker_name}`"
                    if not options:
                        return (
                            f"Für `--{lister}` liefert ComfyUI keine Auswahlliste. "
                            "Entweder hat das Feld keine, oder ComfyUI antwortet nicht."
                        )
                    if needle:
                        shown = [o for o in options if needle.lower() in o.lower()]
                        if not shown:
                            return (
                                f"Keiner der {len(options)} Einträge enthält '{needle}'. "
                                f"Ohne Filter listet `--{lister}` alle auf."
                            )
                        kopf = f"**{titel}** mit '{needle}' ({len(shown)} von {len(options)}):"
                    else:
                        shown = options
                        kopf = f"**{titel}** ({len(options)}):"
                    return kopf + "\n\n" + "\n".join(f"- `{o}`" for o in shown)

                # --- Upload the attached image ---
                images_in = self._extract_images(body)
                if h.get("image"):
                    if images_in:
                        raw_img, fname = images_in[0]
                        await self._emit(__event_emitter__, "Bild wird hochgeladen ...")
                        ref, err = await self._upload_image(
                            session, base, raw_img, fname
                        )
                        if err:
                            return f"Das Bild konnte nicht an ComfyUI uebergeben werden: {err}"
                        self._set(wf, h["image"], ref)
                        used.append(f"Bild: {ref}")
                        if len(images_in) > 1:
                            used.append(
                                f"{len(images_in) - 1} weitere(s) Bild(er) ignoriert - "
                                "dieser Workflow nimmt nur eins"
                            )
                    else:
                        return (
                            f"**{name}** ist ein Bearbeitungs-Workflow und braucht ein Bild.\n\n"
                            "Häng ein Foto an die Nachricht an (Plus-Symbol neben dem "
                            "Eingabefeld) und schreib dazu, was geändert werden soll — "
                            "zum Beispiel „schönes Wetter“."
                        )
                elif images_in:
                    used.append(
                        "Bild angehängt, aber dieser Workflow verarbeitet keins "
                        "(kein PIPE_IMAGE- oder LoadImage-Knoten)"
                    )

                # --- Aspect ratio from the attached image ---
                # Precedence: --ar (message/defaults) > image > aspect_ratio
                # user valve > workflow file. Only for workflows with an
                # image input, and only if switched on at every level.
                ar_from_image = ""
                auto_ar = self.valves.auto_ar_from_image and user_valves.auto_ar
                if "arauto" in flags:
                    auto_ar = self._coerce(flags["arauto"], True)
                if auto_ar and h.get("image") and images_in and "ar" not in flags:
                    size = self._image_size(images_in[0][0])
                    if not size:
                        used.append(
                            "Format aus Bild: Bildgröße nicht lesbar, Vorgabe bleibt"
                        )
                    elif h.get("resolution"):
                        options = await self._resolution_options(session, base)
                        chosen = (
                            self._nearest_ratio_option(options, *size)
                            if options
                            else None
                        )
                        if chosen:
                            flags["ar"] = chosen
                            ar_from_image = f"{size[0]}x{size[1]}"
                        else:
                            used.append(
                                "Format aus Bild: keine Auswahlliste vom ResolutionSelector, "
                                "Vorgabe bleibt"
                            )
                    elif h.get("dimension_nodes"):
                        flags["ar"] = f"{size[0]}:{size[1]}"
                        ar_from_image = f"{size[0]}x{size[1]}"
                    else:
                        used.append(
                            "Format aus Bild: Workflow hat keine setzbare Größe"
                        )

                # --- Validate all values together once ---
                # The aspect ratio from the chat controls has to pass through
                # validation too - otherwise "1:1" instead of "1:1 (Square)"
                # goes to ComfyUI.
                if "ar" not in flags and user_valves.aspect_ratio:
                    flags["ar"] = user_valves.aspect_ratio
                flags, notes = await self._normalize(session, base, wf, h, flags)
                used.extend(notes)

                # --- Apply LoRAs (names are already resolved) ---
                for i, nid in enumerate(h["loras"], start=1):
                    key = f"lora{i}"
                    if key not in flags:
                        continue
                    name_value, strength = self._parse_lora_value(flags[key])
                    if name_value:
                        wf[nid]["inputs"]["lora_name"] = name_value
                        used.append(f"{key}: {name_value}")
                    if strength is not None:
                        wf[nid]["inputs"]["strength_model"] = strength
                        used.append(f"{key} Stärke {strength}")

                # --- Markers that point at model files ---
                for marker_name, handle in file_markers.items():
                    if marker_name not in flags:
                        continue
                    self._set(wf, handle, flags[marker_name])
                    used.append(f"{marker_name}: {flags[marker_name]}")

                # --- GPU slot at Alpaka (v0.13.0) ---
                # Deliberately only here: uploads and option queries above
                # need no GPU. From this point on (translation -> ComfyUI
                # job -> rendering) the slot is held; pipe() releases it in
                # every end path.
                if self.valves.use_alpaka_proxy:
                    slot_tag = str(
                        (__metadata__ or {}).get("chat_id")
                        or f"comfy-{random.randint(10000, 99999)}"
                    )
                    slot_id, slot_err = await self._acquire_slot(
                        __event_emitter__, name, slot_tag
                    )
                    if slot_err:
                        return (
                            f"**GPU-Slot bei Alpaka nicht erhalten** ({slot_err}).\n\n"
                            f"Läuft der Proxy unter `{self._proxy_base()}`? Ohne ihn "
                            "rendert die Pipe nur, wenn die Admin-Valve "
                            "`use_alpaka_proxy` abgeschaltet wird."
                        )
                    _slot_ctx["slot_id"] = slot_id
                    _slot_ctx["hb_task"] = asyncio.create_task(
                        self._heartbeat_loop(slot_id, _slot_ctx["state"])
                    )

                # --- Translation ---
                final_prompt = prompt
                do_translate = user_valves.translate
                if "translate" in flags:
                    do_translate = self._coerce(flags["translate"], True)
                if do_translate and self.valves.translate_model:
                    await self._emit(__event_emitter__, "Prompt wird übersetzt ...")
                    masked, kept = self._protect(prompt)
                    english, err = await self._translate(
                        session, masked, _slot_ctx["slot_id"]
                    )
                    if err:
                        used.append(
                            f"Übersetzung fehlgeschlagen ({err}), Original verwendet"
                        )
                    elif english:
                        final_prompt = self._restore(english, kept)
                        if final_prompt.strip() == prompt.strip():
                            used.append(
                                f"{self.valves.translate_model} hat den Text unverändert zurückgegeben"
                            )
                        else:
                            used.append(f"übersetzt mit {self.valves.translate_model}")
                    if h.get("negative") and flags.get("no"):
                        neg_en, neg_err = await self._translate(
                            session, flags["no"], _slot_ctx["slot_id"]
                        )
                        if neg_en and not neg_err:
                            self._set(wf, h["negative"], neg_en)
                elif do_translate:
                    used.append(
                        "Übersetzung angefordert, aber kein Modell in den Valves gesetzt"
                    )
                else:
                    used.append("ohne Übersetzung")

                # --- Trigger words of the active LoRAs ---
                triggers = self._triggers_for(wf, h)
                if triggers:
                    final_prompt = (
                        final_prompt.rstrip(" ,.") + ", " + ", ".join(triggers)
                    )
                    used.append("Trigger: " + ", ".join(triggers))

                self._set(wf, h["prompt"], final_prompt)
                used.append(f"Prompt: {final_prompt}")

                # --- Resolution ---
                ratio_text = flags.get("ar", "")
                megapixels = user_valves.megapixels
                if flags.get("mp"):
                    try:
                        megapixels = float(flags["mp"].replace(",", "."))
                    except ValueError:
                        pass

                if h.get("resolution"):
                    node = wf[h["resolution"]]["inputs"]
                    if ratio_text:
                        node["aspect_ratio"] = ratio_text
                        used.append(
                            f"Format {ratio_text}"
                            + (f" (aus Bild {ar_from_image})" if ar_from_image else "")
                        )
                    if megapixels > 0:
                        node["megapixels"] = megapixels
                        used.append(f"{megapixels} MP")
                elif h.get("dimension_nodes"):
                    targets = h["dimension_nodes"]
                    lead = wf[h.get("latent") or targets[0]]["inputs"]
                    ratio = self._aspect(ratio_text) if ratio_text else None
                    if ratio or megapixels > 0:
                        cur_w = float(lead.get("width", 1024))
                        cur_h = float(lead.get("height", 1024))
                        ratio = ratio or (cur_w / cur_h)
                        total = (megapixels or (cur_w * cur_h / 1_000_000)) * 1_000_000
                        w = int(round(math.sqrt(total * ratio) / 16) * 16)
                        hh = int(round((total / max(w, 1)) / 16) * 16)
                        for nid in targets:
                            wf[nid]["inputs"]["width"] = w
                            wf[nid]["inputs"]["height"] = hh
                        extra = (
                            f" (in {len(targets)} Knoten gesetzt)"
                            if len(targets) > 1
                            else ""
                        )
                        if ar_from_image:
                            extra += f" (Format aus Bild {ar_from_image})"
                        used.append(f"{w}x{hh}{extra}")

                if not h.get("outputs"):
                    return (
                        f"**{name}** enthält keinen Bild-Ausgabeknoten (SaveImage oder "
                        "PreviewImage) — ComfyUI würde den Bildzweig gar nicht erst "
                        "ausführen.\n\nMeist ist der Knoten beim Export stummgeschaltet "
                        "oder überbrückt gewesen. In ComfyUI prüfen, dass er aktiv ist, "
                        "und den Workflow neu als API exportieren."
                    )

                # --- Submit the job (exactly one second attempt on abort) ---
                attempts = 2 if self.valves.retry_on_error else 1
                history = None
                error_status = None
                for attempt in range(1, attempts + 1):
                    if attempt > 1:
                        used.append(
                            "Erster Versuch von ComfyUI abgebrochen — automatisch wiederholt"
                        )
                        await self._emit(
                            __event_emitter__,
                            f"{name}: Abbruch, zweiter Versuch läuft ...",
                        )
                    else:
                        await self._emit(
                            __event_emitter__, f"{name}: Auftrag geht raus ..."
                        )

                    async with session.post(
                        f"{base}/prompt", json={"prompt": wf}
                    ) as resp:
                        if resp.status != 200:
                            detail = await resp.text()
                            return (
                                f"ComfyUI hat den Auftrag abgelehnt (HTTP {resp.status}):\n\n"
                                f"```\n{_clip_middle(detail)}\n```"
                            )
                        submitted = await resp.json()
                        prompt_id = submitted["prompt_id"]
                        node_errors = submitted.get("node_errors") or {}
                        if node_errors and attempt == 1:
                            problems = []
                            for nid, err in node_errors.items():
                                title = (wf.get(nid, {}).get("_meta") or {}).get(
                                    "title", ""
                                )
                                label = (
                                    f"{nid} ({wf.get(nid, {}).get('class_type', '?')}"
                                )
                                label += f", {title})" if title else ")"
                                for detail in err.get("errors") or []:
                                    problems.append(
                                        f"- {label}: {detail.get('message', '?')} "
                                        f"{detail.get('details', '')}".rstrip()
                                    )
                            used.append(
                                "ComfyUI hat Knoten beanstandet — der betroffene Zweig "
                                "läuft nicht:\n" + "\n".join(problems)
                            )

                    history = None
                    started = time.monotonic()
                    try:
                        while True:
                            elapsed = time.monotonic() - started
                            if (
                                self.valves.timeout_seconds
                                and elapsed > self.valves.timeout_seconds
                            ):
                                break  # v0.13.1: 0 = no compute cap
                            async with session.get(
                                f"{base}/history/{prompt_id}"
                            ) as resp:
                                data = await resp.json()
                            if prompt_id in data:
                                history = data[prompt_id]
                                break
                            position = await self._queue_position(
                                session, base, prompt_id
                            )
                            if position:
                                text = f"{name}: wartet, Position {position} in der Warteschlange"
                            else:
                                suffix = " (2. Versuch)" if attempt > 1 else ""
                                text = f"{name}: rechnet{suffix} ... ({int(elapsed)} s)"
                            await self._emit(__event_emitter__, text)
                            await asyncio.sleep(1.5)
                    except asyncio.CancelledError as e:
                        # Stop button in Open WebUI: withdraw the job from
                        # ComfyUI. shield, so the cleanup completes even on a
                        # second cancel.
                        e.comfy_note = await asyncio.shield(
                            self._abort_job(base, prompt_id)
                        )
                        raise

                    if history is None:
                        return "Zeitüberschreitung: ComfyUI hat den Auftrag nicht abgeschlossen."

                    status = history.get("status", {})
                    if status.get("status_str") != "error":
                        error_status = None
                        break
                    # Abort: retry silently the first time, report otherwise
                    error_status = status

                if error_status is not None:
                    prefix = (
                        "ComfyUI meldet einen Fehler"
                        if attempts == 1
                        else "ComfyUI meldet einen Fehler (auch beim zweiten Versuch)"
                    )
                    return (
                        f"{prefix}:\n\n```\n"
                        f"{_clip_middle(json.dumps(error_status, indent=2, ensure_ascii=False))}\n```"
                        + _RESET_HINT
                    )

                outputs = history.get("outputs", {}) or {}

                refined = None
                if h.get("prompt_result"):
                    entry = outputs.get(h["prompt_result"]) or {}
                    for key in ("text", "string", "value", "result"):
                        val = entry.get(key)
                        if isinstance(val, list) and val:
                            val = val[0]
                        if isinstance(val, str) and val.strip():
                            refined = val.strip()
                            break

                images = []
                for out in outputs.values():
                    for key in ("images", "result", "ui_images"):
                        entries = out.get(key) or []
                        if isinstance(entries, dict):
                            entries = entries.get("images") or []
                        for entry in entries:
                            if isinstance(entry, dict) and entry.get("filename"):
                                images.append(entry)
                if not images:
                    detail = {
                        nid: sorted((outputs.get(nid) or {}).keys()) for nid in outputs
                    }
                    hint = ""
                    if outputs:
                        hint = (
                            "\n\nHäufigste Ursache: **ComfyUIs Zwischenspeicher**. Wenn sich "
                            "gegenüber dem letzten Auftrag kein einziger Wert geändert hat — "
                            "typischerweise durch einen fest gespeicherten Seed — rechnet ComfyUI "
                            "nichts neu und meldet die Bilder nicht erneut."
                        )
                    if not outputs:
                        hint = (
                            "\n\nComfyUI hat gar keine Ausgaben gemeldet. Das passiert, wenn der "
                            "Workflow keinen SaveImage- oder PreviewImage-Knoten enthält oder wenn "
                            "der Ausgabezweig im Export deaktiviert (bypassed) war."
                        )
                    return (
                        "ComfyUI ist durchgelaufen, hat aber kein Bild zurückgegeben."
                        f"{hint}\n\nGemeldete Ausgaben je Knoten:\n\n```\n"
                        f"{_clip_middle(json.dumps(detail, indent=1, ensure_ascii=False), 1500)}\n```"
                        + _RESET_HINT
                    )

                await self._emit(__event_emitter__, "Bilder werden abgeholt ...")
                blocks = []
                store_error = None
                for img in images:
                    params = {
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                    }
                    async with session.get(f"{base}/view", params=params) as resp:
                        data = await resp.read()

                    url = None
                    if self.valves.store_images_as_files:
                        url, err = await self._store_image(
                            data, img["filename"], user_id
                        )
                        if err and not store_error:
                            store_error = err
                    if url:
                        blocks.append(f"![{img['filename']}]({url})")
                    else:
                        b64 = base64.b64encode(data).decode()
                        blocks.append(
                            f"![{img['filename']}](data:image/png;base64,{b64})"
                        )

                if store_error:
                    used.append(f"Dateiablage übersprungen ({store_error})")
                if _slot_ctx["state"].get("lost"):
                    used.append(
                        "Hinweis: die GPU-Slot-Lease war zwischenzeitlich verfallen "
                        "(Alpaka neu gestartet?) — der Auftrag lief trotzdem weiter"
                    )

                await self._emit(__event_emitter__, "Fertig", done=True)
                out = "\n\n".join(blocks)
                if refined:
                    out += f"\n\n---\n\n**Verwendeter Prompt:**\n\n{refined}"
                if defaults and user_valves.show_prompt:
                    parts = []
                    for k, v in defaults.items():
                        if k in msg_flags and str(msg_flags[k]) != str(v):
                            parts.append(
                                f"--{k} {msg_flags[k]} (Vorgabe {v} übersteuert)".rstrip()
                            )
                        else:
                            parts.append(f"--{k} {v}".rstrip())
                    used.append("Vorgaben: " + ", ".join(parts))
                if user_valves.show_prompt and used:
                    out += "\n\n---\n\n*" + " · ".join(used) + "*"
                return out

        except asyncio.TimeoutError:
            return "Zeitüberschreitung bei der Verbindung zu ComfyUI."
        except aiohttp.ClientError as e:
            return f"Verbindung zu ComfyUI fehlgeschlagen: {e}"
