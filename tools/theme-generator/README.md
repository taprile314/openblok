Theme generator
===============

Procedurally generates the `synthwave`, `nes`, `crt_verde`, `dracula` and `aurora` themes:
block textures, ghost, well overlays, logo recolor, gameplay wallpaper and sound effects.
Nothing is hand-drawn or sampled; everything comes from the code in `gen.py`.

Requirements: Python 3, `numpy`, `pillow`, and `ffmpeg` built with `libvorbis`.

```sh
python3 -m venv venv && venv/bin/pip install numpy pillow
venv/bin/python gen.py              # all themes
venv/bin/python gen.py synthwave    # just one
```

The themes are written to `out/<name>/`. Sound effects are written as WAV; the game
looks them up by their `.ogg` names, so convert them before installing:

```sh
for w in out/*/sfx/*.wav; do
    ffmpeg -loglevel error -y -i "$w" -c:a libvorbis -q:a 5 "${w%.wav}.ogg" && rm "$w"
done
```

Each theme is defined in the `THEMES` table at the bottom of `gen.py`: piece palette,
block style, well colors, UI colors (see `THEMES.md` in the repository root), wallpaper
function and the synth style/key of its sound effects.
