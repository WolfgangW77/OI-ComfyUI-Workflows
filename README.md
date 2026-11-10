# ComfyUI Workflows – a Pipe function for Open WebUI

Exposes every ComfyUI workflow in a directory as its own **model** in Open WebUI.
Type a prompt, add a few flags, get images back in the chat – no ComfyUI UI, no
node fiddling for end users.

```
A tabby cat chasing a butterfly in a meadow --ar 16:9 --batch 2 --seed 42
```

Built for a small self-hosted setup (Open WebUI + ComfyUI + Ollama on the same
box), including non-technical family members as users. That shaped a lot of the
design: strict validation instead of silent failure, defaults that survive
across chats, and a manual reachable from inside the chat. Optionally the pipe
shares the GPU with chat models through the
[Alpaka Ollama Log Proxy](https://github.com/WolfgangW77/Alpaka-Ollama-Log-Proxy).

> **Language note:** the code, comments and this README are English. The
> **user-facing texts** (help output, in-chat manual, status and error
> messages, valve descriptions) are **German**, because that is what the
> people using this instance speak. They are plain strings in the source and
> easy to translate if you need another language.

## Features

- **One workflow = one model.** Drop an API-format workflow JSON into a
  directory; it shows up in the model picker under its file name. No restart
  needed – files are re-read when they change.
- **Flags in the prompt.** `--ar`, `--mp`, `--batch`, `--steps`, `--seed`,
  `--cfg`, `--guidance`, `--no` (negative prompt), `--translate`, `--triggers`,
  `--arauto`. `--`, the en dash and the em dash all work.
- **Workflow-specific flags via markers.** Rename any node in ComfyUI to
  `PIPE_something` (or `PIPE_something:field`) and it becomes `--something`.
  Markers on model files (`PIPE_VAE`, `PIPE_MODEL`, `PIPE_CLIP`) accept a
  fragment of the file name and are matched against ComfyUI's option lists.
- **LoRA control.** `--lora1 0.4` sets strength, `--lora1 cat_v1` swaps the
  file by name fragment, `--lora1 cat_v1:0.8` does both. `PIPE_LOCK …` on a
  LoRA loader keeps it out of the numbering. Trigger words per LoRA are
  appended automatically (valve `lora_triggers`, only for LoRAs with a
  strength other than 0); `--triggers 0` switches them off per message or
  as a saved default.
- **Option listing.** Any flag with an option list gets a listing twin:
  `--loras`, `--vaes`, `--models`, `--ars`, a search term behind it filters the
  output.
- **Persistent defaults.** A message consisting only of flags saves them as
  defaults – per user and per workflow, valid in every chat. A flag without a
  value resets that entry; `--reset` clears all. Precedence:
  message > defaults > user valves > workflow file.
- **Validation before it hurts.** Values are checked against ComfyUI's option
  lists when saving *and* when rendering, so nothing is accepted in one place
  and rejected in the other.
- **Optional prompt translation** via a local Ollama model, with quoted text
  protected from translation (useful for lettering in the image).
- **Image editing workflows.** Attach an image; if the workflow has an image
  input (`PIPE_IMAGE` or a `LoadImage` node), the image alone is enough – no
  prompt required.
- **Aspect ratio from the image.** For workflows with an image input the
  output format follows the attached image: the pipe reads its dimensions
  and picks the closest entry from the `ResolutionSelector` (or sets
  width:height directly for plain latent nodes). An explicit `--ar` always
  wins; `--arauto 0` switches it off per message or as a saved default,
  the `auto_ar` user valve per user, `auto_ar_from_image` globally.
- **Per-model system prompt.** The system prompt of an Open WebUI workspace
  model is prepended to every job. Typed text extends it. Handy for
  "make this cat look like *our* cat" style presets.
  Blocks Open WebUI itself adds to the system message – attached-file
  descriptions, the `<memory_context>` block of the memory feature, the
  `[CONVERSATION SUMMARY]` of Context Compaction – are stripped first, so
  neither memories nor chat summaries leak into the image prompt.
- **GPU sharing with chat models (optional).** With Alpaka (v5.3+) the pipe
  takes a GPU slot before the translation step and holds it through the
  ComfyUI job, so image and chat jobs don't fight over VRAM. While it waits,
  the status line shows the position in Alpaka's queue, and the stop button
  cancels the wait. The slot is released on every end path (success, error,
  timeout, stop) and kept alive by a heartbeat; the slot holder's own
  translation requests are let through immediately. Uploads and option
  queries run before the slot is taken, and waiting for the slot does not
  count against `timeout_seconds`.
- **Jobs are withdrawn, not orphaned.** The stop button, the compute cap
  (`timeout_seconds`) and a lost connection while waiting for the result all
  withdraw the job from ComfyUI before the GPU slot is released: pending jobs
  are deleted from the queue, the running one is interrupted (only if it
  really is ours). The outcome is reported in the chat.
- **Admin clean-up and clean handover.** Admin-only flags handled inside the
  pipe, without slot, translation or ComfyUI job – they also work when every
  chat model is stuck: abort running Ollama requests, unload Ollama models,
  free ComfyUI's VRAM, and view or switch Alpaka's clean handover (automatic
  VRAM hand-back between Ollama and ComfyUI, Alpaka v5.4+). See
  [Admin commands](#admin-commands).
- **Robustness.** One automatic retry on sporadic ComfyUI execution errors,
  queue position in the status line, tracebacks clipped in the middle so the
  actual cause stays visible, unique upload names so queued jobs don't
  overwrite each other's input image.
- **Auto titles for image-only chats.** Chats without typed text get
  `YYYYMMDD HH:MM <model name>` as title – only if they have none yet.
- **Images stored as files** in Open WebUI's file storage (with automatic
  fallback to inline Base64), with the MIME type taken from the file name
  (PNG, JPEG, WebP, GIF).

## Requirements

- Open WebUI (Pipe functions with `__event_emitter__`, `__task__` and
  `__metadata__` support – any reasonably recent version)
- ComfyUI reachable from the Open WebUI container over HTTP
- Python package `aiohttp` (declared in the function header; Open WebUI
  installs it). Pillow is used for reading image dimensions if present
  (it ships with Open WebUI); without it a small built-in header parser
  covers PNG, JPEG and WebP.
- Optional: Ollama for prompt translation; the `ResolutionSelector` custom
  node if you want `--ar` with named presets
- Optional: the [Alpaka Ollama Log Proxy](https://github.com/WolfgangW77/Alpaka-Ollama-Log-Proxy)
  for GPU sharing – v5.3+ for the slot, v5.4+ for `--handover`.
  **`use_alpaka_proxy` is on by default:** without Alpaka, switch it off,
  otherwise every image job ends with a clear "no GPU slot" error.

## Installation

1. In Open WebUI go to **Admin Panel → Functions → +** and paste the contents
   of `comfyui_workflows.py`. Save and enable it.
2. Create the workflow directory inside the Open WebUI data volume:
   `/app/backend/data/comfy_workflows`
3. Set the **Valves** (gear icon on the function), at least `comfy_url`.
   Without Alpaka: switch `use_alpaka_proxy` off and, if you want
   translation, point `ollama_url` at Ollama directly (usually port 11434).
4. Export a workflow from ComfyUI and drop it into the directory (see below).
5. Pick the new model in a chat and send `--help`.

## Preparing a workflow in ComfyUI

1. Rename the node that receives the prompt text to `PIPE_PROMPT`.
   (If you don't, the pipe tries to find the positive prompt via the
   sampler – but explicit is better.)
2. Optional markers:
   - `PIPE_NEGATIVE` – negative prompt node, enables `--no`
   - `PIPE_IMAGE` – image input for editing workflows
   - `PIPE_PROMPT_RESULT` – a text output node whose result (e.g. a refined
     prompt) is shown under the image
   - `PIPE_LOCK …` – on a LoRA loader: fixed, not exposed as `--loraN`
   - `PIPE_INTERNAL …` – the node is removed from the job before it is
     sent to ComfyUI (preview/debug outputs that should stay in the
     canvas and out of the chat; dead-end nodes only)
   - `PIPE_NAME` or `PIPE_NAME:field` – any other node: becomes `--name`
3. Run the workflow once successfully, then **Workflow → Export (API)**.
   The normal save format is rejected with a clear message.
4. Copy the file to the workflow directory. The file name becomes the model
   name.
5. Send `--help` in a chat with the new model. It lists what was detected –
   including problems such as a missing image output node or a marker
   pointing at a non-existent field.

Detected automatically by `class_type`: seed (RandomNoise, KSampler, …),
steps (BasicScheduler, KSampler), cfg (CFGGuider, KSampler), FluxGuidance,
resolution (EmptyLatentImage, EmptySD3LatentImage, ResolutionSelector, plus
any node with plain width/height inputs), LoRAs (LoraLoader,
LoraLoaderModelOnly), image input (LoadImage), image outputs (SaveImage,
PreviewImage, …).

After re-exporting a workflow, send `--help` again – node IDs and therefore
LoRA slot numbers can shift, and stale defaults may need a `--reset`.

## Usage in the chat

| Command | Effect |
|---|---|
| `--help` | What the pipe detected in this workflow, available flags, saved defaults |
| `--anleitung` | Full manual (admins get an extra section) |
| `--loras`, `--vaes`, `--ars`, … | List options; add a search term to filter |
| `--reset` | Delete all saved defaults for this workflow |
| `--arauto 0/1` | Aspect ratio from the attached image off/on (image workflows only) |
| flags only, no prompt | Save these flags as defaults |
| `--flag` without value | Reset that one entry (permanently when saving, once when rendering) |

Turn on the user valve **show_prompt** at first – it adds an info line under
every image with everything the pipe did (seed, resolution, translation,
LoRAs, title handling …). That line is where every "why did it do that?"
question gets answered.

### Admin commands

Restricted to the Open WebUI role `admin` and listed in `--help` /
`--anleitung` for admins only. They run inside the pipe – no GPU slot, no
translation, no ComfyUI job – need only `proxy_url` (or `comfy_url` for
`--unload-comfy`) and work with `use_alpaka_proxy` off.

| Command | Effect |
|---|---|
| `--kill-ollama-tasks` | Abort all running Ollama requests via Alpaka |
| `--unload-ollama [name]` | Unload Ollama models via Alpaka (`keep_alive` 0); without a name all of them, a name fragment selects one |
| `--unload-comfy` | ComfyUI's `/free`: unload models, clear the execution cache |
| `--handover` | Show the state of Alpaka's clean handover |
| `--handover on\|off\|custom` | Set the clean-handover mode |
| `--handover-comfy 0/1` | Free ComfyUI's VRAM before chat jobs (switches the mode to `custom`) |
| `--handover-ollama 0/1` | Unload Ollama models before image jobs (switches the mode to `custom`) |

Order in an emergency: first kill (stops what is computing), then unload
(frees VRAM on the Ollama and/or ComfyUI side). Handover changes are
persisted by Alpaka; no proxy restart needed.

## Valves

**Admin valves** (gear icon on the function):

| Valve | Default | Meaning |
|---|---|---|
| `comfy_url` | `http://host.docker.internal:8189` | ComfyUI base URL |
| `timeout_seconds` | `900` | Compute cap from submission; on expiry the job is withdrawn from ComfyUI. `0` = no cap. Waiting for the GPU slot does not count; fixed transport timeouts (connect 10 s, read 120 s) detect dead connections |
| `max_batch` | `8` | Upper limit for `--batch` |
| `retry_on_error` | on | Retry once on a ComfyUI execution error |
| `store_images_as_files` | on | Store images in Open WebUI's file storage instead of inline Base64 |
| `ollama_url` | `http://host.docker.internal:11435` | Base URL for translation – Alpaka by default; without Alpaka Ollama directly (usually port 11434) |
| `proxy_url` | `http://host.docker.internal:11435` | Alpaka base URL (slot and admin endpoints) |
| `use_alpaka_proxy` | on | Take a GPU slot before every image job; if Alpaka is unreachable while on, the job fails with a clear message instead of rendering ungated |
| `translate_model` | empty | Ollama model for translation; empty = no translation |
| `translate_keep_alive` | `5m` | How long the translation model stays loaded |
| `translate_system` | built-in | System instruction for the translation (a glossary fits in here) |
| `lora_triggers` | empty | One `name_fragment \| trigger word` per line |
| `auto_ar_from_image` | on | Aspect ratio from the attached image, globally |

**User valves** (slider icon in the chat): `aspect_ratio`, `megapixels`,
`batch_size`, `steps`, `seed`, `translate`, `show_prompt`, `auto_ar`.

Precedence for the aspect ratio, first match wins: `--ar` in the message or
saved defaults, then the attached image (if `auto_ar` is on), then the
`aspect_ratio` user valve, then the workflow file.

## Storage locations

- Workflows: `/app/backend/data/comfy_workflows/*.json`
- Saved defaults: `/app/backend/data/comfy_pipe_defaults.json`
- Images: Open WebUI file storage (plus ComfyUI's own output folder)
- Uploaded input images: ComfyUI's input folder, named
  `owui_upload_<timestamp>_<random>_<n>.<ext>` – these accumulate; clean up
  occasionally if disk space matters

## A note on Open WebUI internals

Three things rely on Open WebUI internals rather than a public API:

- storing images as files (`open_webui.models.files`,
  `open_webui.storage.provider`)
- setting chat titles (`open_webui.models.chats`)
- recognising what Open WebUI itself writes into the system message (the
  `<memory_context>` block, the `[CONVERSATION SUMMARY]` prefix)

The first two are wrapped so that a changed internal API degrades gracefully
(images fall back to inline Base64, titles are simply not set) and the reason
shows up in the info line. For the third, a changed format would let
memories or chat summaries reach the image prompt again; the info line notes
every time such a block was removed. If an Open WebUI update breaks one of
them, that is where to look.

## Versioning

The version history lives in the docstring at the top of the source file.
Each release is a complete file; there are no patches to apply.

## Development

Written with AI assistance (Claude by Anthropic). Design decisions,
testing against the live setup and integration are the author's; the
code was reviewed and is maintained by the author.

## License

MIT – see `LICENSE`.