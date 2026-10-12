# Download & Open in IINA (yt-dlp)

<img src="extension/icon128.png" width="96" height="96" alt="Download & Open in IINA icon">

A small Firefox extension for macOS. Click the toolbar button or right-click a
page, link, video, or audio URL to download it with yt-dlp into `~/Downloads`,
then open the downloaded file in IINA.

[Install from Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/download-open-in-iina-yt-dlp/)

This is a casual source release. It grew out of the “Open In IINA” extension;
this version downloads first instead of streaming. Issues and small fixes are welcome.

## Setup

You'll need Firefox, [IINA](https://iina.io), Python 3, and yt-dlp.
If you use Homebrew:

```sh
brew install python yt-dlp ffmpeg
```

Firefox needs a local native messaging helper to run yt-dlp. Installing the
Firefox add-on alone isn't enough:

```sh
git clone https://github.com/justinluque/iina-ytdlp-extension.git
cd iina-ytdlp-extension
bash native-host/install.sh
```

The installer copies the helper into Firefox's native messaging directory and
records your Python interpreter's absolute path, so Firefox launched from the
Dock can find it. You can move or remove the checkout afterward. Run the
installer again after updating the helper or moving your Python installation.

Install the add-on from the Firefox link above, then click its toolbar button
on a media page, or choose **Download this … (yt-dlp) & open in IINA** from the
right-click menu. The badge shows `…` while downloading, `✓` on success, and
`!` on an error. Downloads finish before playback starts.

## Development / packaging

For local testing, visit `about:debugging#/runtime/this-firefox`, choose
**Load Temporary Add-on…**, and select `extension/manifest.json`.
Temporary add-ons disappear when Firefox restarts.

```sh
python3 -m unittest discover -s tests
python3 scripts/package.py
```

The packaging command creates an unsigned XPI in `dist/`. Submit it to Mozilla
for signing before distributing it as a permanent Firefox installation.
The GitHub source may be newer than the signed version on Firefox Add-ons.

## Troubleshooting

- **Nothing happens / `!` badge:** check that the helper is installed and
  IINA is available. Inspect the extension console through `about:debugging`
  for details.
- **yt-dlp missing:** the helper searches PATH, `/opt/homebrew/bin`,
  `/usr/local/bin`, and common user Python locations. For a custom install,
  edit `CANDIDATE_YTDLP_PATHS` in the helper and rerun the installer.
- **A site stops working:** update yt-dlp (`brew upgrade yt-dlp`). This uses
  yt-dlp's extractors and does not guarantee support for every media URL.
- Only HTTP and HTTPS URLs are accepted. It does not pass Firefox cookies or
  login sessions to yt-dlp. Playlists follow yt-dlp's defaults; the helper
  opens the last reported file.

## Privacy

No analytics or telemetry. The extension sends the URL you select to the local
helper, and yt-dlp contacts the media site to download it. Files stay in
`~/Downloads`. See [PRIVACY.md](PRIVACY.md).

## Uninstall

Remove the add-on in Firefox, then delete
`~/Library/Application Support/Mozilla/NativeMessagingHosts/io.iina.ytdlp_host.json`
and the adjacent `io.iina.ytdlp_host` directory. Downloaded media is kept.

## License

[GNU AGPL v3.0 only](LICENSE), matching the license on the Firefox Add-ons listing.
