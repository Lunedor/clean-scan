# 🧹 Clean-Scan: Pro Duplicate & Empty Folder Remover

**Clean-Scan** is a high-performance Python CLI tool designed for Windows power users. It helps you reclaim disk space by safely identifying identical files and cleaning up empty directory structures left behind.

## ✨ Key Features

* **⚡ Triple-Check Verification:** Uses a high-speed three-step process (File Size -> Fast 64KB Hash -> Full SHA-256) to ensure 100% accuracy.
* **📂 Long-Path Support:** Specifically engineered for Windows to bypass the 260-character path limit using UNC prefixes.
* **🎨 Color-Coded UI:** Visualizes file sizes in the terminal—Red for huge files (>100MB), Yellow for medium, and Green for small.
* **⛓️ Cascade Detection:** Automatically re-scans for empty folders that are created after duplicates are removed.
* **♻️ Safety First:** Moves files to the Windows Recycle Bin instead of permanent deletion using send2trash.
* **🔢 Smart Navigation:** Paginated review system with support for ranges (1-5), specific indices (1 3 7), and bidirectional navigation (Next/Back).
* **📊 Recovery Tracker:** Displays a live counter of exactly how much disk space has been reclaimed.

---

## 🚀 Installation

1. Clone the repository:
   git clone https://github.com/Lunedor/clean-scan.git

2. Install dependencies:
   pip install send2trash

---

## 🛠 Usage

You can run the script directly via Python or use the provided .bat file for quick access from the Windows CMD.

### Basic Command
python clean-scan.py [folder_path] [-r]

### Arguments
* folder_path: The directory you want to scan (defaults to current directory .).
* -r, --recursive: Scan all subfolders.

---

## 🎮 Navigation & Commands

Inside the Review Menu, you have granular control:

| Command | Action |
| :--- | :--- |
| 1 3 5-7 | Deletes the specified groups (keeps one original copy). |
| page | Deletes every duplicate group currently visible on your screen. |
| nuclear | Deletes every duplicate found in the entire scan (requires confirmation). |
| n | Move to the Next page. |
| b | Move to the Previous page. |
| q | Return to the main menu. |

---

## 🛡️ Logic & Accuracy

The script is designed to be "collision-proof":
1. Step 1: Groups files by exact byte size.
2. Step 2: Hashes only the first 64KB of files with matching sizes to filter out unique files quickly.
3. Step 3: Performs a full SHA-256 bit-by-bit hash only on files that passed the first two stages to confirm they are 100% identical.

---

## 📄 License
Distributed under the MIT License.
