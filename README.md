# yt-tr

A small command-line tool for fetching transcripts from YouTube and Rumble videos.

## Features

- Plain text, SRT, WebVTT, and JSON output
- YouTube watch, `youtu.be`, Shorts, embeds, and live links
- Rumble links such as `https://rumble.com/v123-example-title.html`
- Preferred language selection with automatic fallback
- Language listing and safe save-to-file options

Rumble subtitle extraction uses `yt-dlp`; YouTube extraction continues to use `youtube-transcript-api`.

## Usage

```bash
yt-tr "https://www.youtube.com/watch?v=dQw4w9WgXcQ" en
yt-tr "https://rumble.com/v123-example-title.html" en --format vtt
yt-tr VIDEO_ID --format json -o transcript.json
yt-tr VIDEO_ID --list-languages
```

