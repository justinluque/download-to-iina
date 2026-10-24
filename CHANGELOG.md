# Changelog

## 1.2.2 — 2026-10-24

- Move the GitHub repository to justinluque/download-to-iina.
- Update the extension homepage, help link, and setup instructions.
- Remove the unused original raster icon source.

## 1.2.1 — 2026-10-24

- Rename the extension to Download to IINA.

## 1.2.0 — 2026-10-24

- Start downloading recognized media pages when the toolbar panel opens.
- Reopening the same active URL shows progress without starting a duplicate.
- Replace the large popup with a compact, flat progress panel.
- Remove download history and saved paths; finished/cancelled requests are discarded.
- Keep only a brief completion notice or one actionable error with Retry/Dismiss.
- Preserve live progress, cancellation, queueing, light/dark themes, and keyboard focus.
- Existing 1.1.1 native helpers work unchanged.

## 1.1.1 — 2026-10-24

- Find Homebrew FFmpeg even when Firefox starts without the shell PATH.
- Fall back to combined audio/video media when FFmpeg is unavailable.
- Show explicit upgrade guidance when an older native helper cannot report progress.

## 1.1.0 — 2026-10-24

- Add a toolbar popup with live per-stream progress, speed, size, and ETA.
- Add a serial queue, duplicate protection, cancellation, retries, and session history.
- Show preparation, merging, IINA handoff, errors, and helper setup guidance.
- Stream native progress with request IDs; stop downloader subprocesses on cancellation or disconnect.
- Download one selected item per request, ignore custom yt-dlp configs, and include media IDs in filenames.
- Add the SVG play/download icon, PNG exports, and three vector design options.
- Support light/dark themes, keyboard focus, and reduced motion; remove the broad tabs permission.
- Extend regression coverage and add build/icon commands.
- Requires reinstalling the native helper as well as updating the add-on.

## 1.0.1

- New download/play icon, including properly sized toolbar assets.
- Link to the public source from the extension manifest.
- Install a self-contained helper with an explicit Python interpreter path.
- Reject unsupported URLs and malformed native messages.
- Add setup documentation, privacy notes, license, and reproducible packaging.

## 1.0.0

- Initial Firefox release: download with yt-dlp, then open in IINA.
