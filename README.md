# BibleAPI

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