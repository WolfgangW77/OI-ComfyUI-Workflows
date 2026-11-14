"""
title: OI-ComfyUI-Workflows
author: Wolfgang Weber (WolfgangW77 on github)
version: 0.15.0
license: MIT
description: Exposes every API-format ComfyUI workflow in a directory as its own model - prompt flags (--ar, --no, --steps ...), image series from an LLM-written prompt list (--serie, --los; the LLM sees the input image of image workflows; optional spoken commands at the end of a dictation), optional prompt translation via Ollama, GPU sharing via the Alpaka Ollama Log Proxy (slot v5.3+, --handover v5.4+).
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

v0.13.3
- A job that ends abnormally is now withdrawn from ComfyUI before the
  GPU slot is released. Until now only the stop button did that: when
  the compute cap (timeout_seconds) struck, or the connection to
  ComfyUI broke while waiting for the result, the pipe returned, its
  finally block released the slot - and ComfyUI kept rendering while
  Alpaka already handed the GPU to the next chat. Both paths now call
  the same clean-up as the stop button (_abort_job: pending -> deleted
  from the queue, running -> /interrupt, only if it is our own
  prompt_id) and append its result to the message. If the clean-up
  fails as well (ComfyUI unreachable), the message says so and the
  behaviour is as before. Errors before submission and after the
  result has arrived need no clean-up and are unchanged.
- Default of the admin valve ollama_url is now the Alpaka port
  (http://host.docker.internal:11435), matching use_alpaka_proxy = on;
  saved valve values are not affected. The valve description names
  both cases (Alpaka or Ollama directly).
- Stored and inline images carry the MIME type of their file name
  (PNG, JPEG, WebP, GIF) instead of always image/png - relevant for
  SaveAnimatedWEBP outputs.
- Fix: --triggers 0/1 now works. It was documented in the manual and
  accepted as a known flag, but never evaluated - matching trigger
  words were always appended. Default stays on; --triggers 0 switches
  them off for one message or as a saved default, a bare --triggers
  resets as usual. The info line lists the suppressed trigger words.
- The description in the header is a single line now. Open WebUI's
  header parser reads "key: value" line by line, so only the first line
  of the old multi-line description reached the function list. It now
  also names the Alpaka versions (slot v5.3+, --handover v5.4+).
- Small fixes: author line in the header per the publishing format,
  admin manual ("Alle laufen pipe-lokal" - there are five clean-up
  commands now; the run-time note names Alpaka's file-head constants
  explicitly), dead statement removed from the --help builder.

v0.14.0
- Image series. "brief --serie N" lets an Ollama model (admin valve
  series_model) write N English image prompts as a numbered list in the
  chat; "--los" renders the latest list, "--los 1,3,7" a selection,
  "--serie N --nowait" renders right away. The list can be edited with
  Open WebUI's edit function before "--los" - the visible text is read
  back from the chat history (header "**Prompt-Serie**", one line per
  prompt, "N. [ratio] text"). N defaults to 10, capped by series_max
  (default 20, counts prompts, not images).
- Prompt list request: /api/generate via ollama_url WITHOUT a GPU slot
  (a normal Alpaka request), streamed, with a JSON schema in "format";
  the status line counts words while it arrives ("~3.200 Wörter") or
  shows "denkt nach". Same fallback chain as the translation (think
  off, no think field, instruction inside the prompt). No read timeout
  (the request may wait in Alpaka's queue); done_reason "length" or
  cut-off JSON gives a clear "Antwort abgeschnitten" message. New admin
  valves series_model, series_keep_alive (default "0"), series_num_ctx
  (0 = Ollama/model setting), series_system (instruction text, without
  a fixed word range), series_max, series_ar_options.
- Prompt length: user valve series_words (default 60, 0 = no target,
  max 500) and flag --words N (message > saved default > user valve);
  the list header shows target and achieved average.
- Format of a series: --ar (message or saved default) > input image >
  aspect_ratio user valve > the LLM per prompt (enum of the workflow's
  ResolutionSelector entries, or series_ar_options for plain width/height
  workflows) > workflow file. A fixed format is named once in the header
  ("Format: 16:9, fixiert über User-Valve") and the LLM is not asked.
- All other flags are taken 1:1 from the user for every image; flags on
  the --los message override those of the --serie message, which
  override saved defaults. An image attached to --los replaces the one
  of the --serie message (Open WebUI resends older images as base64). A
  fixed seed applies to every image, otherwise each gets a new one;
  --batch applies per prompt; translation is off in series mode; the
  model's system prompt goes to the prompt LLM as fixed requirements.
- Rendering: one GPU slot for the whole series (label "<workflow>
  (Serie N)"). _run returns an async generator for --los/--nowait, which
  Open WebUI streams, so every image appears as soon as it is done. The
  generator owns slot release and the closing status line, since
  pipe()'s finally block runs before it starts. A failed image (ComfyUI
  error, compute cap, no image, rejection) is reported and the series
  continues; 3 failures in a row or ComfyUI unreachable end it; the stop
  button ends it with the running job withdrawn. Finished images stay.
- Refactoring: the render core (submit, wait, retry, withdraw on compute
  cap or connection loss, fetch, store) moved from _run into
  _render_job, which returns a result instead of a finished message;
  preparation (_apply_static, _prepare_in_session), resolution
  (_apply_resolution) and trigger words (_active_triggers) are shared
  helpers. The single-image path produces the same output as before.
- --help and --anleitung describe the series; serie, nowait, los and
  words are reserved flag names (no colliding marker lister).
- Fix (--help, admin part): --handover-comfy 0/1 and --handover-ollama
  0/1 are now in backticks like every other command, so they can be
  copied with a click.

v0.14.1
- Format ban: every prompt-list request ends with "Do not mention aspect
  ratio, image size or image format in the prompt text." - appended by
  the pipe, not part of the valve texts, so it also reaches saved older
  texts. (The live test showed "Aspect ratio 3:2." inside a prompt while
  the format was fixed by the user valve.) A format chosen by the LLM
  still goes into the JSON field "ar".
- Format label in the short form above AND below every image:
  "Format 1:1 (User-Valve)", "(--ar)", "(Vorgabe)", "(Bild-Input)",
  "(LLM)", or "Format wie Workflow". Fixes "Format Workflow-Format
  (Workflow)" and the nested brackets for the input image. The list
  header keeps the long form.
- "--serie N --los" works like "--serie N --nowait"; numbers after --los
  are ignored there with a note (a selection only makes sense for an
  existing list). Before, the combination was refused.
- Image workflows: the input image now goes to the prompt LLM.
  - Workflows with an image input need the image on the --serie message;
    without it the pipe stops right away with the single-image message,
    before any prompt is written (v0.14.0 wrote a list about nothing).
  - Vision check first: POST /api/show via ollama_url; no "vision" in
    capabilities -> clear message, no list; check not possible -> the
    image goes anyway, with a note. Same timeouts as the prompt request.
  - Images with a longest side above 1536 px are scaled down (JPEG 90,
    EXIF orientation applied, large JPEGs decoded at reduced scale);
    smaller ones go unchanged; without Pillow the original goes.
  - --bildart edit|control (value flag, storable per workflow, default
    edit) picks the instruction: new admin valves series_system_edit
    (short edit instructions - the edit model sees the photo) and
    series_system_control (describe the subject of the photo - structure
    workflows like depth only see its shape). The list header names it
    ("Bildart: edit") when an image went to the LLM. --bildart on a
    workflow without image input is ignored with a note; on --los it has
    no effect (note), on a single image it is noted in the info line.
- --words and --bildart are checked in the shared validation stage
  (_normalize), i.e. already when saved as defaults (principle since
  v0.6.0): --words must be a number from 0, --bildart edit or control.

v0.15.0
- Spoken commands (user valve voice_commands, default off): a dictated
  text (Whisper STT, often without punctuation) may end with commands
  after the signal word "Serie" - count (a number right after "Serie",
  or "zehn Bilder", "10 Prompts", "5 Stück"), length ("130 Worte"),
  "Querformat" (16:9), "Hochformat" (9:16), "quadratisch" (1:1),
  "sofort starten" / "sofort" (--nowait), "los" with optional numbers
  (--los 1,3,5). Digits or German number words up to 500; fillers (und,
  bitte, mit, je, von, im, in, als, jeweils, lang, Nummer) and
  punctuation are skipped. The last "Serie" directly followed by a
  command starts the command part; everything after it must be
  understood, otherwise the pipe stops with a message naming the unknown
  words (no LLM request, no slot). "Serie los" without a brief renders
  the latest list, with a brief it works like --nowait. Typed flags win
  (with a note). The generated flags behave exactly like typed ones and
  are shown as a note ("Sprachbefehle: ..."); --los re-reads the --serie
  message with the same recognition, so a dictated format still applies.
- Total length hint (planned as v0.14.2, merged into this version): with
  a target length, when prompts x words reaches the new admin valve
  series_total_hint (default 600, 0 = off), the list request adds "In
  total about 2,400 words are expected (20 prompts x about 120 words). A
  long answer is fine - do not shorten individual prompts to save
  space." Models tend to shorten the single prompts of long lists
  (gemma4: 20 x 120 words gave an average of 68). With show_prompt the
  info line notes that the hint was sent.
- Flags start with "--" or the em dash (U+2014, Open WebUI turns "--"
  into it) only; the en dash (U+2013) no longer starts a flag - it did
  so before, undocumented.
"""

import asyncio
import base64
import copy
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

# --- Image series (v0.14.0) ---
DEFAULT_SERIES_SYSTEM = (
    "You write prompts for the text-to-image model Krea 2. You receive a brief, a "
    "number N and optionally a target length, fixed requirements and a list of allowed "
    "aspect ratios. Write exactly N clearly different prompts that all fulfil the brief "
    "and vary it in subject detail, setting, composition, lighting and mood. Write "
    "every prompt in English as natural descriptive language: start with the overall "
    "style or medium (e.g. photo, oil painting), then the main subject, setting, "
    "composition and camera, lighting and mood. No keyword lists, no weights, no "
    "quality tags, no negative prompts. Never add trigger words, LoRA names or anything "
    "starting with --. If a target length is given, keep every prompt close to it. If "
    "fixed requirements are given, honour them in every prompt. If allowed aspect ratios "
    "are given, pick for every prompt the one that fits its composition best. Reply "
    "only with the JSON object."
)
SERIES_FLAGS = {"serie", "nowait", "los"}  # commands, never stored as defaults
SERIES_DEFAULT_COUNT = 10  # --serie without a number
SERIES_WORDS_MAX = 500  # upper bound for --words / series_words
SERIES_FAIL_STREAK = 3  # failed images in a row that end a series
# v0.14.1: appended by the pipe to every list request (not part of the
# valve texts, so it also reaches installations with older saved texts)
SERIES_FORMAT_BAN = (
    "Do not mention aspect ratio, image size or image format in the prompt text."
)
SERIES_IMAGE_MAX = 1536  # longest side of the image sent to the prompt LLM
BILDART_VALUES = ("edit", "control")  # --bildart; first entry is the default
DEFAULT_SERIES_SYSTEM_EDIT = (
    "You write edit instructions for an image-editing model. An input image is "
    "attached; the editing model sees this image and applies one instruction at a "
    "time. You receive a brief, a number N and optionally a target length, fixed "
    "requirements and a list of allowed aspect ratios. Look at the image carefully. "
    "Write exactly N clearly different instructions that each fulfil the brief. Every "
    "instruction says precisely what to change and what must stay the same (for "
    "example: keep the subject, its pose and its identity unchanged), referring to "
    "elements that are visible in the image. Write in English as plain imperative "
    "sentences. No keyword lists, no weights, no quality tags. Never add trigger "
    "words, LoRA names or anything starting with --. If a target length is given, keep "
    "every instruction close to it. If fixed requirements are given, honour them in "
    "every instruction. If allowed aspect ratios are given, pick for every instruction "
    "the one that fits best. Reply only with the JSON object."
)
DEFAULT_SERIES_SYSTEM_CONTROL = (
    "You write prompts for the text-to-image model Krea 2. It is guided by the "
    "structure (depth or pose) of an attached input image but does not see its "
    "colours, textures or details. You receive a brief, a number N and optionally a "
    "target length, fixed requirements and a list of allowed aspect ratios. Look at "
    "the image carefully. Write exactly N clearly different prompts that all fulfil "
    "the brief. Every prompt describes the main subject of the image concretely - "
    "species or type, colours, markings, clothing, distinctive features - so that it "
    "stays recognisable, keeps its pose, and then applies the brief to setting, "
    "season, lighting, style and mood. Write every prompt in English as natural "
    "descriptive language: start with the overall style or medium, then the subject, "
    "setting, lighting and mood. No keyword lists, no weights, no quality tags, no "
    "negative prompts. Never add trigger words, LoRA names or anything starting with "
    "--. If a target length is given, keep every prompt close to it. If fixed "
    "requirements are given, honour them in every prompt. If allowed aspect ratios "
    "are given, pick for every prompt the one that fits its composition best. Reply "
    "only with the JSON object."
)
LIST_HEADER = "**Prompt-Serie**"  # first line of a prompt list in the chat
# One list entry: "3. [16:9] text" or "3. text" (also "3)")
LIST_LINE_RE = re.compile(r"^\s*(\d+)[.)]\s+(?:\[([^\]]*)\]\s*)?(.*\S)\s*$")
# v0.15.0: total length hint, appended when prompts x words >= series_total_hint
SERIES_TOTAL_HINT = (
    "In total about {total:,} words are expected ({n} {prompts} × about {words} "
    "words). A long answer is fine – do not shorten individual prompts to save space."
)

