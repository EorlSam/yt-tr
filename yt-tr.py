#!/usr/bin/env python3
"""Fetch YouTube and Rumble transcripts with friendly CLI output and file formats."""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs


@dataclass
class TranscriptSnippet:
    text: str
    start: float
    duration: float


def is_rumble_url(value: str) -> bool:
    """Return whether value is a Rumble URL."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower().split(":", 1)[0].endswith("rumble.com")


def rumble_video_id_from(value: str) -> str:
    """Extract the short Rumble video ID from a video URL."""
    path = urlparse(value).path
    match = re.search(r"/(v[0-9a-z]+)(?:[-/.?]|$)", path, re.IGNORECASE)
    if not match:
        raise ValueError("Rumble URL does not contain a video ID")
    return match.group(1)


def video_id_from(value: str) -> str:
    """Extract a YouTube video ID, or return a plain ID unchanged."""
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            if parsed.netloc.endswith("youtu.be"):
                return parts[0]
            if parts[0] in {"shorts", "embed", "live"} and len(parts) > 1:
                return parts[1]
    match = re.search(r"(?:[?&]v=|youtu\.be/|/(?:shorts|embed|live)/)([^&#/?]+)", value)
    return match.group(1) if match else value


def timestamp(seconds: float, decimal: str = ",") -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{decimal}{millis:03}"


def render(snippets, output_format: str) -> str:
    rows = [
        {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
        for snippet in snippets
    ]
    if output_format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    if output_format == "txt":
        return "\n".join(row["text"] for row in rows) + "\n"
    if output_format == "vtt":
        blocks = ["WEBVTT", ""]
        for row in rows:
            blocks.extend([
                f"{timestamp(row['start'], '.')} --> {timestamp(row['start'] + row['duration'], '.')}" ,
                row["text"],
                "",
            ])
        return "\n".join(blocks)
    blocks = []
    for index, row in enumerate(rows, 1):
        blocks.extend([
            str(index),
            f"{timestamp(row['start'])} --> {timestamp(row['start'] + row['duration'])}",
            row["text"],
            "",
        ])
    return "\n".join(blocks)


def parse_webvtt(content: str):
    """Parse the timed text returned by Rumble into transcript snippets."""
    snippets = []
    blocks = re.split(r"\r?\n\s*\r?\n", content.lstrip("\ufeff"))
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None or timing_index + 1 >= len(lines):
            continue
        start_text, end_text = (part.strip().split(" ", 1)[0] for part in lines[timing_index].split("-->"))
        try:
            start = _vtt_time(start_text)
            end = _vtt_time(end_text)
        except ValueError:
            continue
        text = " ".join(lines[timing_index + 1:])
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            snippets.append(TranscriptSnippet(text, start, max(0, end - start)))
    return snippets


def _vtt_time(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(value)


def fetch_rumble_transcript(url: str, requested, cookies_from_browser=None):
    """Fetch a Rumble subtitle track through Rumble's embed metadata API."""
    from yt_dlp import YoutubeDL

    video_id = rumble_video_id_from(url)
    metadata_url = (
        "https://rumble.com/embedJS/u3/?request=video&ver=2&v="
        + video_id
    )
    options = {
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://rumble.com/",
        },
    }
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    with YoutubeDL(options) as ydl:
        info = json.loads(ydl.urlopen(metadata_url).read().decode("utf-8"))
        tracks = {
            language: [{"url": urljoin("https://rumble.com/", details["path"]), "ext": "vtt"}]
            for language, details in (info.get("cc") or {}).items()
            if details.get("path")
        }
        selected_code = next((code for code in requested if code in tracks), None)
        if selected_code is None and tracks:
            selected_code = next(iter(tracks))
        if selected_code is None:
            return [], None
        track = tracks[selected_code]
        source = next((entry for entry in track if entry.get("ext") == "vtt"), track[0])
        content = ydl.urlopen(source["url"]).read().decode("utf-8")
        return parse_webvtt(content), selected_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-tr",
        description="Fetch a YouTube or Rumble transcript from a video ID or full URL.",
    )
    parser.add_argument("video", help="YouTube video ID, YouTube URL, or Rumble URL")
    parser.add_argument("language_positional", nargs="?", metavar="language", help="Preferred language code")
    parser.add_argument("-l", "--language", dest="languages", action="append", help="Preferred language code; repeatable")
    parser.add_argument("-t", "--timestamps", action="store_true", help="Include timestamps in SRT format")
    parser.add_argument("--format", choices=("txt", "srt", "vtt", "json"), help="Output format (default: txt)")
    parser.add_argument("-s", "--save", action="store_true", help="Save using an automatic filename in the current directory")
    parser.add_argument("-o", "--output", metavar="FILE", help="Save to an explicit output path (implies --save)")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    parser.add_argument("--list-languages", action="store_true", help="List available transcript languages and exit")
    parser.add_argument("--cookies-from-browser", metavar="BROWSER", help="Use cookies from a browser (for example: chrome, edge, or firefox)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress save/status messages")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    requested = list(args.languages or [])
    if args.language_positional:
        requested.insert(0, args.language_positional)
    if not requested:
        requested = ["en"]

    rumble = is_rumble_url(args.video)
    video_id = args.video if rumble else video_id_from(args.video)
    try:
        if rumble:
            fetched, selected_code = fetch_rumble_transcript(args.video, requested, args.cookies_from_browser)
            available_codes = [selected_code] if selected_code else []
        else:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcripts = YouTubeTranscriptApi().list(video_id)
            available = list(transcripts)
            available_codes = [transcript.language_code for transcript in available]
            if args.list_languages:
                if not available:
                    print("No transcripts are available.")
                    return 0
                for transcript in available:
                    kind = "generated" if transcript.is_generated else "manual"
                    print(f"{transcript.language_code}\t{transcript.language}\t{kind}")
                return 0
            selected = next((transcript for code in requested for transcript in available if transcript.language_code == code), None)
            if selected is None and available:
                selected = available[0]
                if not args.quiet:
                    print(f"Requested language(s) {', '.join(requested)} unavailable; using {selected.language_code}.", file=sys.stderr)
            if selected is None:
                fetched = []
            else:
                fetched = selected.fetch(preserve_formatting=True)
        if args.list_languages:
            for code in available_codes:
                print(code)
            return 0
    except Exception as exc:
        print(f"Error: could not access transcripts for {video_id}: {exc}", file=sys.stderr)
        return 1

    if not fetched:
        print(f"Error: no transcripts are available for {video_id}.", file=sys.stderr)
        return 1

    output_format = args.format or ("srt" if args.timestamps else "txt")
    content = render(fetched, output_format)
    if args.output or args.save:
        if args.output:
            target = Path(args.output)
        else:
            extension = "srt" if output_format == "srt" else output_format
            target = Path(f"yt-tr_{video_id}.{extension}")
        if target.exists() and not args.force:
            print(f"Error: {target} already exists; use --force to overwrite.", file=sys.stderr)
            return 1
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            print(f"Error: could not save {target}: {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"Saved transcript to {target.resolve()}", file=sys.stderr)
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

