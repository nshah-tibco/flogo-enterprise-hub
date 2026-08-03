# Create Image Activity

OpenAI image-generation activity for Flogo. Wraps `POST /images/generations`,
supporting `dall-e-2`, `dall-e-3`, and the GPT image model family
(`gpt-image-1`, `gpt-image-1-mini`, `gpt-image-1.5`, `gpt-image-2`,
`gpt-image-2-2026-04-21`).

## Settings

| Name | Required | Description |
|------|----------|-------------|
| `endPointURL` | yes | OpenAI API base URL, e.g. `https://api.openai.com/v1` |
| `apiKey`      | yes | OpenAI API key |

## Inputs

`prompt` is required. All others are optional but **conditionally valid**
depending on `model`. The activity rejects invalid combinations before calling
the API.

| Input | Type | Notes |
|-------|------|-------|
| `prompt` | string | Max length: 1000 (dall-e-2), 4000 (dall-e-3), 32000 (gpt-image) |
| `model` | string | `dall-e-2` (default), `dall-e-3`, or a `gpt-image-*` model |
| `numberOfImages` | integer | 1–10. Must be 1 for `dall-e-3` |
| `size` | string | Allowed values depend on model. `gpt-image-2` accepts arbitrary `WxH` |
| `quality` | string | `standard` (dall-e-2/3), `hd` (dall-e-3), `low`/`medium`/`high` (gpt-image), `auto` |
| `style` | string | `vivid` or `natural`. **dall-e-3 only** |
| `responseFormat` | string | `url` or `b64_json`. **dall-e-2/3 only**, mutually exclusive with `outputFormat` |
| `outputFormat` | string | `png`, `jpeg`, `webp`. **gpt-image only** |
| `background` | string | `transparent`/`opaque`/`auto`. **gpt-image only**. `transparent` requires `outputFormat ∈ {png, webp}` |
| `outputCompression` | integer | 0–100. **gpt-image only**, only when `outputFormat ∈ {webp, jpeg}` |
| `moderation` | string | `low` or `auto`. **gpt-image only** |
| `user` | string | End-user identifier |

## Outputs

| Output | Type | Notes |
|--------|------|-------|
| `created` | integer | Unix timestamp |
| `background` | string | Echoed background (gpt-image) |
| `outputFormat` | string | Echoed output format (gpt-image) |
| `quality` | string | Echoed quality |
| `size` | string | Echoed size |
| `data` | array | One entry per generated image: `{ b64_json, url, revised_prompt }` |
| `usage` | object | Token usage details (gpt-image) |

## Limitations

- `stream` and `partial_images` are **not** supported. A separate streaming
  activity is required for SSE consumption.

## Tests

Unit tests for input validation run with no credentials:

```bash
go test ./activity/imageCreate/
```

Integration tests require a real key. Copy `.env.example` to `.env`, fill in
`OPEN_AI_API_KEY`, set `RUN_INTEGRATION=1`, then:

```bash
go test ./activity/imageCreate/ -run Integration -v
```

## Parameter dependencies

Most of the activity's settings are conditionally valid depending on the
chosen `model`. The sections below summarize how the fields relate to each
other; these rules are enforced at runtime by `validateInput()` in
[activity.go](activity.go).

### Tabs

| Tab           | Field                                                                                                              |
| ------------- | ------------------------------------------------------------------------------------------------------------------ |
| Configuration | `endPointURL`, `apiKey`, `model`, `numberOfImages`, `size`, `quality`, `style`, `responseFormat`, `outputFormat`, `background`, `outputCompression`, `moderation`, `user` |
| Input         | `prompt`                                                                                                           |

### Model families

The `model` setting drives almost every other rule. Models are grouped into
four families:

| Family        | Models                                                       |
| ------------- | ------------------------------------------------------------ |
| `dall-e-2`    | `dall-e-2` (also the default when `model` is empty)          |
| `dall-e-3`    | `dall-e-3`                                                   |
| `gpt-image`   | `gpt-image-1`, `gpt-image-1-mini`, `gpt-image-1.5`           |
| `gpt-image-2` | `gpt-image-2`, `gpt-image-2-2026-04-21` (and other variants) |

### Per-parameter rules

#### `prompt` (input, required)

Maximum length depends on the model family:

| Family        | Max chars |
| ------------- | --------- |
| `dall-e-2`    | 1 000     |
| `dall-e-3`    | 4 000     |
| `gpt-image*`  | 32 000    |

