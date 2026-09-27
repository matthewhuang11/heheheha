# Design

The scoutbot dashboard is a quiet dark console with one loud thing on it: the mission status. A judge a meter away should be able to tell what the robot sees, whether it's searching on its own or syncing, and who it found. Recorded from the built `dashboard/index.html`.

The first version (a "rescue beacon" instrument skin) was rejected as too busy for a demo; the lesson is kept here: fewer readouts, bigger type, one state color at a time.

## Hierarchy

The layout is big simple tiles, modeled on a teammate's reference: a centered title, a left column of tiles, the feed in the center, and controls on the right. Survivors run in a strip along the bottom.

1. **Status tile (top left):** one huge colored word (`ready`, `searching`, `returning`, `syncing`, `all clear`), one plain line under it, and the mission clock only while searching. The tile tints itself with the state color.
2. **Live feed (center):** the largest element. Two overlays: `no connection · recording on the robot` while searching, and a centered chip (`person 2.4 m to the left`) whose arrow turns toward the person.
3. **Controls (right):** an arrow cross with the round red stop button in its center, and the three mission buttons below it (send it in, bring it back, back in range), numbered in demo order.
4. **Survivors found:** a big orange number under the status tile, with a small map tile under that.
5. **Survivor strip (bottom):** photo cards with a triage tag. Tapping one slides in a drawer with the big photo, what they said, the audio, and the report as labeled rows.

## Tokens

| Token | Value | Role |
|---|---|---|
| `--bg` | `#0d0f12` | page |
| `--panel` / `--panel-2` | `#15181d` / `#1c2027` | panels / cards and hover |
| `--line` | `#262b33` | dividers, quiet buttons, map dots |
| `--text` / `--muted` / `--faint` | `#eef1f4` / `#9aa4af` / `#6b7580` | text levels |
| `--accent` | `#ff6b2c` | survivors, sync state, focus ring |
| `--search` | `#7c6cff` | the blackout / searching state, pending survivors |
| `--return` | `#f5b83d` | coming back; also the DELAYED tag |
| `--ok` | `#3ecf8e` | all triaged; also the MINOR tag |
| `--stop` | `#cf383e` | stop button, IMMEDIATE tag, rec dot |

`--state` is set to one of these per station. The banner tints itself 16% with it, and the radar ring and progress bar use it.

Type: **Archivo**, self-hosted at `dashboard/fonts/archivo-latin.woff2`. Body text is 15px. The headline is 30px at weight 750, `font-stretch: 112%`. Numerals are tabular.

Radii: panels 18px, cards 14px, buttons 10px, tags 7px.

## Motion

Easing is `cubic-bezier(0.16, 1, 0.3, 1)` everywhere. Everything is disabled under `prefers-reduced-motion`.

- **State change:** the banner tint crossfades over 0.9 s.
- **Searching:** a conic radar sweep turns every 2.4 s, and the rec dot blinks.
- **Returning or syncing:** the radar center pulses.
- **Survivor found:** the card arrives (rise, un-blur, fade over 0.7 s), and a ring pings out of their dot on the map.
- **Survivor triaged:** the photo develops from a latent gray to full color over 2.6 s. This is the signature moment.
- **Map:** the robot glides between polls on a frame loop, and the view zooms smoothly as the explored area grows.
- **Target chip:** the arrow rotates toward the person's bearing.

## Rules

- One state color on screen at a time. The accent is for survivors.
- No readout goes on the main surface unless a judge needs it; everything else lives in the details line.
- Red is only for stop, IMMEDIATE, and recording.
- Positions are dead reckoning, so they're shown to 0.1 m and never presented as survey-grade.
