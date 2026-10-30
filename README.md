# yt-tr

A small command-line tool for fetching YouTube transcripts from a video ID or full YouTube URL.

## Features

- Plain text, SRT, WebVTT, and JSON output
- Preferred language selection with automatic fallback
- Language listing
- Save to the current directory or an explicit path
- Protection against accidental overwrites
- Works with watch URLs, `youtu.be`, Shorts, embeds, and live links

## Install

### Linux/macOS

```bash
git clone https://github.com/EorlSam/yt-tr.git
cd yt-tr
bash install.sh
```

The installer creates an isolated user virtual environment and installs `yt-tr` in `~/.local/bin`.

### Windows PowerShell

```powershell
git clone https://github.com/EorlSam/yt-tr.git
cd yt-tr
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The Windows installer creates an isolated virtual environment under `%LOCALAPPDATA%\yt-tr`, installs the command in `%USERPROFILE%\bin`, and adds that folder to the user PATH. Open a new terminal after installation.

## Usage

```bash
yt-tr VIDEO_ID_OR_URL [language]
yt-tr "https://www.youtube.com/watch?v=dQw4w9WgXcQ" en
yt-tr VIDEO_ID en -t
yt-tr VIDEO_ID --format vtt -s
yt-tr VIDEO_ID --format json -o transcript.json
yt-tr VIDEO_ID --list-languages
```

Options:

```text
-l, --language CODE       Preferred language; repeatable
-t, --timestamps          SRT timestamps
    --format FORMAT       txt, srt, vtt, or json
-s, --save                Save with an automatic filename
-o, --output FILE         Save to an explicit path
    --force               Overwrite an existing file
    --list-languages      Show available transcript languages
-q, --quiet               Suppress save and fallback status messages
```

If the requested language is unavailable, `yt-tr` uses the first available transcript and reports the fallback.

## Note

YouTube may temporarily block automated transcript requests from some IP addresses. The tool reports that condition clearly; using a proxy is the appropriate workaround when needed.
