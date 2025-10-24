# Local HTTP Endpoints

`tidal-dl` exposes a couple of local HTTP endpoints when specific features are enabled. By default they listen on `127.0.0.1:8123`, but you can change the port from the interactive settings menu (option `6` → *Listener port*). The same configured port is reused for both PKCE logins and listener-mode downloads.

## `/pkce`

* **Available during:** PKCE login flow (menu option `8`). The temporary server starts automatically when you begin a PKCE login and shuts down once a redirect is received or you cancel the flow.
* **Purpose:** Accepts the redirected URL payload from the browser extension/automation so the CLI can finish the OAuth exchange without manual copy/paste.
* **Authentication:** None. The endpoint is only reachable from `127.0.0.1` while the PKCE login prompt is active.
* **Request:** `POST http://127.0.0.1:<port>/pkce`
  * Content-Type: `application/json`
  * Body fields:
    * `normalizedUri` (string, optional) – full redirect URL. If provided, other fields are ignored.
    * `pkceUri` (string, optional) – alternative name for the full redirect URL.
    * `scheme` (string, optional) – URI scheme (e.g. `https`).
    * `path` (string, optional) – URI host/path segment (e.g. `tidal.com/browse`).
    * `params` (object, optional) – key/value query parameters to append when `scheme` and `path` are supplied separately.
  * The CLI accepts whichever combination it can turn into a usable redirect URL.
* **Response:** `{ "status": "received" }` when accepted. The server immediately completes the login and shuts down.

## `/run` and `/run_sync`

* **Available during:** Listener mode (start with `tidal-dl --listen`).
* **Purpose:** Trigger downloads remotely via HTTP instead of the interactive CLI.
* **Authentication:** Requires the `X-Auth` request header to match the *Listener secret* configured in settings.
* **Request:**
  * Endpoint: `POST http://127.0.0.1:<port>/run` for asynchronous downloads, or `/run_sync` to wait for completion.
  * Headers:
    * `Content-Type: application/json`
    * `X-Auth: <your-shared-secret>`
    * Optional: `Authorization: Bearer <token>` if you want to reuse an existing TIDAL bearer token for that request.
  * Body fields:
    * `url` (string, required) – TIDAL track URL.
    * `bearerAuthorization` or `bearer_token` (string, optional) – alternative way to pass a bearer token instead of the header.
* **Responses:**
  * `/run` – `{ "status": "started" }` once the download attempt is queued in the background.
  * `/run_sync` – `{ "status": "finished", "final_code": <0|1>, "codec": "<STREAM CODEC>", "title": "<TRACK TITLE>" }` after the attempt (including the HiFi retry) completes.

Log output for listener-mode requests is appended to `~/tidal-dl-listener.txt` in the home directory.
