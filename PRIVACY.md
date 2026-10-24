# Privacy

Download to IINA does not collect analytics or telemetry, create an
account, or send information to the developer.

When you start a download, the extension sends the selected HTTP/HTTPS URL
and a request ID to the native helper installed on your Mac. The helper runs
yt-dlp, which contacts the selected media site and any services needed to
retrieve that media. These requests are subject to those services' policies.
Firefox cookies and login sessions are not forwarded.

The helper reports download title, progress, error details, and completion to
the extension. Only active/queued requests and the latest unresolved error are
held in memory. Completed and cancelled requests are removed immediately; a
brief completion message clears after three seconds. There is no download
history, remote logging, or extension storage of these details.

Files are saved in `~/Downloads`. Cancelled downloads may leave partial files
there for resuming. Removing the extension does not delete media files.

Permissions: `activeTab` reads the current page's URL and title after you
invoke the toolbar panel and checks whether the page contains media elements
or video metadata; `contextMenus` adds download menu items;
`nativeMessaging` communicates with the local helper.
