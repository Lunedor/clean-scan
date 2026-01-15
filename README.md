# 🧹 Clean-Scan: Pro Duplicate & Empty Folder Remover

**Clean-Scan** is a high-performance Python CLI tool designed for Windows power users. It helps you reclaim disk space by safely identifying identical files and cleaning up empty directory structures.

## ✨ Key Features

* **⚡ Triple-Check Verification:** Uses a high-speed three-step process (File Size -> Fast 64KB Hash -> Full SHA-256) for 100% accuracy.
* **📂 Long-Path Support:** Engineered to bypass the Windows 260-character path limit.
* **🎨 Color-Coded UI:** Visualizes file sizes (Red >100MB, Yellow >10MB, Green <10MB).
* **⛓️ Cascade Detection:** Automatically re-scans for empty folders created after file deletion.
* **🔢 Smart Navigation:** Paginated review (Page X of Y) with Next/Back (`n`/`p`) support.
* **📊 Recovery Tracker:** Displays a live counter of exactly how much disk space has been reclaimed.
* **🚀 Full Auto Clean:** A "Nuclear" option to trash all duplicates and recursively remove all empty folders in one click.

---

## 🚀 Installation & Usage

1. **Install dependencies:**
   `pip install send2trash`

2. **Run the script:**
   `python clean-scan.py [folder_path] [-r]`

---

## 🎮 Commands

| Command | Action |
| :--- | :--- |
| `1 3 5-7` | Deletes specific groups (keeps one original). |
| `page` | Deletes every duplicate group on the current page. |
| `nuclear` | Deletes every duplicate in the entire scan. |
| `n` / `p` | Move to **Next** or **Previous** page. |
| `q` | Return to the main menu. |

---

## 🛡️ Logic


1. **Size Grouping:** Filters by exact byte size.
2. **Fast Hash:** Hashes the first 64KB of potential matches.
3. **Full Hash:** Bit-by-bit SHA-256 verification for final confirmation.

---

## 📄 License
Distributed under the MIT License.
