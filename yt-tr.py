#!/usr/bin/env python3
"""Fetch YouTube transcripts with friendly CLI output and file formats."""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-tr",
        description="Fetch a YouTube transcript from a video ID or full URL.",
    )
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument("language_positional", nargs="?", metavar="language", help="Preferred language code")
    parser.add_argument("-l", "--language", dest="languages", action="append", help="Preferred language code; repeatable")
    parser.add_argument("-t", "--timestamps", action="store_true", help="Include timestamps in SRT format")
    parser.add_argument("--format", choices=("txt", "srt", "vtt", "json"), help="Output format (default: txt)")
    parser.add_argument("-s", "--save", action="store_true", help="Save using an automatic filename in the current directory")
    parser.add_argument("-o", "--output", metavar="FILE", help="Save to an explicit output path (implies --save)")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    parser.add_argument("--list-languages", action="store_true", help="List available transcript languages and exit")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress save/status messages")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    video_id = video_id_from(args.video)
    requested = list(args.languages or [])
    if args.language_positional:
        requested.insert(0, args.language_positional)
    if not requested:
        requested = ["en"]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcripts = YouTubeTranscriptApi().list(video_id)
    except Exception as exc:
        print(f"Error: could not access transcripts for {video_id}: {exc}", file=sys.stderr)
        return 1

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

    selected = None
    for code in requested:
        selected = next((transcript for transcript in available if transcript.language_code == code), None)
        if selected:
            break
    if selected is None and available:
        selected = available[0]
        if not args.quiet:
            print(f"Requested language(s) {', '.join(requested)} unavailable; using {selected.language_code}.", file=sys.stderr)
    if selected is None:
        print(f"Error: no transcripts are available for {video_id}.", file=sys.stderr)
        return 1

    try:
        fetched = selected.fetch(preserve_formatting=True)
    except Exception as exc:
        print(f"Error: could not fetch the {selected.language_code} transcript: {exc}", file=sys.stderr)
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