# --- Spoken commands (v0.15.0) ---
# A dictated text may end with "Serie" plus commands; see _voice_parse.
VOICE_SIGNAL = "serie"
VOICE_PUNCT = ".,;:!?"  # stripped from both ends of every word
VOICE_FILLERS = {
    "und", "bitte", "mit", "je", "von", "im", "in", "als", "jeweils", "lang",
    "nummer", "nummern",
}
VOICE_COUNT_UNITS = {"bilder", "bildern", "bild", "prompts", "prompt", "stück"}
VOICE_WORD_UNITS = {"worte", "wörter", "worten", "wörtern"}
VOICE_FORMATS = {"querformat": "16:9", "hochformat": "9:16", "quadratisch": "1:1"}
_DE_UNITS = {
    "ein": 1, "eins": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}
_DE_TEENS = {
    "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14,
    "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
}
_DE_TENS = {
    "zwanzig": 20, "dreißig": 30, "dreissig": 30, "vierzig": 40, "fünfzig": 50,
    "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90,
}
_DE_COMPOUND_RE = re.compile(
    r"(ein|zwei|drei|vier|fünf|sechs|sieben|acht|neun)und("
    + "|".join(_DE_TENS)
    + r")"
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


def _de_below_100(word: str) -> Optional[int]:
    if word in _DE_UNITS:
        return _DE_UNITS[word]
    if word in _DE_TEENS:
        return _DE_TEENS[word]
    if word in _DE_TENS:
        return _DE_TENS[word]
    m = _DE_COMPOUND_RE.fullmatch(word)
    if m:
        return _DE_UNITS[m.group(1)] + _DE_TENS[m.group(2)]
    return None


def _de_number(word: str) -> Optional[int]:
    """A number given as digits or as a German number word below 1000
    ("zwölf", "dreiundzwanzig", "hundertzwanzig", "einhundertfünfzig").
    None if the word is no number. (v0.15.0)"""
    word = word.lower()
    if re.fullmatch(r"[0-9]+", word):
        return int(word)
    if "hundert" in word:
        pre, _sep, post = word.partition("hundert")
        if pre in ("", "ein"):
            hundreds = 1
        elif pre in _DE_UNITS and pre != "eins":
            hundreds = _DE_UNITS[pre]
        else:
            return None
        if post.startswith("und"):
            post = post[3:]  # "hundertundzwanzig"
        rest = _de_below_100(post) if post else 0
        if rest is None:
            return None
        return hundreds * 100 + rest
    return _de_below_100(word)


def _voice_parse(text: str) -> Optional[dict]:
    """Spoken commands at the end of a dictated text (v0.15.0).

    The command part starts at the last "Serie" that is directly followed
    (after fillers) by a command; everything after it must be a command or
    a filler. Case and punctuation at the words do not matter - Whisper
    often sets no punctuation at all. Returns None when there is no
    command part, otherwise a dict with
      prompt  - the text before the command part
      flags   - the generated flags (serie, los, words, ar, nowait)
      spoken  - flag -> spoken words, for notes
      unknown - words that were not understood (non-empty = stop)
      tail    - the command part as dictated
    """
    tokens = []
    for m in re.finditer(r"\S+", text):
        tokens.append((m.group(0).strip(VOICE_PUNCT).lower(), m.start(), m.group(0)))

    def is_command_start(word: str) -> bool:
        return (
            _de_number(word) is not None
            or word in VOICE_FORMATS
            or word in ("sofort", "los")
        )

    def skip_fillers(j: int) -> int:
        while j < len(tokens) and (not tokens[j][0] or tokens[j][0] in VOICE_FILLERS):
            j += 1
        return j

    start = None
    for i, (word, _pos, _orig) in enumerate(tokens):
        if word != VOICE_SIGNAL:
            continue
        j = skip_fillers(i + 1)
        if j < len(tokens) and is_command_start(tokens[j][0]):
            start = i

    if start is None:
        return None

    count = words = ar = None
    nowait = los = False
    selection: list = []
    spoken: dict = {}
    unknown: list = []
    first = True  # no command read yet: a bare number is the count
    in_selection = False  # numbers right after "los" select list entries
    k = start + 1
    while k < len(tokens):
        word, _pos, orig = tokens[k]
        shown = orig.strip(VOICE_PUNCT)
        if not word or word in VOICE_FILLERS:
            k += 1
            continue
        nxt = tokens[k + 1][0] if k + 1 < len(tokens) else ""
        number = _de_number(word)
        if number is not None and nxt in VOICE_COUNT_UNITS:
            count = number
            spoken["serie"] = f"{shown} {tokens[k + 1][2].strip(VOICE_PUNCT)}"
            in_selection = False
            k += 2
        elif number is not None and nxt in VOICE_WORD_UNITS:
            words = number
            spoken["words"] = f"{shown} {tokens[k + 1][2].strip(VOICE_PUNCT)}"
            in_selection = False
            k += 2
        elif number is not None and in_selection:
            selection.append(number)
            k += 1
        elif number is not None and first:
            count = number
            spoken["serie"] = f"Serie {shown}"
            k += 1
        elif in_selection and re.fullmatch(r"[0-9]+(?:,[0-9]+)+", word):
            selection.extend(int(x) for x in word.split(","))
            k += 1
        elif word in VOICE_FORMATS:
            ar = VOICE_FORMATS[word]
            spoken["ar"] = shown
            in_selection = False
            k += 1
        elif word == "sofort":
            nowait = True
            spoken["nowait"] = shown
            in_selection = False
            k += 1
            if k < len(tokens) and tokens[k][0] == "starten":
                spoken["nowait"] = f"{shown} {tokens[k][2].strip(VOICE_PUNCT)}"
                k += 1
        elif word == "los":
            los = True
            in_selection = True
            k += 1
        else:
            unknown.append(shown)
            in_selection = False
            k += 1
        first = False

    prompt = text[: tokens[start][1]].rstrip()
    while prompt and prompt[-1] in ",;:":
        prompt = prompt[:-1].rstrip()
    selection_text = ",".join(str(x) for x in selection)
    if los:
        spoken["los"] = ("los " + " ".join(str(x) for x in selection)).strip()

    flags: dict = {}
    if los and not prompt and count is None:
        # "Serie los": render the latest list; "sofort" means the same here
        flags["los"] = selection_text
        if words is not None:
            flags["words"] = str(words)
        if ar:
            flags["ar"] = ar
    else:
        flags["serie"] = str(count) if count is not None else ""
        if los:
            flags["los"] = selection_text
        if words is not None:
            flags["words"] = str(words)
        if ar:
            flags["ar"] = ar
        if nowait:
            flags["nowait"] = ""
    spoken.setdefault("serie", "Serie")
    return {
        "prompt": prompt,
        "flags": flags,
        "spoken": spoken,
        "unknown": unknown,
        "tail": text[tokens[start][1] :].strip(),
    }


# v0.15.0: "--" or the em dash Open WebUI makes of it; the en dash no
# longer starts a flag
FLAG_RE = re.compile(r"(?:--|\u2014)\s*([a-zA-Z][a-zA-Z0-9_-]*)")

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
    "serie",
    "nowait",
    "los",
}  # admin clean-up + handover + image series (v0.14.0)

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