#### `numberOfImages` (number of images)

- Range: `1`–`10`.
- `dall-e-3` only supports `numberOfImages=1`.
- A value of `0` is treated as "not provided" and is omitted from the request.

#### `size`

| Family        | Allowed values                                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `dall-e-2`    | `256x256`, `512x512`, `1024x1024`                                                                                       |
| `dall-e-3`    | `1024x1024`, `1792x1024`, `1024x1792`                                                                                   |
| `gpt-image`   | `1024x1024`, `1536x1024`, `1024x1536`, `auto`                                                                           |
| `gpt-image-2` | The three sizes above, **plus** any `WxH` that is divisible by 16, has aspect ratio between 1:3 and 3:1, and ≤ 3840x2160 |

`size=auto` is only valid for `gpt-image` / `gpt-image-2`.

#### `quality`

| Family        | Allowed values         |
| ------------- | ---------------------- |
| `dall-e-2`    | `standard`, `auto`, `` (empty — recommended for dall-e-2; OpenAI rejects sending `quality` for this model in some cases) |
| `dall-e-3`    | `standard`, `hd`, `auto` |
| `gpt-image*`  | `low`, `medium`, `high`, `auto` |

Empty `quality` (`""`) is omitted from the request entirely, which is the
safest choice for `dall-e-2`.

#### `style`

- Only valid for `dall-e-3`.
- Allowed values: `vivid`, `natural` (or empty to omit).

#### `responseFormat` vs `outputFormat`

These are **mutually exclusive** — set at most one.

| Field            | Valid for                | Allowed values             |
| ---------------- | ------------------------ | -------------------------- |
| `responseFormat` | `dall-e-2`, `dall-e-3`   | `url`, `b64_json`          |
| `outputFormat`   | `gpt-image`, `gpt-image-2` | `png`, `jpeg`, `webp`    |

`url` responses from `dall-e-2/3` are valid for 60 minutes.

#### `background`

- Only valid for `gpt-image` / `gpt-image-2`.
- Allowed values: `transparent`, `opaque`, `auto`.
- `background=transparent` requires `outputFormat` to be `png` or `webp`
  (or empty so the API picks a compatible default).

#### `outputCompression`

- Only valid for `gpt-image` / `gpt-image-2`.
- Range: `1`–`100`.
- Only takes effect when `outputFormat` is `webp` or `jpeg`.
- A value of `0` is treated as "not provided" and is omitted from the request
  (Flogo's metadata reflection cannot distinguish a missing `int` from `0`).

#### `moderation`

- Only valid for `gpt-image` / `gpt-image-2`.
- Allowed values: `low`, `auto`.

#### `user`

- Free-form opaque identifier used by OpenAI for abuse detection.
- No model dependency.

### Quick compatibility matrix

A `✓` means the field is accepted, `–` means it is rejected (or, where noted,
silently ignored by skipping it from the request).

| Field               | dall-e-2 | dall-e-3 | gpt-image | gpt-image-2 |
| ------------------- | :------: | :------: | :-------: | :---------: |
| `prompt`            | ✓        | ✓        | ✓         | ✓           |
| `numberOfImages` (>1) | ✓        | –        | ✓         | ✓           |
| `size` standard     | ✓        | ✓        | ✓         | ✓           |
| `size=auto`         | –        | –        | ✓         | ✓           |
| `size` arbitrary    | –        | –        | –         | ✓           |
| `quality=standard`  | ✓        | ✓        | –         | –           |
| `quality=hd`        | –        | ✓        | –         | –           |
| `quality=low/med/high` | –     | –        | ✓         | ✓           |
| `quality=auto`      | ✓¹       | ✓        | ✓         | ✓           |
| `style`             | –        | ✓        | –         | –           |
| `responseFormat`    | ✓        | ✓        | –         | –           |
| `outputFormat`      | –        | –        | ✓         | ✓           |
| `background`        | –        | –        | ✓         | ✓           |
| `outputCompression` | –        | –        | ✓²        | ✓²          |
| `moderation`        | –        | –        | ✓         | ✓           |
| `user`              | ✓        | ✓        | ✓         | ✓           |

¹ `quality` is best left empty for `dall-e-2`; some OpenAI deployments reject the parameter outright.
² Only effective when `outputFormat` is `webp` or `jpeg`.
