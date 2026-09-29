# Installing Kruti Finder

Download the installer for your computer from the project's GitHub **Releases** page, or from the latest successful **Actions** run (Artifacts section).

| Computer | File | Requirements |
|---|---|---|
| Windows 10 / 11 (64-bit) | `KrutiFinder-Setup-x.y.z.exe` | No admin rights needed |
| Mac with Apple chip (M1–M4) | `KrutiFinder-x.y.z-mac-apple-silicon.dmg` | macOS 14 Sonoma or newer |
| Ubuntu 22.04+ / Linux Mint 21+ / Debian 12+ | `kruti-finder_x.y.z_amd64.deb` | Internet during install (for OCR package) |

OCR for Hindi, Gujarati and Sanskrit is included. Nothing else needs to be installed.

The app is **not code-signed** (internal use), so each system shows a one-time warning. This is expected.

## Windows

1. Double-click `KrutiFinder-Setup-x.y.z.exe`.
2. If Windows shows **"Windows protected your PC"**, click **More info** → **Run anyway**.
3. Follow the installer. It installs for your user only; no administrator password is needed.
4. Start **Kruti Finder** from the Start menu or the desktop shortcut.

## Mac (Apple chip)

1. Open the `.dmg` and drag **Kruti Finder** onto **Applications**.
2. The first time only, open **Applications**, **right-click** Kruti Finder → **Open** → **Open**.

   If macOS says the app "is damaged" or "can't be opened", run this once in Terminal:

   ```bash
   xattr -dr com.apple.quarantine "/Applications/Kruti Finder.app"
   ```

   Then open it normally.

## Ubuntu / Linux Mint / Debian

In a terminal, run:

```bash
sudo apt install ./kruti-finder_x.y.z_amd64.deb
```

This also installs the OCR engine automatically. Start **Kruti Finder** from the applications menu, or run `kruti-finder`.

Double-clicking the `.deb` in *Software Manager* (Mint) or *App Center* (Ubuntu) also works.

To uninstall: `sudo apt remove kruti-finder`

## Using the app

1. **Kruti Excel:** choose the team's `.xlsx` file.
2. **PDF books:**
   - **Add PDF files…** picks one or many PDFs.
   - **Add folder…** takes every PDF inside the folder and its sub-folders.
   - You can also drag files or folders onto the list.
3. **Save results to:** choose a folder. Each run creates its own sub-folder, named with the date and time.
4. Click **Start**.
   - Two progress bars show all books and the current book.
   - The panel also shows elapsed time, time left, pages OCR'd, and Kruti found.
   - **Pause** / **Resume** at any time.
   - **Cancel** stops after the current page. Everything read so far is saved, so the next Start continues quickly instead of starting over. The same applies if the computer restarts or the app is closed.
5. When done, click **Open Missing Kruti file**.
6. After the team reviews it (Approve = Y), use the **Merge Reviewed File** tab to create the new master Excel.

**Tips**

- Scanned books are slow to read, about 2–6 seconds per page. A 200-book run can take many hours; leave it running overnight.
- **Advanced settings** → *Parallel OCR jobs*: use 2 on 8 GB RAM laptops, 4–6 on 16 GB+ desktops.
- Saved page text lives in the app's data folder. *Advanced settings → Clear saved OCR results* frees that space.
