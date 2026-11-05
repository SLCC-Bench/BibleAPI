# BibleAPI

## Desktop startup and schema maintenance

`BIBLEAPI_LOCAL=1` and frozen desktop executables start without creating or
altering cloud database tables. The database schema must already be provisioned;
the hosted service retains its existing schema initialization on startup.

To initialize or update the schema explicitly, run `python app.py --init-db`
(or `bibleapi.exe --init-db` for the Windows binary) with the database settings
configured. This command runs schema maintenance and exits without starting HTTP
or the keep-alive thread. Use it during deployment, rather than every client launch.

## Local administrator access

Desktop/local mode binds only to `127.0.0.1`. Open `/login` on the app's active
local API port to sign in and reach `/static/admin.html`. The supplied username
is stored as a SHA-256 digest and the password as a salted PBKDF2-SHA256 hash
in `admin_credentials.json`; neither plaintext credential is shipped.
Admin sessions expire after five minutes of inactivity and are reset on API restart.
State-changing browser requests require CSRF tokens. Login is limited to five
attempts per minute; logout clears the browser session.

Praisehub generates a random app token each launch and passes it only to its
child API and trusted app requests from Electron's main process. It is not
saved to disk or exposed through preload/IPC. It permits Bible reads, song
sync, registration checking/redemption, readiness, and local events; it does
not grant admin controls, code listing, or user management. All other direct
API requests require the administrator session. Hosted-mode auth is unchanged.

`local_security.py` and the hash-only JSON must be included in desktop builds.
Keep the credential text file outside source control. A user controlling the OS
account can inspect or modify local processes and binaries; these controls do
not make a client-side application tamper-proof or replace database least privilege.

## Hardware-bound registration migration

Before deploying hardware-aware clients, run the explicit `--init-db` command.
Alternatively, apply `migrations/2026-11-05-hardware-registration.sql` once for
only the new column/index, without the other schema-initialization operations.
It adds nullable `RegistrationCodes.hardware_device_id` and its unique index;
existing `device_id` values and registration codes/expiry dates are preserved.
Desktop startup still never maintains the schema. A hardware-aware request against
an unmigrated database returns HTTP 503 with migration instructions, while
legacy-only requests keep working. Rollback can retain this additive nullable
column and index; do not drop device bindings or reset used codes.

Clients send an application-scoped SHA-256 hardware fingerprint as `hardware_id`,
never a physical UUID or serial. The API stores a domain-separated HMAC-SHA256 of
that fingerprint. Keep `HMAC_SECRET` stable across deployments and desktop builds.
An active existing registration is linked only when its legacy `device_id` matches.
After that link, the same hardware can restore registration after an OS reformat
without changing its original key, expiry, or legacy device binding. Redeeming a
previously used key still requires that same device/hardware binding.

Upgrade existing installations before reformatting so their hardware can be
linked. Old MachineGuid-only hashes cannot reveal a device's physical identity
after reformatting. macOS clients also preserve their legacy device identity while
linking the new hashed hardware identity, so updating an existing installation
does not lose its registration. Never auto-transfer
a used key solely because someone knows the key; unrecognized hardware requires
an administrator-approved recovery process.

New activations preserve the original readable `registration_code` in the database;
only device identities are hashed. Historical bcrypt-hashed registration codes
remain verifiable when the owner re-enters their original key on the bound device.
They cannot be decrypted or automatically converted back to readable codes.

## Allowing a registered device to enter another code

Apply `migrations/2026-11-05-registration-replacement.sql` once (or run the
explicit `--init-db` deployment command). In the admin Registration Codes tab,
choose **Allow another code** on the device's current used code. The open
Registration tab updates through a local Server-Sent Events connection;
**Cancel code change** hides the field again. No periodic registration queries
are made. Keep-alives do not access the database, and reconnecting reconciles
the current permission. Closing the tab closes the connection. Offline devices
keep the entry field hidden.

Events are loopback-only and process-local: changes must go through this same
local BibleAPI instance. Changes from another API process, a hosted admin, or
direct SQL are not broadcast. The stream carries no codes or device identities.

The API enforces this permission even for direct redemption requests. Only a
valid, unused new key replaces an active registration. A failed attempt leaves
the current license intact. Successful replacement moves the hashed device and
hardware bindings to the new key and consumes permission; the old key remains
used. Re-entering the original key still preserves its expiry as before.

## Fetching the updated Bible from the server

To fetch the latest Bible data from the running server:

1. Open VS Code terminal.
2. Run the following command to download the Bible translations list:
   ```
   curl https://bibleapi-uswk.onrender.com/api/translations -o translations.json
   ```
   Or to fetch all verses for a translation (replace `TranslationName` with the actual name):
   ```
   curl "https://bibleapi-uswk.onrender.com/api/verses/TranslationName" -o verses.json
   ```

3. If you want to update your local SQLite3 file (`db/bible.sqlite3`), check if the server provides a direct download endpoint for the database file. For example:
   ```
   curl https://bibleapi-uswk.onrender.com/static/db/bible.sqlite3 -o db/bible.sqlite3
   ```
   If you get a `404 Not Found` error, the endpoint does not exist or is not publicly accessible.  
   In this case, use the admin upload/download feature (if available) or contact the server admin to obtain the latest database file.

4. To update your GitHub repository or local development:
   - Replace your local `db/bible.sqlite3` file with the downloaded one.
   - Commit and push the changes if you want to update the file in GitHub:
     ```
     git add db/bible.sqlite3
     git commit -m "Update Bible database from server"
     git push
     ```

If you need to automate this in Python or another language, ask for a script.

### Downloading `bible.sqlite3` from Render.com server hosting

To download `db/bible.sqlite3` directly from a Render.com server, the server must expose a public endpoint for the file (e.g., `/static/db/bible.sqlite3`). If this endpoint does not exist or returns a 404 error, you cannot download the file directly.

**Options:**
- **Public Endpoint:**  
  If available, use:
  ```
  curl https://bibleapi-uswk.onrender.com/static/db/bible.sqlite3 -o db/bible.sqlite3
  ```
- **Admin Panel:**  
  Check if the admin panel provides a download feature for the database.
- **Server Access:**  
  If you have SSH or SFTP access to the server, you can manually copy the file.
- **Contact Admin:**  
  Ask the server administrator to provide the latest `db/bible.sqlite3` file.

**Note:**  
Render.com does not provide direct file access to deployed servers unless you set up a public endpoint or use their shell access (if available).
