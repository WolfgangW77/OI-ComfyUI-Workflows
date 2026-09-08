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
across chats, and a manual reachable from inside the chat.

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
  `--cfg`, `--guidance`, `--no` (negative prompt), `--translate`, `--triggers`.
  Both `--` and the em dash work.
- **Workflow-specific flags via markers.** Rename any node in ComfyUI to
  `PIPE_something` (or `PIPE_something:field`) and it becomes `--something`.
  Markers on model files (`PIPE_VAE`, `PIPE_MODEL`, `PIPE_CLIP`) accept a
  fragment of the file name and are matched against ComfyUI's option lists.
- **LoRA control.** `--lora1 0.4` sets strength, `--lora1 cat_v1` swaps the
  file by name fragment, `--lora1 cat_v1:0.8` does both. `PIPE_LOCK …` on a
  LoRA loader keeps it out of the numbering. Trigger words per LoRA are
  appended automatically (configurable).
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
- **Stop button works.** Cancelling in Open WebUI withdraws the job from
  ComfyUI: pending jobs are deleted from the queue, the running one is
  interrupted (only if it really is ours).
- **Robustness.** One automatic retry on sporadic ComfyUI execution errors,
  queue position in the status line, tracebacks clipped in the middle so the
  actual cause stays visible, unique upload names so queued jobs don't
  overwrite each other's input image.
- **Auto titles for image-only chats.** Chats without typed text get
  `YYYYMMDD HH:MM <model name>` as title – only if they have none yet.
- **Images stored as files** in Open WebUI's file storage (with automatic
  fallback to inline Base64).

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

## Installation

1. In Open WebUI go to **Admin Panel → Functions → +** and paste the contents
   of `comfyui_workflows_v*.py`. Save and enable it.
2. Create the workflow directory inside the Open WebUI data volume:
   `/app/backend/data/comfy_workflows`
3. Set the **Valves** (gear icon on the function), at least `comfy_url`.
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

## Valves

**Admin valves** (gear icon on the function): `comfy_url`, `timeout_seconds`,
`max_batch`, `retry_on_error`, `store_images_as_files`, `ollama_url`,
`translate_model`, `translate_keep_alive`, `translate_system`,
`lora_triggers` (one `name_fragment | trigger word` per line),
`auto_ar_from_image`.

**User valves** (slider icon in the chat): `aspect_ratio`, `megapixels`,
`batch_size`, `steps`, `seed`, `translate`, `show_prompt`, `auto_ar`.

Precedence for the aspect ratio: `--ar` in the message or saved defaults
> attached image (if `auto_ar` is on) > `aspect_ratio` user valve >
workflow file.

## Storage locations

- Workflows: `/app/backend/data/comfy_workflows/*.json`
- Saved defaults: `/app/backend/data/comfy_pipe_defaults.json`
- Images: Open WebUI file storage (plus ComfyUI's own output folder)
- Uploaded input images: ComfyUI's input folder, named
  `owui_upload_<timestamp>_<random>_<n>.<ext>` – these accumulate; clean up
  occasionally if disk space matters

## A note on Open WebUI internals

Two features import Open WebUI's internal modules rather than a public API:

- storing images as files (`open_webui.models.files`,
  `open_webui.storage.provider`)
- setting chat titles (`open_webui.models.chats`)

Both are wrapped so that a changed internal API degrades gracefully (images
fall back to inline Base64, titles are simply not set) and the reason shows
up in the info line. If an Open WebUI update breaks one of them, that is
where to look.

## Versioning

The version history lives in the docstring at the top of the source file.
Each release is a complete file; there are no patches to apply.

## Development

Written with AI assistance (Claude by Anthropic). Design decisions,
testing against the live setup and integration are the author's; the
code was reviewed and is maintained by the author.

## License

MIT – see `LICENSE`.