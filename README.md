# BibleAPI

## Desktop startup and schema maintenance

`BIBLEAPI_LOCAL=1` and frozen desktop executables start without creating or
altering cloud database tables. The database schema must already be provisioned;
the hosted service retains its existing schema initialization on startup.

To initialize or update the schema explicitly, run `python app.py --init-db`
(or `bibleapi.exe --init-db` for the Windows binary) with the database settings
configured. This command runs schema maintenance and exits without starting HTTP
or the keep-alive thread. Use it during deployment, rather than every client launch.

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