_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _mime_for(filename: str) -> str:
    """MIME type from the file name; unknown endings count as PNG. (v0.13.3)"""
    return _MIME_BY_SUFFIX.get(Path(filename or "").suffix.lower(), "image/png")


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
                "Rechen-Deckel ab Auftragsübermittlung; bei Überschreitung "
                "wird der Auftrag bei ComfyUI zurückgezogen. 0 = kein Deckel "
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
            default="http://host.docker.internal:11435",
            description=(
                "Basis-URL für die Prompt-Übersetzung und die Prompt-Liste der "
                "Bildserien: mit Alpaka die Proxy-URL (Standard, Port 11435), "
                "ohne Alpaka Ollama direkt (üblicherweise Port 11434)."
            ),
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
        # --- Image series (v0.14.0) ---
        series_model: str = Field(
            default="",
            description=(
                "Ollama-Modell, das bei --serie die Prompt-Liste schreibt. "
                "Leer = Serienmodus nicht verfügbar."
            ),
        )
        series_keep_alive: str = Field(
            default="0",
            description=(
                "Wie lange das Prompt-Modell nach der Liste im VRAM bleibt. "
                "'0' = sofort entladen (danach folgt ohnehin GPU-Arbeit)."
            ),
        )
        series_num_ctx: int = Field(
            default=0,
            description=(
                "Kontextgröße (num_ctx) der Prompt-Anfrage. 0 = Einstellung von "
                "Ollama bzw. des Modells."
            ),
        )
        series_system: str = Field(
            default=DEFAULT_SERIES_SYSTEM,
            description=(
                "Anweisung an das Prompt-Modell (Workflows ohne Bildeingang). Anzahl, "
                "Länge, Format-Verbot, feste Vorgaben und erlaubte Formate hängt die "
                "Pipe selbst an."
            ),
        )
        series_system_edit: str = Field(
            default=DEFAULT_SERIES_SYSTEM_EDIT,
            description=(
                "Anweisung an das Prompt-Modell bei Workflows mit Bildeingang und "
                "--bildart edit (Standard): kurze Änderungsanweisungen zum Foto."
            ),
        )
        series_system_control: str = Field(
            default=DEFAULT_SERIES_SYSTEM_CONTROL,
            description=(
                "Anweisung an das Prompt-Modell bei Workflows mit Bildeingang und "
                "--bildart control: das Motiv aus dem Foto beschreiben, Vorgabe umsetzen."
            ),
        )
        series_max: int = Field(
            default=20,
            description=(
                "Obergrenze für --serie N. Zählt Prompts, nicht Bilder "
                "(--batch gilt je Prompt)."
            ),
        )
        series_ar_options: str = Field(
            default="1:1, 4:3, 3:4, 3:2, 2:3, 16:9, 9:16",
            description=(
                "Formate, aus denen das Prompt-Modell bei Workflows ohne "
                "ResolutionSelector (nur Breite/Höhe) wählt; kommagetrennt."
            ),
        )
        series_total_hint: int = Field(
            default=600,
            description=(
                "Bildserien: ab dieser Gesamtlänge (Prompts × Wörter) bittet die Pipe "
                "das Prompt-Modell ausdrücklich, die einzelnen Prompts nicht zu "
                "kürzen. 0 = aus."
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
        series_words: int = Field(
            default=60,
            description=(
                "Bildserien: ungefähre Länge je Prompt in englischen Wörtern. "
                "0 = keine Vorgabe, höchstens 500. Einmalig per --words."
            ),
        )
        voice_commands: bool = Field(
            default=False,
            description=(
                "Gesprochene Befehle am Ende eines Diktats (Signalwort „Serie“) "
                "in Kürzel umsetzen."
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
        messages = body.get("messages") or []
        if not messages:
            return []
        return self._images_from_message(messages[-1])

    def _images_from_message(self, message: dict) -> list:
        """Collect attached images as (bytes, file name) from one message.
        v0.14.0: split out of _extract_images so that --los can take the
        image of the earlier --serie message (Open WebUI resends images of
        older user messages as base64 data URLs)."""
        import base64 as _b64

        content = (message or {}).get("content", "")
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
        for entry in (message or {}).get("images") or []:
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

        # --- Series values (v0.14.1): same check when saving and using ---
        out, more = self._check_series_values(out)
        notes += more
        return out, notes

    @staticmethod
    def _check_series_values(values: dict):
        """--words must be a number from 0, --bildart edit or control.
        Invalid values are dropped with a note. Part of the shared
        validation stage (saving defaults AND using them, see v0.6.0); also
        called directly by the series list phase. (v0.14.1)"""
        out = dict(values)
        notes: list[str] = []
        if "words" in out and str(out["words"]).strip():
            text = str(out["words"]).strip()
            try:
                number = int(float(text.replace(",", ".")))
            except ValueError:
                number = -1
            if number < 0:
                out.pop("words")
                notes.append(f"--words {text}: keine Zahl ab 0 — nicht übernommen")
            else:
                out["words"] = str(number)
        if "bildart" in out and str(out["bildart"]).strip():
            text = str(out["bildart"]).strip()
            if text.lower() in BILDART_VALUES:
                out["bildart"] = text.lower()
            else:
                out.pop("bildart")
                notes.append(
                    f"--bildart {text}: unbekannt — erlaubt: "
                    + ", ".join(BILDART_VALUES)
                )
        return out, notes

    async def _normalize_standalone(self, wf: dict, h: dict, values: dict):
        """Like _normalize, but opens its own short connection."""
        base = self.valves.comfy_url.rstrip("/")
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                return await self._normalize(session, base, wf, h, values)
        except Exception as e:
            # v0.14.1: the series values need no ComfyUI - check them anyway
            checked, more = self._check_series_values(values)
            return checked, [
                f"ComfyUI nicht erreichbar ({e}) — ungeprüft gespeichert"
            ] + more

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
                        "content_type": _mime_for(safe),
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
            # v0.14.0: image series - reserved, so that e.g. a PIPE_WORD
            # marker does not produce a colliding --words lister
            "serie",
            "nowait",
            "los",
            "words",
            "bildart",  # v0.14.1
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
            "serie",  # v0.14.0: image series
            "nowait",  # v0.14.0: image series
            "los",  # v0.14.0: image series
            "words",  # v0.14.0: image series (prompt length)
            "bildart",  # v0.14.1: image series (edit/control)
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

    async def _acquire_slot(
        self, emitter, name: str, tag: str, status_label: Optional[str] = None
    ):
        """Blocking acquire with position display. Returns (slot_id, err).
        A user abort cancels the request - Alpaka's socket peek then
        removes the waiting entry by itself. Waiting is deliberately NOT
        bounded by timeout_seconds (slot specification).
        name is the slot label at Alpaka; status_label (v0.14.0) replaces it
        in the status line, e.g. "Serie" for a series slot."""
        shown = status_label or name
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
                                f"{shown}: wartet auf freie GPU — "
                                f"Position {pos} in der Warteschlange ...",
                            )
                        else:
                            await self._emit(
                                emitter, f"{shown}: wartet auf freie GPU ..."
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
        """Withdraw our own job from ComfyUI - after a stop in Open WebUI and,
        since v0.13.3, after the compute cap or a broken connection while
        waiting for the result (so the GPU slot is not released while
        ComfyUI keeps rendering). Runs over its own short connection because
        the main session is being torn down or broken. Returns: a short text
        for the status line or message - no exception ever escapes from here.

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

    @staticmethod
    def _abort_suffix(note: str) -> str:
        """Turn an _abort_job result into a closing paragraph for the chat
        message; a failed clean-up says that ComfyUI may still be rendering.
        (v0.13.3)"""
        if not note:
            return ""
        text = note[:1].upper() + note[1:]
        if "fehlgeschlagen" in note:
            text += " — der Auftrag läuft bei ComfyUI womöglich weiter"
        return f"\n\n{text}."

    async def _withdraw_open_job(self, base: str, prompt_id: Optional[str]) -> str:
        """For the connection-error paths: withdraw a job that was accepted
        but whose result never arrived; returns the closing paragraph or ""
        if there is no such job. (v0.13.3)"""
        if not prompt_id:
            return ""
        note = await asyncio.shield(self._abort_job(base, prompt_id))
        return self._abort_suffix(note)

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

## Bildserien

Ein Sprachmodell schreibt aus einer Vorgabe mehrere englische
Bildprompts, danach werden sie nacheinander gerendert.

1. `Katze in vier Jahreszeiten, Fotostil --serie 10` -- erzeugt 10
   Prompts und zeigt sie als nummerierte Liste (ohne Zahl: 10).
2. Liste prüfen, bei Bedarf über die Bearbeiten-Funktion der Antwort
   ändern -- es gilt der bearbeitete Stand. Eine Zeile je Prompt.
3. `--los` rendert alle, `--los 1,3,7` nur die genannten Nummern.

| Kürzel | Wirkung |
|---|---|
| `--serie 5 --nowait` | Liste erzeugen und sofort rendern (`--serie 5 --los` wirkt genauso) |
| `--words 200` | ungefähre Länge je Prompt in englischen Wörtern (0 = keine Vorgabe, höchstens 500) |
| `--bildart edit` / `--bildart control` | nur Workflows mit Bildeingang: Änderungsanweisungen (Standard) bzw. Motivbeschreibung für Struktur-Workflows wie Depth -- am besten einmal pro Workflow als Vorgabe speichern |

- **Format:** `--ar` gilt für alle Bilder. Ohne `--ar` gilt das Format
  des angehängten Bildes, dann `aspect_ratio` aus der Chat-Steuerung --
  sonst wählt das Sprachmodell je Prompt eins (steht in der Liste in
  eckigen Klammern und lässt sich dort ändern).
- **Alle anderen Kürzel** (`--lora1`, `--seed`, `--batch` ...) gelten
  unverändert für jedes Bild. Kürzel an `--los` übersteuern die an
  `--serie`. Ein Bild an `--los` ersetzt das Bild der `--serie`-Nachricht.
- **Seed:** ein fester Seed gilt für alle Bilder der Serie, sonst bekommt
  jedes Bild einen neuen.
- **Übersetzung** entfällt -- das Sprachmodell schreibt gleich englisch.
- **Workflows mit Bildeingang:** das Foto gehört an die `--serie`-Nachricht
  (sonst bricht die Pipe gleich ab) und geht verkleinert an das
  Sprachmodell, das dafür Bilder verarbeiten können muss. `--los` nimmt
  dasselbe Foto, ein neues Foto an `--los` ersetzt es.
- Schlägt ein Bild fehl, geht es mit dem nächsten weiter; nach drei
  Fehlschlägen in Folge bricht die Serie ab. Der Stopp-Knopf beendet die
  Serie, fertige Bilder bleiben stehen.
- Die Grafikkarte bleibt für die ganze Serie belegt -- Chats warten so
  lange. Während die Liste nur angezeigt wird, ist nichts belegt.

### Sprachbefehle beim Diktat

Mit `voice_commands` in der Chat-Steuerung (Standard aus) setzt die
Pipe gesprochene Befehle am Ende eines Diktats in Kürzel um. Sie stehen
hinter dem Signalwort „Serie“:

| gesprochen | wird zu |
|---|---|
| „Serie zehn“, „zehn Bilder“, „10 Prompts“, „5 Stück“ | `--serie 10` usw. |
| „130 Worte“, „mit je 150 Wörtern“ | `--words 130` usw. |
| „Querformat“ / „Hochformat“ / „quadratisch“ | `--ar 16:9` / `--ar 9:16` / `--ar 1:1` |
| „sofort starten“, „sofort“ | `--nowait` |
| „Serie los“, „Serie los 1, 3 und 5“ | `--los`, `--los 1,3,5` |

- Beispiel: „Eine Katze läuft über eine Straße Serie 10 Bilder 130
  Worte quadratisch sofort starten“ -- die Vorgabe ist der Text davor.
- Zahlen als Ziffern oder Zahlwörter bis 500. Füllwörter („und“,
  „bitte“, „mit“, „je“, „jeweils“, „von“, „im“, „in“, „als“, „lang“,
  „Nummer“) und Satzzeichen werden übergangen.
- Es zählt das letzte „Serie“, dem direkt ein Befehl folgt; ab dort muss
  alles Befehl sein. Wird ein Teil nicht verstanden, hält die Pipe mit
  einer Meldung an. „Eine Serie von Leuchttürmen“ bleibt normaler Text.
- Steht vor „Serie los“ eine Vorgabe, wirkt „los“ wie „sofort starten“.
- Getippte Kürzel gehen vor. Die erkannten Befehle stehen als Hinweis
  bei der Liste und wirken genau wie getippte.

## Chat-Steuerung (Schieberegler-Symbol)

`translate` (Übersetzung dauerhaft an), `show_prompt` (Info-Zeile
unter dem Bild -- anfangs anschalten!), `auto_ar` (Format aus dem
angehängten Bild), `seed`, `steps`, `aspect_ratio`, `megapixels`,
`batch_size`, `series_words` (Promptlänge bei Bildserien),
`voice_commands` (Sprachbefehle beim Diktat).

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
zur Laufzeit schaltbar per `--handover`; Alpakas Dateikopf-Konstanten
sind nur die Erststart-Vorgaben.

Bildserien: `series_model` (Ollama-Modell für die Prompt-Liste; leer =
Serienmodus aus; für Workflows mit Bildeingang muss es Bilder verarbeiten
können -- die Pipe prüft das über `/api/show`), `series_keep_alive`
(Standard `0`), `series_num_ctx` (0 = Einstellung von Ollama bzw. des
Modells), `series_system` (Anweisung ans Prompt-Modell ohne Bild),
`series_system_edit` / `series_system_control` (Anweisungen mit Bild je
nach `--bildart`; Anzahl, Länge, Format-Verbot, feste Vorgaben und
Formate hängt die Pipe jeweils selbst an), `series_max` (Obergrenze für `--serie N`,
zählt Prompts), `series_ar_options` (Formatauswahl für Workflows ohne
ResolutionSelector), `series_total_hint` (ab dieser Gesamtlänge
Prompts × Wörter bittet die Pipe das Prompt-Modell ausdrücklich, die
einzelnen Prompts nicht zu kürzen; Standard 600, 0 = aus). Die
Prompt-Anfrage läuft ohne GPU-Slot als normale
Anfrage über `ollama_url`; der Slot wird erst zum Rendern gezogen und
dann für die ganze Serie gehalten. Ein Systemprompt am Workspace-Modell
geht bei Serien als feste Vorgabe an das Prompt-Modell.

## Aufräum-Kommandos (nur Admins)

| Kürzel | Wirkung |
|---|---|
| `--kill-ollama-tasks` | bricht alle laufenden Ollama-Anfragen über den Alpaka-Proxy ab |
| `--unload-ollama [name]` | entlädt Ollama-Modelle per keep_alive 0 (ohne Name: alle) |
| `--unload-comfy` | gibt ComfyUIs Speicher frei (Modelle entladen, Cache leeren) |
| `--handover [on/off/custom]` | zeigt (ohne Wert) oder setzt Alpakas Saubere Übergabe |
| `--handover-comfy 0/1`, `--handover-ollama 0/1` | Einzelschalter je Richtung (stellt automatisch auf custom) |

Alle laufen pipe-lokal: kein GPU-Slot, keine Übersetzung, kein
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
        voice: bool = False,
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
            "**Bildserien:** `Vorgabe --serie 10` lässt ein Sprachmodell eine Prompt-Liste "
            "schreiben (Länge je Prompt: `--words 200`), `--los` rendert sie, `--los 1,3,7` "
            "nur die genannten Nummern, `--serie 5 --nowait` (oder `--serie 5 --los`) sofort. "
            + (
                "Bei diesem Workflow mit Bildeingang sieht das Sprachmodell das Foto; "
                "`--bildart edit` (Standard) schreibt Änderungsanweisungen, "
                "`--bildart control` beschreibt das Motiv für Struktur-Workflows. "
                if h.get("image")
                else ""
            )
            + (
                f"Prompt-Modell: {self.valves.series_model.strip()}."
                if self.valves.series_model.strip()
                else "⚠ Derzeit nicht verfügbar — Admin-Valve `series_model` ist leer."
            ),
        ]
        if voice:  # v0.15.0
            lines += [
                "",
                "**Sprachbefehle (an):** ein diktierter Text kann mit Befehlen hinter "
                "„Serie“ enden, z. B. „… Serie zehn Bilder 130 Worte Querformat sofort "
                "starten“ oder „Serie los 1, 3 und 5“ — Einzelheiten in `--anleitung`.",
            ]
        lines += [
            "",
            "**Zum Kopieren:** "
            + " ".join(f"`--{l}`" for l in sorted(listers))
            + "  `--serie`  `--los`  `--anleitung`  `--reset`",
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
                "Einzelschalter `--handover-comfy 0/1` und `--handover-ollama 0/1`). "
                "Alle laufen pipe-lokal — kein GPU-Slot, keine Übersetzung.",
            ]
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
    ):
        """Wrapper around _run: makes sure the status display is cleared on
        every path - including early returns and errors.

        v0.14.0: for --los and --serie --nowait, _run returns an async
        generator that Open WebUI streams piece by piece. This finally block
        runs before the generator produces anything, so the generator owns
        its GPU slot and its closing status line itself."""
        started = time.monotonic()
        cancelled = False
        abort_note = None
        result = None
        # v0.13.0: slot bookkeeping lives here so that EVERY end path of
        # _run (return, error, stop button) releases the GPU slot.
        slot_ctx = {"slot_id": None, "hb_task": None, "state": {"lost": False}}
        try:
            result = await self._run(
                body,
                __user__,
                __event_emitter__,
                __task__,
                __metadata__,
                slot_ctx,
            )
            return result
        except asyncio.CancelledError as e:
            # Stop button in Open WebUI. What _run cleaned up at ComfyUI is
            # attached to the exception as an attribute (see _render_job).
            cancelled = True
            abort_note = getattr(e, "comfy_note", None)
            raise
        finally:
            if slot_ctx["hb_task"] is not None:
                slot_ctx["hb_task"].cancel()
            if slot_ctx["slot_id"]:
                # shield: the release must go through even on a second stop
                await asyncio.shield(self._release_slot(slot_ctx["slot_id"]))
            if inspect.isasyncgen(result):
                pass  # v0.14.0: the series generator reports its own status
            else:
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
    ):
        if __task__:
            return "ComfyUI"
        _slot_ctx = (
            _slot_ctx
            if _slot_ctx is not None
            else {"slot_id": None, "hb_task": None, "state": {"lost": False}}
        )

        pipe_id = str(body.get("model", "")).split(".")[-1]

        messages = body.get("messages") or []
        raw = self._message_text(messages[-1]) if messages else ""

        user_valves = (__user__ or {}).get("valves") or self.UserValves()

        try:
            wf, name = self._load(pipe_id)
        except Exception as e:
            return f"**Workflow konnte nicht geladen werden**\n\n{e}"

        h = self._analyze(wf)
        raw = _strip_wrappers(raw)
        prompt, flags = self._parse_flags(raw)

        # --- Spoken commands (v0.15.0) ---
        # Turned into flags before anything else looks at them, so they
        # behave exactly like typed ones; typed flags win.
        voice_hints: list[str] = []
        if getattr(user_valves, "voice_commands", False):
            voice = _voice_parse(prompt)
            if voice is not None:
                if voice["unknown"]:
                    return self._voice_halt_text(voice)
                prompt = voice["prompt"]
                applied: dict = {}
                for key, value in voice["flags"].items():
                    if key in flags:
                        typed = f"--{key} {flags[key]}".rstrip()
                        voice_hints.append(
                            f"Sprachbefehl „{voice['spoken'].get(key, key)}“ "
                            f"übergangen — getippt: `{typed}`"
                        )
                    else:
                        flags[key] = value
                        applied[key] = value
                if applied:
                    shown = " ".join(f"--{k} {v}".rstrip() for k, v in applied.items())
                    voice_hints.insert(0, f"Sprachbefehle: `{shown}`")
                    await self._emit(__event_emitter__, f"Sprachbefehle: {shown}")

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

        # --- Image series (v0.14.0) ---
        # Before help, saved defaults and the empty-prompt check: a bare
        # "--los" would otherwise be treated as a defaults message.
        if set(flags) & SERIES_FLAGS:
            return await self._series_entry(
                body,
                __user__,
                __event_emitter__,
                __metadata__,
                pipe_id,
                wf,
                name,
                h,
                prompt,
                flags,
                voice_hints,
            )

        has_image_input = bool(h.get("image")) and bool(self._extract_images(body))
        if "help" in flags or (not raw.strip() and not has_image_input):
            help_defaults = self._load_defaults((__user__ or {}).get("id"), pipe_id)
            is_admin = str((__user__ or {}).get("role", "")).lower() == "admin"
            return self._describe(
                name,
                h,
                wf,
                help_defaults,
                self._listers(h, wf),
                is_admin,
                bool(getattr(user_valves, "voice_commands", False)),
            )

        if not h.get("prompt"):
            return self._no_prompt_node_text(name)
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
        self._apply_negative(wf, h, flags, used)

        # --- Seed ---
        seed = user_valves.seed
        if "seed" in flags and flags["seed"].lstrip("-").isdigit():
            seed = int(flags["seed"])
        if seed < 0:
            seed = random.randint(0, 2**53)
        if self._set(wf, h.get("seed"), seed):
            used.append(f"seed {seed}")

        # --- Steps, cfg/guidance, marker nodes, batch (v0.14.0: shared) ---
        file_markers = self._apply_static(wf, h, flags, user_valves, used)

        # v0.14.0: --words only steers the prompt list of a series
        if "words" in msg_flags:
            used.append("--words wirkt nur zusammen mit --serie")
        if "bildart" in msg_flags:  # v0.14.1
            used.append("--bildart wirkt nur zusammen mit --serie")

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

                # --- Image upload, format from image, validation, LoRAs,
                # file markers (v0.14.0: shared with the series path) ---
                images_in = self._extract_images(body)
                flags, ar_from_image, prep_err = await self._prepare_in_session(
                    session,
                    base,
                    wf,
                    h,
                    flags,
                    user_valves,
                    images_in,
                    used,
                    file_markers,
                    name,
                    __event_emitter__,
                    handle_ar=True,
                )
                if prep_err:
                    return prep_err

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
                        return self._slot_error_text(slot_err)
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
                # v0.13.3: --triggers 0 (message or saved default) switches
                # them off; default on, as documented in the manual.
                triggers = self._active_triggers(wf, h, flags, used)
                if triggers:
                    final_prompt = (
                        final_prompt.rstrip(" ,.") + ", " + ", ".join(triggers)
                    )

                self._set(wf, h["prompt"], final_prompt)
                used.append(f"Prompt: {final_prompt}")

                # --- Resolution ---
                self._apply_resolution(
                    wf,
                    h,
                    flags.get("ar", ""),
                    self._megapixels(flags, user_valves),
                    ar_from_image,
                    used,
                )

                if not h.get("outputs"):
                    return self._no_output_text(name)

                # --- Submit, wait, fetch (v0.14.0: shared core) ---
                res = await self._render_job(
                    session, base, wf, h, f"{name}:", __event_emitter__, user_id
                )
                used.extend(res["notes"])
                if res["kind"] != "ok":
                    return res["text"]

                if _slot_ctx["state"].get("lost"):
                    used.append(
                        "Hinweis: die GPU-Slot-Lease war zwischenzeitlich verfallen "
                        "(Alpaka neu gestartet?) — der Auftrag lief trotzdem weiter"
                    )

                await self._emit(__event_emitter__, "Fertig", done=True)
                out = "\n\n".join(res["blocks"])
                if res["refined"]:
                    out += f"\n\n---\n\n**Verwendeter Prompt:**\n\n{res['refined']}"
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

        # v0.14.0: connection errors after submission are handled (and the
        # job withdrawn) inside _render_job; these handlers only cover the
        # steps before it (option lists, upload, translation).
        except asyncio.TimeoutError:
            return "Zeitüberschreitung bei der Verbindung zu ComfyUI."
        except aiohttp.ClientError as e:
            return f"Verbindung zu ComfyUI fehlgeschlagen: {e}"

    # ------------------------------------------------------------------
    # Building blocks shared by single image and series (v0.14.0)
    # ------------------------------------------------------------------

    @staticmethod
    def _message_text(msg: dict) -> str:
        """Text of one chat message; list content is joined from its text parts."""
        content = (msg or {}).get("content", "")
        if isinstance(content, list):
            return "\n".join(
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        return str(content or "")

    @staticmethod
    def _no_prompt_node_text(name: str) -> str:
        return (
            f"Im Workflow **{name}** ist kein Knoten mit dem Titel `{TITLE_PROMPT}` markiert "
            "und es ließ sich auch keiner herleiten. Bitte in ComfyUI den Knoten umbenennen, "
            "der den Prompt-Text aufnimmt, und neu als API exportieren."
        )

    @staticmethod
    def _needs_image_text(name: str) -> str:
        """Message for a workflow with image input but no image attached
        (single image since v0.7.x; series list phase since v0.14.1)."""
        return (
            f"**{name}** ist ein Bearbeitungs-Workflow und braucht ein Bild.\n\n"
            "Häng ein Foto an die Nachricht an (Plus-Symbol neben dem "
            "Eingabefeld) und schreib dazu, was geändert werden soll — "
            "zum Beispiel „schönes Wetter“."
        )

    @staticmethod
    def _no_output_text(name: str) -> str:
        return (
            f"**{name}** enthält keinen Bild-Ausgabeknoten (SaveImage oder "
            "PreviewImage) — ComfyUI würde den Bildzweig gar nicht erst "
            "ausführen.\n\nMeist ist der Knoten beim Export stummgeschaltet "
            "oder überbrückt gewesen. In ComfyUI prüfen, dass er aktiv ist, "
            "und den Workflow neu als API exportieren."
        )

    def _slot_error_text(self, slot_err: str) -> str:
        return (
            f"**GPU-Slot bei Alpaka nicht erhalten** ({slot_err}).\n\n"
            f"Läuft der Proxy unter `{self._proxy_base()}`? Ohne ihn "
            "rendert die Pipe nur, wenn die Admin-Valve "
            "`use_alpaka_proxy` abgeschaltet wird."
        )

    def _apply_negative(self, wf: dict, h: dict, flags: dict, used: list):
        if "no" in flags:
            if h.get("negative"):
                self._set(wf, h["negative"], flags["no"])
                used.append(f"negativ: {flags['no']}")
            else:
                used.append("negativ: ignoriert (Workflow hat keinen Negativ-Zweig)")

    def _apply_static(self, wf: dict, h: dict, flags: dict, user_valves, used: list):
        """Steps, cfg/guidance, marker nodes and batch - the settings that
        are the same for every image of a job or series. Marker nodes that
        point at model files are returned for the in-session matching."""
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
        return file_markers

    async def _prepare_in_session(
        self,
        session,
        base: str,
        wf: dict,
        h: dict,
        flags: dict,
        user_valves,
        images_in: list,
        used: list,
        file_markers: dict,
        name: str,
        emitter,
        handle_ar: bool = True,
    ):
        """Upload the input image, derive the format from it, validate all
        values against ComfyUI, apply LoRAs and file markers.
        Returns (flags, ar_from_image, error text or None). With
        handle_ar=False (series) the format is left to the series plan."""
        # --- Upload the attached image ---
        if h.get("image"):
            if images_in:
                raw_img, fname = images_in[0]
                await self._emit(emitter, "Bild wird hochgeladen ...")
                ref, err = await self._upload_image(session, base, raw_img, fname)
                if err:
                    return (
                        flags,
                        "",
                        f"Das Bild konnte nicht an ComfyUI uebergeben werden: {err}",
                    )
                self._set(wf, h["image"], ref)
                used.append(f"Bild: {ref}")
                if len(images_in) > 1:
                    used.append(
                        f"{len(images_in) - 1} weitere(s) Bild(er) ignoriert - "
                        "dieser Workflow nimmt nur eins"
                    )
            else:
                return flags, "", self._needs_image_text(name)
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
        if handle_ar:
            auto_ar = self.valves.auto_ar_from_image and user_valves.auto_ar
            if "arauto" in flags:
                auto_ar = self._coerce(flags["arauto"], True)
            if auto_ar and h.get("image") and images_in and "ar" not in flags:
                size = self._image_size(images_in[0][0])
                if not size:
                    used.append("Format aus Bild: Bildgröße nicht lesbar, Vorgabe bleibt")
                elif h.get("resolution"):
                    options = await self._resolution_options(session, base)
                    chosen = (
                        self._nearest_ratio_option(options, *size) if options else None
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
                    used.append("Format aus Bild: Workflow hat keine setzbare Größe")

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
        return flags, ar_from_image, None

    def _active_triggers(self, wf: dict, h: dict, flags: dict, used: list) -> list:
        """Trigger words of the active LoRAs, unless --triggers 0. (v0.13.3,
        shared since v0.14.0)"""
        triggers = self._triggers_for(wf, h)
        use_triggers = True
        if "triggers" in flags:
            use_triggers = self._coerce(flags["triggers"], True)
        if triggers and use_triggers:
            used.append("Trigger: " + ", ".join(triggers))
            return triggers
        if triggers:
            used.append("Trigger abgeschaltet (--triggers 0): " + ", ".join(triggers))
        return []

    @staticmethod
    def _megapixels(flags: dict, user_valves) -> float:
        megapixels = user_valves.megapixels
        if flags.get("mp"):
            try:
                megapixels = float(str(flags["mp"]).replace(",", "."))
            except ValueError:
                pass
        return megapixels

    def _apply_resolution(
        self,
        wf: dict,
        h: dict,
        ratio_text: str,
        megapixels: float,
        ar_from_image: str,
        used: list,
    ):
        """Write format and size into the ResolutionSelector or into all
        nodes with literal width/height fields."""
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
                extra = f" (in {len(targets)} Knoten gesetzt)" if len(targets) > 1 else ""
                if ar_from_image:
                    extra += f" (Format aus Bild {ar_from_image})"
                used.append(f"{w}x{hh}{extra}")

    async def _render_job(
        self,
        session,
        base: str,
        wf: dict,
        h: dict,
        label: str,
        emitter,
        user_id,
        fetch_status: str = "Bilder werden abgeholt ...",
    ) -> dict:
        """Submit one prepared workflow, wait for it, fetch the images.
        Shared by single image and series (v0.14.0). Never returns with a
        job still rendering: compute cap and connection errors withdraw it
        first (v0.13.3); the stop button raises CancelledError with the
        clean-up result attached as .comfy_note.

        Returns a dict with kind:
          "ok"    - blocks (markdown image lines), refined, notes
          "error" - a failure of this job: text (full message), short
                    (one line for series), detail (optional), notes
          "conn"  - ComfyUI unreachable: text, short, notes"""
        notes: list[str] = []
        # prompt_id of a job ComfyUI has accepted but whose result has not
        # arrived yet - the connection-error handlers withdraw it (v0.13.3)
        open_job: Optional[str] = None
        try:
            attempts = 2 if self.valves.retry_on_error else 1
            history = None
            error_status = None
            for attempt in range(1, attempts + 1):
                if attempt > 1:
                    notes.append(
                        "Erster Versuch von ComfyUI abgebrochen — automatisch wiederholt"
                    )
                    await self._emit(
                        emitter, f"{label} Abbruch, zweiter Versuch läuft ..."
                    )
                else:
                    await self._emit(emitter, f"{label} Auftrag geht raus ...")

                async with session.post(f"{base}/prompt", json={"prompt": wf}) as resp:
                    if resp.status != 200:
                        detail = await resp.text()
                        return {
                            "kind": "error",
                            "short": f"von ComfyUI abgelehnt (HTTP {resp.status})",
                            "detail": _clip_middle(detail, 1200),
                            "text": (
                                f"ComfyUI hat den Auftrag abgelehnt (HTTP {resp.status}):\n\n"
                                f"```\n{_clip_middle(detail)}\n```"
                            ),
                            "notes": notes,
                        }
                    submitted = await resp.json()
                    prompt_id = submitted["prompt_id"]
                    open_job = prompt_id  # v0.13.3: withdraw on connection loss
                    node_errors = submitted.get("node_errors") or {}
                    if node_errors and attempt == 1:
                        problems = []
                        for nid, err in node_errors.items():
                            title = (wf.get(nid, {}).get("_meta") or {}).get("title", "")
                            label_node = f"{nid} ({wf.get(nid, {}).get('class_type', '?')}"
                            label_node += f", {title})" if title else ")"
                            for detail in err.get("errors") or []:
                                problems.append(
                                    f"- {label_node}: {detail.get('message', '?')} "
                                    f"{detail.get('details', '')}".rstrip()
                                )
                        notes.append(
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
                        async with session.get(f"{base}/history/{prompt_id}") as resp:
                            data = await resp.json()
                        if prompt_id in data:
                            history = data[prompt_id]
                            open_job = None  # result is there, nothing to withdraw
                            break
                        position = await self._queue_position(session, base, prompt_id)
                        if position:
                            text = f"{label} wartet, Position {position} in der Warteschlange"
                        else:
                            suffix = " (2. Versuch)" if attempt > 1 else ""
                            text = f"{label} rechnet{suffix} ... ({int(elapsed)} s)"
                        await self._emit(emitter, text)
                        await asyncio.sleep(1.5)
                except asyncio.CancelledError as e:
                    # Stop button in Open WebUI: withdraw the job from
                    # ComfyUI. shield, so the cleanup completes even on a
                    # second cancel.
                    e.comfy_note = await asyncio.shield(self._abort_job(base, prompt_id))
                    raise

                if history is None:
                    # v0.13.3: compute cap reached - withdraw the job (same
                    # clean-up as the stop button) BEFORE the GPU slot is
                    # released. shield: completes even on a stop during the
                    # clean-up.
                    note = await asyncio.shield(self._abort_job(base, prompt_id))
                    open_job = None
                    return {
                        "kind": "error",
                        "short": f"Zeitüberschreitung ({note})",
                        "text": (
                            "**Zeitüberschreitung:** ComfyUI hat den Auftrag nicht "
                            f"innerhalb von {_duration(self.valves.timeout_seconds)} "
                            "abgeschlossen (Admin-Valve `timeout_seconds`)."
                            + self._abort_suffix(note)
                        ),
                        "notes": notes,
                    }

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
                dump = json.dumps(error_status, indent=2, ensure_ascii=False)
                return {
                    "kind": "error",
                    "short": prefix,
                    "detail": _clip_middle(dump, 1200),
                    "text": f"{prefix}:\n\n```\n{_clip_middle(dump)}\n```" + _RESET_HINT,
                    "notes": notes,
                }

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
                return {
                    "kind": "error",
                    "short": "kein Bild",
                    "text": (
                        "ComfyUI ist durchgelaufen, hat aber kein Bild zurückgegeben."
                        f"{hint}\n\nGemeldete Ausgaben je Knoten:\n\n```\n"
                        f"{_clip_middle(json.dumps(detail, indent=1, ensure_ascii=False), 1500)}\n```"
                        + _RESET_HINT
                    ),
                    "notes": notes,
                }

            await self._emit(emitter, fetch_status)
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
                    url, err = await self._store_image(data, img["filename"], user_id)
                    if err and not store_error:
                        store_error = err
                if url:
                    blocks.append(f"![{img['filename']}]({url})")
                else:
                    b64 = base64.b64encode(data).decode()
                    mime = _mime_for(img["filename"])
                    blocks.append(f"![{img['filename']}](data:{mime};base64,{b64})")

            if store_error:
                notes.append(f"Dateiablage übersprungen ({store_error})")
            return {"kind": "ok", "blocks": blocks, "refined": refined, "notes": notes}

        except asyncio.TimeoutError:
            return {
                "kind": "conn",
                "short": "Zeitüberschreitung bei der Verbindung zu ComfyUI",
                "text": "Zeitüberschreitung bei der Verbindung zu ComfyUI."
                + (await self._withdraw_open_job(base, open_job)),
                "notes": notes,
            }
        except aiohttp.ClientError as e:
            return {
                "kind": "conn",
                "short": f"Verbindung zu ComfyUI fehlgeschlagen ({e})",
                "text": f"Verbindung zu ComfyUI fehlgeschlagen: {e}"
                + (await self._withdraw_open_job(base, open_job)),
                "notes": notes,
            }

    # ------------------------------------------------------------------
    # Image series (v0.14.0)
    # ------------------------------------------------------------------

    @staticmethod
    def _voice_halt_text(voice: dict) -> str:
        """Message when the spoken command part was only partly understood
        (v0.15.0): nothing is started."""
        unknown = ", ".join(f"„{w}“" for w in voice["unknown"])
        known = " ".join(f"--{k} {v}".rstrip() for k, v in voice["flags"].items())
        return (
            f"**Sprachbefehl nicht verstanden:** {unknown}\n\n"
            f"Befehlsteil: „{voice['tail']}“ · erkannt: `{known}` · "
            "es wurde nichts gestartet.\n\n"
            "Befehle stehen am Ende hinter „Serie“: Anzahl („zehn Bilder“), "
            "Länge („130 Worte“), „Querformat“, „Hochformat“, „quadratisch“, "
            "„sofort starten“, „los“ (auch mit Nummern). War kein Befehl gemeint: "
            "anders formulieren oder `voice_commands` in der Chat-Steuerung "
            "ausschalten."
        )

    async def _series_entry(
        self,
        body: dict,
        __user__: Optional[dict],
        emitter,
        __metadata__: Optional[dict],
        pipe_id: str,
        wf: dict,
        name: str,
        h: dict,
        prompt: str,
        flags: dict,
        pre_hints: Optional[list] = None,
    ):
        """Dispatch --serie (list phase, optionally rendering right away
        with --nowait) and --los (render a list from the chat).
        pre_hints: notes from the spoken commands (v0.15.0)."""
        hints: list[str] = list(pre_hints or [])
        if "serie" in flags and "los" in flags:
            # v0.14.1: --los next to --serie means "render right away",
            # like --nowait; a selection makes no sense for a new list
            flags = dict(flags)
            selection = str(flags.pop("los") or "").strip()
            flags["nowait"] = ""
            if selection:
                hints.append(
                    f"`--los {selection}`: Auswahl gilt nur für eine bestehende Liste "
                    "— hier wirkt `--los` wie `--nowait`"
                )
        if "nowait" in flags and "serie" not in flags:
            return (
                "`--nowait` gehört zu `--serie`, zum Beispiel:\n\n"
                "`Katze in vier Jahreszeiten, Fotostil --serie 5 --nowait`"
            )
        if not h.get("prompt"):
            return self._no_prompt_node_text(name)
        if not h.get("outputs"):
            return self._no_output_text(name)

        user = __user__ or {}
        ctx = {
            "body": body,
            "emitter": emitter,
            "metadata": __metadata__ or {},
            "user_id": user.get("id"),
            "user_valves": user.get("valves") or self.UserValves(),
            "pipe_id": pipe_id,
            "wf": wf,
            "name": name,
            "h": h,
            "defaults": self._load_defaults(user.get("id"), pipe_id),
            "hints": hints,
            "info": [],
        }
        if "serie" in flags:
            return await self._series_list_phase(ctx, prompt, flags)
        return await self._series_los_phase(ctx, flags)

    @staticmethod
    def _series_layer(flags: dict) -> dict:
        """Flags of one message without the commands (they are never
        values of a job and never saved)."""
        return {
            k: v
            for k, v in flags.items()
            if k not in SERIES_FLAGS and k not in COMMAND_FLAGS
        }

    def _layer_flags(self, base: dict, layer: dict) -> dict:
        """Lay one message's flags over a lower layer, with the same rules
        as a single image over its saved defaults: a bare flag drops the
        value for this run, LoRA name and strength merge separately."""
        bare = {k for k, v in layer.items() if not str(v).strip()}
        out = {**base, **layer}
        for k, v in layer.items():
            if k in bare:
                continue
            if re.fullmatch(r"lora\d+", k) and k in base:
                out[k] = self._merge_lora_value(base[k], v)
        for k in bare:
            out.pop(k, None)
        return out

    def _series_count(self, value, hints: list) -> int:
        maximum = max(1, int(self.valves.series_max))
        text = str(value or "").strip()
        if not text:
            n = SERIES_DEFAULT_COUNT
        elif text.isdigit():
            n = int(text)
        else:
            hints.append(
                f"`--serie {text}` ist keine Zahl — es gilt {SERIES_DEFAULT_COUNT}"
            )
            n = SERIES_DEFAULT_COUNT
        if n < 1:
            hints.append("mindestens 1 Prompt")
            n = 1
        if n > maximum:
            hints.append(
                f"{n} Prompts auf {maximum} begrenzt (Admin-Valve `series_max`)"
            )
            n = maximum
        return n

    def _series_total(self, n: int, words: int) -> int:
        """Total words of a list request when the total length hint applies
        (target length set, n x words >= series_total_hint > 0), else 0.
        (v0.15.0)"""
        threshold = int(self.valves.series_total_hint or 0)
        if words <= 0 or threshold <= 0 or n * words < threshold:
            return 0
        return n * words

    def _series_words(self, flags: dict, user_valves, hints: list) -> int:
        raw = flags.get("words")
        words = user_valves.series_words
        if raw is not None and str(raw).strip():
            text = str(raw).strip()
            try:
                words = int(float(text.replace(",", ".")))
            except ValueError:
                hints.append(
                    f"`--words {text}` ist keine Zahl — es gilt der Wert aus der "
                    "Chat-Steuerung"
                )
        if words < 0:
            words = 0
        if words > SERIES_WORDS_MAX:
            hints.append(f"Länge {words} Wörter auf {SERIES_WORDS_MAX} begrenzt")
            words = SERIES_WORDS_MAX
        return words

    def _series_match_ar(self, value: str, h: dict, options_full: list):
        """Map a user-given ratio to what the workflow takes: the full
        ResolutionSelector entry, or W:H for plain width/height nodes."""
        value = str(value).strip()
        if h.get("resolution"):
            for o in options_full:
                if o == value or o.split(" ")[0] == value:
                    return o
            return None
        if h.get("dimension_nodes"):
            return value if self._aspect(value) else None
        return None

    async def _series_ar_plan(
        self, h: dict, flags: dict, ar_from_msg: bool, user_valves, images_in: list
    ) -> dict:
        """Who decides the format of a series: --ar > input image > user
        valve > the LLM per prompt > workflow file. A fixed format is named
        once in the list header and the LLM is not asked for one."""
        notes: list[str] = []
        base = self.valves.comfy_url.rstrip("/")
        options_full: list[str] = []
        short_to_full: dict = {}
        if h.get("resolution"):
            try:
                timeout = aiohttp.ClientTimeout(total=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    options_full = await self._resolution_options(session, base)
            except Exception:
                options_full = []
            for o in options_full:
                short = o.split(" ")[0]
                if self._aspect(short) and short not in short_to_full:
                    short_to_full[short] = o
            if not options_full:
                notes.append(
                    "Formatliste des ResolutionSelectors nicht erhalten (ComfyUI "
                    "erreichbar?) — Format wie im Workflow"
                )
        elif h.get("dimension_nodes"):
            for part in re.split(r"[,;]", self.valves.series_ar_options or ""):
                short = part.strip()
                if short and self._aspect(short) and short not in short_to_full:
                    short_to_full[short] = short
        settable = bool(short_to_full) or bool(
            h.get("dimension_nodes") and not h.get("resolution")
        )

        def fixed(value_full: str, display: str, source: str, short: str) -> dict:
            # source: long form for the list header; short (v0.14.1): the
            # label in "Format 1:1 (User-Valve)" above and below the images
            return {
                "mode": "fixed",
                "value_full": value_full,
                "display": display,
                "source": source,
                "short": short,
                "short_to_full": short_to_full,
                "notes": notes,
            }

        workflow_plan = {
            "mode": "workflow",
            "value_full": "",
            "display": "",
            "source": "",
            "short": "",
            "short_to_full": short_to_full,
            "notes": notes,
        }
        if not settable:
            return workflow_plan

        # 1. --ar (message or saved default)
        ar = str(flags.get("ar", "") or "").strip()
        if ar:
            full = self._series_match_ar(ar, h, options_full)
            if full:
                return fixed(
                    full,
                    full.split(" ")[0],
                    "--ar" if ar_from_msg else "gespeicherte Vorgabe",
                    "--ar" if ar_from_msg else "Vorgabe",
                )
            notes.append(f"`--ar {ar}`: Format unbekannt — ignoriert")

        # 2. input image (same switches as the single image)
        auto_ar = self.valves.auto_ar_from_image and user_valves.auto_ar
        if "arauto" in flags:
            auto_ar = self._coerce(flags["arauto"], True)
        if auto_ar and h.get("image") and images_in:
            size = self._image_size(images_in[0][0])
            if not size:
                notes.append("Format aus Bild: Bildgröße nicht lesbar")
            else:
                w, hh = size
                source = f"Bild-Input (aus Bild {w}x{hh})"
                if h.get("resolution"):
                    chosen = (
                        self._nearest_ratio_option(options_full, w, hh)
                        if options_full
                        else None
                    )
                    if chosen:
                        return fixed(chosen, chosen.split(" ")[0], source, "Bild-Input")
                else:
                    g = math.gcd(w, hh) or 1
                    return fixed(
                        f"{w}:{hh}", f"{w // g}:{hh // g}", source, "Bild-Input"
                    )

        # 3. user valve
        uv = str(user_valves.aspect_ratio or "").strip()
        if uv:
            full = self._series_match_ar(uv, h, options_full)
            if full:
                return fixed(full, full.split(" ")[0], "User-Valve", "User-Valve")
            notes.append(f"User-Valve `aspect_ratio` {uv}: Format unbekannt — ignoriert")

        # 4. the LLM chooses per prompt
        if short_to_full:
            return {
                "mode": "llm",
                "value_full": "",
                "display": "",
                "source": "LLM",
                "short": "LLM",
                "short_to_full": short_to_full,
                "notes": notes,
            }
        return workflow_plan

    @staticmethod
    def _series_format_header(plan: dict) -> str:
        if plan["mode"] == "fixed":
            return f"Format: {plan['display']}, fixiert über {plan['source']}"
        if plan["mode"] == "llm":
            return "Format: je Prompt vom LLM gewählt"
        return "Format: wie im Workflow"

    async def _series_list_phase(self, ctx: dict, prompt: str, flags: dict):
        """--serie: let the prompt LLM write the list; with --nowait render
        it right away."""
        v = self.valves
        hints, info = ctx["hints"], ctx["info"]
        user_valves = ctx["user_valves"]
        h = ctx["h"]
        model = v.series_model.strip()
        if not model:
            return (
                "**Serienmodus nicht verfügbar:** in den Admin-Valves ist kein "
                "`series_model` gesetzt."
            )
        vorgabe = " ".join(prompt.split())
        if not vorgabe:
            return (
                "Für eine Serie fehlt die Vorgabe. Der Text steht **vor** den Kürzeln, "
                "zum Beispiel:\n\n`Katze in vier Jahreszeiten, Fotostil --serie 10`"
            )
        images_in = self._extract_images(ctx["body"])
        # v0.14.1: a workflow with image input needs its image before any
        # prompt is written - otherwise the LLM writes about nothing
        if h.get("image") and not images_in:
            return self._needs_image_text(ctx["name"])

        n = self._series_count(flags.get("serie", ""), hints)
        nowait = "nowait" in flags
        layer = self._series_layer(flags)
        eff = self._layer_flags(ctx["defaults"], layer)
        eff, checks = self._check_series_values(eff)
        hints.extend(checks)
        words = self._series_words(eff, user_valves, hints)
        eff.pop("words", None)
        bildart = eff.pop("bildart", None)
        if bildart and not h.get("image"):
            hints.append(
                "`--bildart` wird ignoriert — dieser Workflow hat keinen Bildeingang"
            )
            bildart = None

        system_prompt, had_memory, had_summary = self._system_prompt(ctx["body"])
        if had_memory:
            info.append("Gedächtnis-Block aus dem Systemprompt entfernt")
        if had_summary:
            info.append(
                "Chat-Zusammenfassung (Context Compaction) aus dem Systemprompt entfernt"
            )
        if system_prompt:
            info.append("Systemprompt als feste Vorgabe an das Prompt-Modell übergeben")

        plan = await self._series_ar_plan(
            h,
            eff,
            bool(str(layer.get("ar", "")).strip()),
            user_valves,
            images_in,
        )
        hints.extend(plan["notes"])
        ar_options = list(plan["short_to_full"]) if plan["mode"] == "llm" else None

        # --- Image for the prompt LLM (v0.14.1) ---
        system_text = v.series_system
        llm_image = None
        used_bildart = None
        if h.get("image"):
            used_bildart = bildart or BILDART_VALUES[0]
            system_text = (
                v.series_system_control
                if used_bildart == "control"
                else v.series_system_edit
            )
            await self._emit(
                ctx["emitter"], "Serie: Bildfähigkeit des Prompt-Modells wird geprüft ..."
            )
            vision, detail = await self._series_vision_check()
            if vision is False:
                return (
                    f"**Das Prompt-Modell `{model}` kann keine Bilder verarbeiten.**\n\n"
                    "Für Serien mit einem Bild-Workflow in der Admin-Valve "
                    "`series_model` ein Modell mit Bildverarbeitung eintragen."
                )
            if vision is None:
                hints.append(
                    f"Bildfähigkeit von `{model}` nicht prüfbar ({detail}) — "
                    "das Bild geht trotzdem mit"
                )
            llm_image, image_note = self._series_llm_image(images_in[0][0])
            if image_note:
                info.append(image_note)
        elif images_in:
            info.append(
                "Bild angehängt, aber dieser Workflow hat keinen Bildeingang — "
                "es geht nicht an das Prompt-Modell"
            )

        await self._emit(ctx["emitter"], "Serie: Prompts werden erstellt ...")
        items, err, gen_notes = await self._series_generate(
            ctx["emitter"],
            vorgabe,
            n,
            words,
            system_prompt,
            ar_options,
            system_text,
            llm_image,
        )
        if err:
            return err
        hints.extend(gen_notes)
        info.append(f"Prompt-Modell: {model}")
        total = self._series_total(n, words)
        if total:  # v0.15.0
            info.append(
                f"Gesamtlängen-Zusatz an das Prompt-Modell (~{total:,} Wörter)".replace(
                    ",", "."
                )
            )

        list_block = self._series_list_block(
            ctx["name"], items, plan, words, vorgabe, nowait, used_bildart
        )
        if not nowait:
            out = list_block
            if hints:
                out += "\n\n*Hinweise: " + " · ".join(hints) + "*"
            if user_valves.show_prompt and info:
                out += "\n\n---\n\n*" + " · ".join(info) + "*"
            return out

        entries = [
            (i, it["prompt"], it.get("ar")) for i, it in enumerate(items, start=1)
        ]
        return await self._series_prepare_render(
            ctx, entries, eff, images_in, plan, list_block
        )

    async def _series_vision_check(self):
        """Ask Ollama (via ollama_url, i.e. through Alpaka) whether
        series_model can process images. Returns (True|False|None, detail);
        None = could not be checked. No read timeout, like the prompt
        request itself. (v0.14.1)"""
        url = self.valves.ollama_url.rstrip("/") + "/api/show"
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=None)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, json={"model": self.valves.series_model.strip()}
                ) as resp:
                    if resp.status != 200:
                        return None, f"HTTP {resp.status}"
                    data = await resp.json(content_type=None)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"
        caps = data.get("capabilities") if isinstance(data, dict) else None
        if not isinstance(caps, list):
            return None, "keine Angabe zu capabilities"
        return "vision" in caps, None

    @staticmethod
    def _series_llm_image(raw: bytes):
        """The input image as base64 for the prompt LLM. Images whose
        longest side exceeds SERIES_IMAGE_MAX are scaled down and sent as
        JPEG (quality 90) with the EXIF orientation applied; smaller ones go
        unchanged; without Pillow the original goes. Returns (b64, note).
        (v0.14.1)"""
        try:
            import io as _io

            from PIL import Image as _Image
            from PIL import ImageOps as _ImageOps
        except Exception:
            return (
                base64.b64encode(raw).decode(),
                "Bild unverkleinert an das Prompt-Modell (Pillow fehlt)",
            )
        try:
            with _Image.open(_io.BytesIO(raw)) as original:
                w, hh = original.size
                if max(w, hh) <= SERIES_IMAGE_MAX:
                    return base64.b64encode(raw).decode(), None
                if original.format == "JPEG":
                    # decode at a reduced scale - cheap even for 200 MP photos
                    original.draft("RGB", (SERIES_IMAGE_MAX, SERIES_IMAGE_MAX))
                im = _ImageOps.exif_transpose(original).convert("RGB")
                im.thumbnail((SERIES_IMAGE_MAX, SERIES_IMAGE_MAX), _Image.LANCZOS)
                buf = _io.BytesIO()
                im.save(buf, format="JPEG", quality=90)
                return (
                    base64.b64encode(buf.getvalue()).decode(),
                    f"Bild für das Prompt-Modell verkleinert ({w}x{hh} → "
                    f"{im.size[0]}x{im.size[1]})",
                )
        except Exception as e:
            return (
                base64.b64encode(raw).decode(),
                f"Bild unverkleinert an das Prompt-Modell ({type(e).__name__})",
            )

    def _series_list_block(
        self,
        name: str,
        items: list,
        plan: dict,
        words: int,
        vorgabe: str,
        nowait: bool,
        bildart: Optional[str] = None,
    ) -> str:
        avg = round(sum(len(it["prompt"].split()) for it in items) / len(items))
        length = (
            f"Länge: ~{words} Wörter (Ø {avg})" if words > 0 else f"Länge: Ø {avg} Wörter"
        )
        head = (
            f"{LIST_HEADER} · {name} · {len(items)} Prompts · "
            f"{self._series_format_header(plan)} · {length}"
        )
        if bildart:  # v0.14.1: only when an image went to the prompt LLM
            head += f" · Bildart: {bildart}"
        lines = [head, "", f"Vorgabe: {vorgabe}", ""]
        for i, it in enumerate(items, start=1):
            tag = f"[{it['ar']}] " if plan["mode"] == "llm" and it.get("ar") else ""
            lines.append(f"{i}. {tag}{it['prompt']}")
        lines.append("")
        if nowait:
            lines.append(
                "Läuft sofort (`--nowait`). Später erneut rendern: `--los` bzw. "
                "`--los 1,3,7` – auch nach Bearbeiten der Liste."
            )
        else:
            lines.append(
                "Starten mit `--los`, Auswahl mit `--los 1,3,7`. Die Liste lässt sich "
                "vorher über die Bearbeiten-Funktion ändern – es gilt der bearbeitete Stand."
            )
        return "\n".join(lines)

    async def _series_generate(
        self,
        emitter,
        vorgabe: str,
        n: int,
        words: int,
        fixed: str,
        ar_options: Optional[list],
        system_text: Optional[str] = None,
        image_b64: Optional[str] = None,
    ):
        """Ask the prompt LLM (via ollama_url, i.e. through Alpaka's normal
        queue - no GPU slot) for n prompts as JSON, streamed for the
        progress display. Returns (items, error text, notes).
        v0.14.1: system_text (series_system or the edit/control text for
        image workflows), image_b64 (input image for the LLM) and the
        format ban appended to every request."""
        v = self.valves
        url = v.ollama_url.rstrip("/") + "/api/generate"
        item_props: dict = {"prompt": {"type": "string"}}
        required = ["prompt"]
        if ar_options:
            item_props["ar"] = {"type": "string", "enum": list(ar_options)}
            required.append("ar")
        schema = {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": item_props,
                        "required": required,
                    },
                }
            },
            "required": ["prompts"],
        }
        parts = [f"Brief: {vorgabe}", f"Number of prompts: {n}"]
        if words > 0:
            parts.append(f"Each prompt should be about {words} words long.")
            total = self._series_total(n, words)
            if total:  # v0.15.0
                parts.append(
                    SERIES_TOTAL_HINT.format(
                        total=total,
                        n=n,
                        prompts="prompt" if n == 1 else "prompts",
                        words=words,
                    )
                )
        parts.append(SERIES_FORMAT_BAN)
        if fixed:
            parts.append(f"Fixed requirements for every prompt: {fixed}")
        if ar_options:
            parts.append("Allowed aspect ratios: " + ", ".join(ar_options))
        user_text = "\n".join(parts)

        system_text = system_text or v.series_system
        base = {
            "model": v.series_model.strip(),
            "stream": True,
            "keep_alive": v.series_keep_alive,
            "format": schema,
        }
        if image_b64:
            base["images"] = [image_b64]
        if v.series_num_ctx and v.series_num_ctx > 0:
            base["options"] = {"num_ctx": int(v.series_num_ctx)}
        # Same order as the translation: thinking off, then without the
        # think field (models without thinking answer that with an error),
        # then the instruction inside the prompt instead of the system role.
        attempts = [
            {**base, "prompt": user_text, "system": system_text, "think": False},
            {**base, "prompt": user_text, "system": system_text},
            {**base, "prompt": f"{system_text}\n\n{user_text}"},
        ]
        # No read timeout: without a slot the request waits in Alpaka's
        # queue, and nothing arrives until it is dispatched. The stop
        # button closes the connection.
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=None)
        last_err = None
        truncated_text = (
            "**Antwort abgeschnitten** – das Prompt-Modell hat vor dem Ende aufgehört. "
            "Länge (`--words`) oder Anzahl verringern – oder die Admin-Valve "
            "`series_num_ctx` erhöhen."
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for payload in attempts:
                try:
                    text, done_reason, finished, err = await self._series_stream(
                        session, url, payload, emitter
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    last_err = f"{type(e).__name__}: {e}"
                    continue
                if err:
                    last_err = err
                    continue
                if done_reason == "length":
                    return None, truncated_text, []
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
                items, notes, parse_err = self._series_parse_llm(text, n, ar_options)
                if parse_err:
                    if not finished:
                        return None, truncated_text, []
                    last_err = parse_err
                    continue
                return items, None, notes
        return (
            None,
            f"**Prompt-Liste konnte nicht erzeugt werden** ({last_err}).\n\n"
            f"Antwortet das Modell `{v.series_model.strip()}` unter `{v.ollama_url}`?",
            [],
        )

    async def _series_stream(self, session, url: str, payload: dict, emitter):
        """One streamed /api/generate call. Returns (text, done_reason,
        finished, error). The status line shows a rough word count every
        1.5 s (JSON keys count as words too - hence the '~')."""
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                detail = (await resp.text())[:300].strip()
                return "", None, False, f"HTTP {resp.status} {detail}".strip()
            chunks: list[str] = []
            done_reason = None
            finished = False
            thinking = False
            last_emit = 0.0
            async for raw_line in resp.content:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("error"):
                    return "".join(chunks), None, False, str(obj["error"])
                piece = obj.get("response") or ""
                if piece:
                    chunks.append(piece)
                if obj.get("thinking"):
                    thinking = True
                if obj.get("done"):
                    finished = True
                    done_reason = obj.get("done_reason")
                    break
                now = time.monotonic()
                if now - last_emit >= 1.5:
                    last_emit = now
                    if chunks:
                        count = len("".join(chunks).split())
                        await self._emit(
                            emitter,
                            "Serie: Prompts werden erstellt ... ~"
                            f"{count:,}".replace(",", ".") + " Wörter",
                        )
                    elif thinking:
                        await self._emit(emitter, "Serie: Prompt-Modell denkt nach ...")
            return "".join(chunks), done_reason, finished, None

    @staticmethod
    def _series_parse_llm(text: str, n: int, ar_options: Optional[list]):
        """Turn the LLM's JSON into list items. Returns (items, notes, error)."""
        data = None
        try:
            data = json.loads(text)
        except Exception:
            start, end = text.find("{"), text.rfind("}")
            if 0 <= start < end:
                try:
                    data = json.loads(text[start : end + 1])
                except Exception:
                    data = None
        if data is None:
            return None, [], "kein gültiges JSON"
        raw_items = data.get("prompts") if isinstance(data, dict) else data
        if not isinstance(raw_items, list):
            return None, [], "JSON ohne Liste 'prompts'"
        items: list[dict] = []
        bad_ar: list[int] = []
        for entry in raw_items:
            ar = None
            if isinstance(entry, str):
                text_value = entry
            elif isinstance(entry, dict):
                text_value = entry.get("prompt") or entry.get("text") or ""
                ar = entry.get("ar")
            else:
                continue
            text_value = " ".join(str(text_value).split())
            text_value = re.sub(r"^\d+[.)]\s+", "", text_value)
            if not text_value:
                continue
            if ar_options:
                ar = str(ar or "").strip()
                if ar not in ar_options:
                    bad_ar.append(len(items) + 1)
                    ar = None
            else:
                ar = None
            items.append({"prompt": text_value, "ar": ar})
        if not items:
            return None, [], "keine Prompts in der Antwort"
        notes: list[str] = []
        if len(items) > n:
            items = items[:n]
            bad_ar = [b for b in bad_ar if b <= n]
        elif len(items) < n:
            notes.append(f"das Prompt-Modell hat nur {len(items)} von {n} Prompts geliefert")
        if bad_ar:
            notes.append(
                "ungültiges Format bei Nr. "
                + ", ".join(str(b) for b in bad_ar)
                + " — dort gilt das Workflow-Format"
            )
        return items, notes, None

    @staticmethod
    def _series_parse_list(text: str):
        """Read the visible (possibly edited) list: the lines after the
        header of the form 'N. [ratio] text' or 'N. text'. Numbers are taken
        from the text, not recounted. Returns (entries, notes)."""
        lines = text.splitlines()
        start = next(
            (i for i, line in enumerate(lines) if line.lstrip().startswith(LIST_HEADER)),
            None,
        )
        if start is None:
            return [], []
        entries: list[tuple] = []
        seen: set = set()
        dup: list[int] = []
        collecting = False
        for line in lines[start + 1 :]:
            if not line.strip():
                continue
            m = LIST_LINE_RE.match(line)
            if m:
                collecting = True
                num = int(m.group(1))
                ratio = (m.group(2) or "").strip() or None
                text_value = " ".join(m.group(3).split())
                if num in seen:
                    dup.append(num)
                    continue
                seen.add(num)
                entries.append((num, text_value, ratio))
            elif collecting:
                break
        notes = []
        if dup:
            notes.append(
                "doppelte Nummer(n) in der Liste: "
                + ", ".join(str(d) for d in dup)
                + " — jeweils die erste gilt"
            )
        return entries, notes

    @staticmethod
    def _series_selection(value, numbers: list):
        """--los 1,3,7 -> the chosen numbers in the given order."""
        text = str(value or "").strip()
        if not text:
            return list(numbers), []
        chosen: list[int] = []
        notes: list[str] = []
        bad, unknown, dup = [], [], []
        for token in [t for t in re.split(r"[,;\s]+", text) if t]:
            if not token.isdigit():
                bad.append(token)
                continue
            k = int(token)
            if k not in numbers:
                unknown.append(k)
            elif k in chosen:
                dup.append(k)
            else:
                chosen.append(k)
        if bad:
            notes.append(
                "nicht verstanden: "
                + ", ".join(bad)
                + " (nur Einzelnummern mit Komma, keine Bereiche)"
            )
        if unknown:
            notes.append(
                "nicht in der Liste: Nr. " + ", ".join(str(u) for u in unknown)
            )
        if dup:
            notes.append("doppelt genannt: Nr. " + ", ".join(str(d) for d in dup))
        return chosen, notes

    async def _series_los_phase(self, ctx: dict, flags: dict):
        """--los: find the latest list in the chat and render it (or a
        selection of it)."""
        hints = ctx["hints"]
        messages = ctx["body"].get("messages") or []
        list_index, list_text = None, ""
        for i in range(len(messages) - 2, -1, -1):
            msg = messages[i]
            if msg.get("role") != "assistant":
                continue
            text = self._message_text(msg)
            if any(line.lstrip().startswith(LIST_HEADER) for line in text.splitlines()):
                list_index, list_text = i, text
                break
        if list_index is None:
            return "Keine Prompt-Liste im Chat gefunden – zuerst `--serie` senden."
        entries_all, parse_notes = self._series_parse_list(list_text)
        hints.extend(parse_notes)
        if not entries_all:
            return (
                "In der letzten Prompt-Liste stehen keine lesbaren Prompt-Zeilen "
                "(Form: `1. [16:9] Text` bzw. `1. Text`, eine Zeile je Prompt)."
            )
        numbers = [e[0] for e in entries_all]
        chosen, sel_notes = self._series_selection(flags.get("los", ""), numbers)
        hints.extend(sel_notes)
        if not chosen:
            return "Keine der genannten Nummern steht in der Liste." + (
                "\n\n*Hinweise: " + " · ".join(hints) + "*" if hints else ""
            )
        by_num = {e[0]: e for e in entries_all}
        entries = [by_num[k] for k in chosen]

        # The --serie message: the user message right before the list
        serie_msg = None
        for j in range(list_index - 1, -1, -1):
            if messages[j].get("role") == "user":
                serie_msg = messages[j]
                break
        serie_flags: dict = {}
        if serie_msg is not None:
            _p, serie_flags = self._parse_flags(
                _strip_wrappers(self._message_text(serie_msg))
            )
            # v0.15.0: a dictated --serie message carries its flags as
            # spoken commands - read them the same way (no stop here)
            if getattr(ctx["user_valves"], "voice_commands", False):
                voice = _voice_parse(_p)
                if voice is not None and not voice["unknown"]:
                    for key, value in voice["flags"].items():
                        serie_flags.setdefault(key, value)
        serie_layer = self._series_layer(serie_flags)
        los_layer = self._series_layer(flags)
        serie_layer.pop("words", None)
        serie_layer.pop("bildart", None)
        if "words" in los_layer:
            los_layer.pop("words")
            hints.append("`--words` wirkt nur beim Erzeugen der Liste")
        if "bildart" in los_layer:  # v0.14.1
            los_layer.pop("bildart")
            hints.append("`--bildart` wirkt nur beim Erzeugen der Liste")
        eff = self._layer_flags(
            self._layer_flags(ctx["defaults"], serie_layer), los_layer
        )
        ar_from_msg = any(
            str(layer.get("ar", "")).strip() for layer in (serie_layer, los_layer)
        )

        # Input image: the one attached to --los wins, else the one from
        # the --serie message (Open WebUI resends it as base64)
        images_in = self._extract_images(ctx["body"])
        if not images_in and serie_msg is not None:
            images_in = self._images_from_message(serie_msg)

        plan = await self._series_ar_plan(
            ctx["h"], eff, ar_from_msg, ctx["user_valves"], images_in
        )
        hints.extend(plan["notes"])
        return await self._series_prepare_render(
            ctx, entries, eff, images_in, plan, None
        )

    def _series_item_ratio(self, plan: dict, line_ar: Optional[str], num: int, hints: list):
        """(value for the workflow, label) of one list entry. The label is
        the short form shown above and below the image (v0.14.1):
        "Format 1:1 (User-Valve)", "Format 16:9 (LLM)", "Format wie Workflow"."""
        if plan["mode"] == "fixed":
            return plan["value_full"], f"Format {plan['display']} ({plan['short']})"
        if plan["mode"] == "llm" and line_ar:
            full = plan["short_to_full"].get(line_ar)
            if full:
                return full, f"Format {line_ar} (LLM)"
            hints.append(f"Nr. {num}: Format [{line_ar}] unbekannt — Format wie Workflow")
        return "", "Format wie Workflow"

    async def _series_prepare_render(
        self,
        ctx: dict,
        entries: list,
        eff: dict,
        images_in: list,
        plan: dict,
        list_block: Optional[str],
    ):
        """Shared preparation for --los and --nowait: apply every setting
        that is the same for all images, upload the input image once, then
        hand over to the rendering generator. Errors before the first image
        come back as plain text."""
        h, name, user_valves = ctx["h"], ctx["name"], ctx["user_valves"]
        wf = ctx["wf"]
        hints, info = ctx["hints"], ctx["info"]
        used: list[str] = []
        base = self.valves.comfy_url.rstrip("/")
        prefix = (list_block + "\n\n") if list_block else ""

        self._apply_negative(wf, h, eff, used)
        file_markers = self._apply_static(wf, h, eff, user_valves, used)
        unknown = [k for k in eff if k not in self._known_flags(h)]
        if unknown:
            used.append(
                "unbekannt und ignoriert: " + ", ".join("--" + u for u in unknown)
            )
        used.append("ohne Übersetzung (Serienmodus)")

        flags_prep = dict(eff)
        flags_prep.pop("ar", None)  # the format comes from the series plan
        try:
            timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                flags_prep, _ar, err = await self._prepare_in_session(
                    session,
                    base,
                    wf,
                    h,
                    flags_prep,
                    user_valves,
                    images_in,
                    used,
                    file_markers,
                    name,
                    ctx["emitter"],
                    handle_ar=False,
                )
        except asyncio.TimeoutError:
            err = "Zeitüberschreitung bei der Verbindung zu ComfyUI."
        except aiohttp.ClientError as e:
            err = f"Verbindung zu ComfyUI fehlgeschlagen: {e}"
        if err:
            return prefix + err

        triggers = self._active_triggers(wf, h, flags_prep, used)
        seed_fixed = user_valves.seed
        if "seed" in eff and str(eff["seed"]).lstrip("-").isdigit():
            seed_fixed = int(eff["seed"])
        megapixels = self._megapixels(eff, user_valves)
        if megapixels > 0:
            used.append(f"{megapixels} MP")
        if ctx["defaults"] and user_valves.show_prompt:
            used.append(
                "Vorgaben: "
                + ", ".join(f"--{k} {v}".rstrip() for k, v in ctx["defaults"].items())
            )

        items = []
        for num, text, line_ar in entries:
            ratio, label = self._series_item_ratio(plan, line_ar, num, hints)
            items.append({"num": num, "prompt": text, "ratio": ratio, "label": label})

        head = prefix
        if hints:
            head += "*Hinweise: " + " · ".join(hints) + "*\n\n"
        render = {
            "emitter": ctx["emitter"],
            "user_id": ctx["user_id"],
            "user_valves": user_valves,
            "name": name,
            "h": h,
            "wf": wf,
            "items": items,
            "triggers": triggers,
            "seed_fixed": seed_fixed,
            "megapixels": megapixels,
            "used": info + used,
            "head": head,
            "slot_tag": str(
                ctx["metadata"].get("chat_id") or f"comfy-{random.randint(10000, 99999)}"
            ),
        }
        return self._series_render(render)

    async def _series_render(self, r: dict):
        """The rendering generator: holds ONE GPU slot for the whole series,
        renders the entries one after another and yields every result as
        soon as it is there. Owns slot release and the closing status line
        (pipe()'s finally has already run when this starts)."""
        emitter = r["emitter"]
        h = r["h"]
        items = r["items"]
        total = len(items)
        user_valves = r["user_valves"]
        base = self.valves.comfy_url.rstrip("/")
        started = time.monotonic()
        slot_id = None
        hb_task = None
        state = {"lost": False}
        ok_count = 0
        image_count = 0
        failed: list[int] = []
        finished = 0
        streak = 0
        end_reason = None
        cancelled = False
        abort_note = None
        try:
            if r["head"]:
                yield r["head"]

            if self.valves.use_alpaka_proxy:
                slot_id, slot_err = await self._acquire_slot(
                    emitter,
                    f"{r['name']} (Serie {total})",
                    r["slot_tag"],
                    status_label="Serie",
                )
                if slot_err:
                    end_reason = "kein GPU-Slot"
                    yield self._slot_error_text(slot_err)
                    return
                hb_task = asyncio.create_task(self._heartbeat_loop(slot_id, state))

            timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for i, item in enumerate(items, start=1):
                    num = item["num"]
                    wf_i = copy.deepcopy(r["wf"])
                    final_prompt = item["prompt"]
                    if r["triggers"]:
                        final_prompt = (
                            final_prompt.rstrip(" ,.") + ", " + ", ".join(r["triggers"])
                        )
                    self._set(wf_i, h["prompt"], final_prompt)
                    seed = (
                        r["seed_fixed"]
                        if r["seed_fixed"] >= 0
                        else random.randint(0, 2**53)
                    )
                    has_seed = self._set(wf_i, h.get("seed"), seed)
                    self._apply_resolution(
                        wf_i, h, item["ratio"], r["megapixels"], "", []
                    )
                    label = f"Serie: Nr. {num} ({i}/{total})"
                    res = await self._render_job(
                        session,
                        base,
                        wf_i,
                        h,
                        label,
                        emitter,
                        r["user_id"],
                        fetch_status=f"{label} Bilder werden abgeholt ...",
                    )
                    finished = i
                    head = f"**Nr. {num}** · {item['label']} · Bild {i}/{total}"
                    if res["kind"] == "ok":
                        ok_count += 1
                        image_count += len(res["blocks"])
                        streak = 0
                        block = f"{head}\n\n{item['prompt']}\n\n" + "\n\n".join(
                            res["blocks"]
                        )
                        if res["refined"]:
                            block += f"\n\n**Verwendeter Prompt:** {res['refined']}"
                        if user_valves.show_prompt:
                            line = []
                            if has_seed:
                                line.append(f"Seed {seed}")
                            line.append(item["label"])
                            line += res["notes"]
                            block += "\n\n*" + " · ".join(line) + "*"
                        yield block + "\n\n"
                        continue

                    failed.append(num)
                    streak += 1
                    block = (
                        f"**Nr. {num}** · fehlgeschlagen – {res['short']} · "
                        f"Bild {i}/{total}\n\n{item['prompt']}"
                    )
                    if res.get("detail"):
                        block += f"\n\n```\n{res['detail']}\n```"
                    yield block + "\n\n"
                    if res["kind"] == "conn":
                        end_reason = "ComfyUI nicht erreichbar"
                        break
                    if streak >= SERIES_FAIL_STREAK:
                        end_reason = f"{SERIES_FAIL_STREAK} Fehlschläge in Folge"
                        break

            elapsed = _duration(time.monotonic() - started)
            if image_count != ok_count:
                done_text = (
                    f"{ok_count} von {total} Prompts gerendert ({image_count} Bilder)"
                )
            else:
                done_text = f"{ok_count} von {total} Bildern"
            if end_reason:
                summary = (
                    f"**Serie abgebrochen** nach {finished}/{total} – {end_reason} · "
                    f"{done_text} · {elapsed}"
                )
            else:
                summary = f"**Serie fertig:** {done_text}"
                if failed:
                    summary += (
                        f" · {len(failed)} fehlgeschlagen (Nr. "
                        + ", ".join(str(f) for f in failed)
                        + ")"
                    )
                summary += f" · {elapsed}"
            used = list(r["used"])
            if state.get("lost"):
                used.append(
                    "Hinweis: die GPU-Slot-Lease war zwischenzeitlich verfallen "
                    "(Alpaka neu gestartet?) — die Serie lief trotzdem weiter"
                )
            out = "---\n\n" + summary
            if user_valves.show_prompt and used:
                out += "\n\n*" + " · ".join(used) + "*"
            yield out
        except asyncio.CancelledError as e:
            cancelled = True
            abort_note = getattr(e, "comfy_note", None)
            raise
        except GeneratorExit:
            # The consumer went away (e.g. connection closed)
            cancelled = True
            raise
        finally:
            if hb_task is not None:
                hb_task.cancel()
            if slot_id:
                # shield: the release must go through even on a second stop
                await asyncio.shield(self._release_slot(slot_id))
            if cancelled:
                text = f"Abgebrochen nach {finished}/{total}"
                if abort_note:
                    text += f" — {abort_note}"
            elif end_reason:
                text = f"Serie abgebrochen nach {finished}/{total} — {end_reason}"
            else:
                text = (
                    f"Serie fertig: {ok_count}/{total} in "
                    f"{_duration(time.monotonic() - started)}"
                )
            await self._emit(emitter, text, done=True)