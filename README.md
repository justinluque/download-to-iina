# Download & Open in IINA (yt-dlp)

Fork of the "Open In IINA" Firefox extension that, instead of streaming the
URL directly to IINA, downloads it with `yt-dlp` into `~/Downloads` first and
then opens the downloaded file in IINA.

Browser extensions can't shell out to a local binary on their own, so this
needs a small **native messaging host** — a Python script Firefox launches
and talks to over stdin/stdout — that runs `yt-dlp` and then `open -a IINA`.

## Requirements

- `yt-dlp` installed (`brew install yt-dlp`)
- IINA installed
- Firefox
- Python 3 (ships with macOS / usually already present)

## Install

1. Run the installer, which registers the native messaging host:

   ```bash
   ./native-host/install.sh
   ```

   This writes
   `~/Library/Application Support/Mozilla/NativeMessagingHosts/io.iina.ytdlp_host.json`
   pointing at `native-host/iina_ytdlp_host.py`.

2. Load the extension in Firefox:
   - Go to `about:debugging#/runtime/this-firefox`
   - Click **Load Temporary Add-on…**
   - Select `extension/manifest.json`

   (Temporary add-ons are removed when Firefox restarts — reload it each
   session, or self-sign it via `web-ext sign` / AMO for a permanent install.)

3. Click the toolbar icon on a page, or right-click a video/audio/link and
   choose "Download this ... (yt-dlp) & open in IINA". The toolbar badge
   shows `…` while downloading, `✓` when IINA has opened the file, or `!` on
   error (check the background page console via `about:debugging` → Inspect
   for the error message).

## Notes / gotchas

- **PATH**: Firefox launched from Finder/Dock doesn't inherit your shell's
  PATH, so `yt-dlp` on PATH in Terminal may not be visible to the native
  host. `iina_ytdlp_host.py` falls back to common locations
  (`/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`) — edit
  `CANDIDATE_YTDLP_PATHS` in that file if yours lives elsewhere.
- Downloads use yt-dlp's own extractors, so this works on any site yt-dlp
  supports (not just direct media URLs) — the extension sends whatever URL
  you clicked (page/link/video/audio) straight to yt-dlp.
- The whole download runs before IINA opens anything — for long videos
  there's no "start playback immediately" streaming behavior anymore, by
  design.
- Uninstall: remove the native host manifest at
  `~/Library/Application Support/Mozilla/NativeMessagingHosts/io.iina.ytdlp_host.json`
  and remove the temporary add-on in `about:debugging`.
