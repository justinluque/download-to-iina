# Download to IINA

<img src="extension/icon.svg" width="96" height="96" alt="Download to IINA icon">

Download video or audio into `~/Downloads`, follow its progress in Firefox,
then play the completed file in [IINA](https://iina.io).
Free and open source. No accounts, analytics, or telemetry.

[Install from Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/download-open-in-iina-yt-dlp/)

## Features

- One toolbar click starts the current video and opens a compact progress panel.
- Live download progress, transfer speed, size, and time remaining.
- Separate preparing, downloading, merging, opening, and completed states.
- A serial download queue. Add more links while a download is running.
- Cancel queued or active downloads; retry the latest failure in the panel.
- No download history. Finished and cancelled requests are removed immediately.
- Right-click a page, link, video, or audio item to add it directly.
- A toolbar percentage badge, light and dark themes, keyboard controls, and reduced-motion support.
- A vector icon with checked-in PNGs and three editable design explorations.

## Setup

You need macOS, Firefox, IINA, Python 3, and a current yt-dlp.
FFmpeg is recommended for merging separate video and audio streams. The helper
finds Homebrew FFmpeg even when Firefox starts from the Dock. Without FFmpeg,
it requests a combined audio/video stream, which may have lower quality.
With Homebrew:

```sh
brew install python yt-dlp ffmpeg
```

Firefox needs a local native messaging helper to run yt-dlp. The add-on alone
cannot download files:

```sh
git clone https://github.com/justinluque/download-to-iina.git
cd download-to-iina
bash native-host/install.sh
```

Install the Firefox add-on using the link above. The installer copies the
helper into Firefox's native messaging directory and records your Python
interpreter's absolute path, so Firefox launched from the Dock can find it.
You can move or remove the checkout afterward.

**Upgrading to 1.1:** rerun `bash native-host/install.sh` to install the new
progress/cancellation helper. Reload the add-on or restart Firefox after
updating the helper. Update the add-on as well; the published store version
may lag behind this source checkout.

## Use

1. Open a video page and click the toolbar icon. The download starts and the
   progress panel opens in the same click.
2. Close and reopen the panel at any time; the download continues in the background.
   Reopening the same active page does not start a duplicate download.
3. When download and merging finish, IINA opens the completed file.

The toolbar recognizes YouTube video routes, Vimeo video URLs, direct media
URLs, and pages containing video/audio elements or video metadata. On other
pages it only shows existing progress. Right-click media or a link to send any
HTTP/HTTPS URL to yt-dlp, including pages the toolbar does not recognize.

Downloads run one at a time, with up to 20 unfinished requests. Duplicate active
URLs are ignored. Completed and cancelled requests leave the panel immediately.
A short completion message disappears after three seconds; only the latest
unresolved error is kept for **Retry** or **Dismiss**. No download history is saved.

Progress is for the current media stream. Sites that download video and audio
separately may start a second progress pass before merging. When size is unknown,
the bar shows ongoing activity instead of an invented percentage. Preparing and
merging may also take time without a percentage.

Cancellation stops yt-dlp and its child processes. Partial files are kept so a
retry may resume them; finished files are never deleted by this extension.
Closing Firefox stops active work and clears the queue.
Playlists are disabled: a video page downloads the selected item.

## Build and test

Requires Python 3 and Node.js, with no dependency installation for normal builds:

```sh
make test
make build
```

Or run the commands directly:

```sh
python3 -m unittest discover -s tests
node --test tests/*.test.cjs
python3 scripts/package.py
```

The build creates a deterministic, **unsigned** XPI in `dist/`. For temporary
Firefox testing, open `about:debugging#/runtime/this-firefox`, choose
**Load Temporary Add-on…**, and select `extension/manifest.json` or the XPI.
Disable any other copy first. Temporary add-ons disappear on Firefox restart.
Permanent installation in standard Firefox requires Mozilla signing.

Tests cover native message framing, URL validation, live progress, queue
ordering, duplicate requests, cancellation, helper disconnects, retries,
output validation, IINA failures, installer portability, and subprocess cleanup.
Popup tests cover one-click initiation, duplicate protection on reopening,
media-page detection, error recovery, and immediate removal of finished requests.
Streaming tests use real child processes and fixture media; they do not
contact media websites or launch IINA.

The selected vector source is `extension/icon.svg`. Alternatives live in
`assets/icon-options/`. Install `librsvg` and run `make icons` to regenerate
PNGs after editing the vector. No image generation service is used.

## Troubleshooting

- **Helper disconnected / nothing starts:** rerun the helper installer from
  this source folder, reload the add-on, then retry. The panel displays the
  connection error and setup guidance.
- **yt-dlp not found:** install or update yt-dlp. The helper searches PATH,
  `/opt/homebrew/bin`, `/usr/local/bin`, and common user Python locations.
  Custom locations can be added to `CANDIDATE_YTDLP_PATHS` in the helper.
- **A site stops working:** update yt-dlp (`brew upgrade yt-dlp`, or the method
  you used to install it). Site support depends on yt-dlp's extractors.
- **Merging fails:** install FFmpeg. Error details are shown in the panel.
- **Downloaded, but IINA did not open:** check IINA is installed; the error
  includes the saved file's location so you can open it manually.
- **No percentage:** some sites do not report a total size. The activity bar
  still shows that the request is running. Individual jobs time out after one hour.

Only HTTP and HTTPS URLs are accepted. The helper uses predictable download
options and ignores user yt-dlp configuration files. It does not pass Firefox
cookies, login sessions, or credentials to yt-dlp. Protected or login-only media
may not work.

## Privacy

The extension sends the selected URL and an opaque request ID to a local helper.
yt-dlp contacts the media site to download it. Files stay in `~/Downloads`.
Only unfinished requests and the latest unresolved error are held in memory.
There is no download history. See [PRIVACY.md](PRIVACY.md).

## Uninstall

Remove the add-on in Firefox, then delete
`~/Library/Application Support/Mozilla/NativeMessagingHosts/io.iina.ytdlp_host.json`
and the adjacent `io.iina.ytdlp_host` directory. Downloaded media is kept.

## Attribution and license

This project grew out of the “Open In IINA” extension and changes the workflow
to download first, then play locally. It is an independent extension; IINA and
yt-dlp are separate projects. The current play/download vector icon was created
for this extension. Existing repository history and licensing are retained.

[GNU AGPL v3.0 only](LICENSE), matching the Firefox Add-ons listing.
