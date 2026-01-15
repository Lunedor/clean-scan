#! python
import os
import hashlib
import argparse
from collections import defaultdict
from send2trash import send2trash

# Color codes for Windows CMD
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Global tracker for space saved
SPACE_SAVED_BYTES = 0

def fix_path(path):
    """Bypasses Windows 260 character limit."""
    abs_path = os.path.abspath(path)
    if abs_path.startswith("\\\\?\\"): return abs_path
    return "\\\\?\\" + abs_path

def get_hash(path, fast=False, buf_size=65536):
    h = hashlib.sha256()
    try:
        with open(fix_path(path), "rb") as f:
            if fast: h.update(f.read(buf_size))
            else:
                while True:
                    data = f.read(buf_size)
                    if not data: break
                    h.update(data)
        return h.hexdigest()
    except: return None

def get_color_for_size(mb):
    if mb > 100: return RED
    if mb > 10: return YELLOW
    return GREEN

def find_duplicates(root, recursive):
    size_map = defaultdict(list)
    print(f"{CYAN}🔍 Scanning for duplicates...{RESET}")
    
    def files_iter():
        if recursive:
            for d, _, files in os.walk(root):
                for f in files: yield os.path.join(d, f)
        else:
            for f in os.listdir(root):
                p = os.path.join(root, f)
                if os.path.isfile(p): yield p

    for path in files_iter():
        try: size_map[os.path.getsize(fix_path(path))].append(path)
        except: continue

    potential = []
    for files in size_map.values():
        if len(files) < 2: continue
        fast_map = defaultdict(list)
        for f in files:
            h = get_hash(f, fast=True)
            if h: fast_map[h].append(f)
        for g in fast_map.values():
            if len(g) > 1: potential.append(g)

    final = []
    for group in potential:
        full_map = defaultdict(list)
        for f in group:
            h = get_hash(f, fast=False)
            if h: full_map[h].append(f)
        for g in full_map.values():
            if len(g) > 1: final.append(g)
            
    # Sort by total wasted space
    final.sort(key=lambda x: os.path.getsize(fix_path(x[0])) * (len(x)-1), reverse=True)
    return final

def find_empty_folders(root, recursive):
    empty = []
    for d, subdirs, files in os.walk(root, topdown=False):
        if not subdirs and not files: empty.append(d)
        if not recursive: break
    return empty

def parse_selection(selection, max_val):
    result = set()
    for part in selection.replace(",", " ").split():
        if "-" in part:
            try:
                s, e = map(int, part.split("-"))
                result.update(range(s, e + 1))
            except: continue
        elif part.isdigit(): result.add(int(part))
    return [n for n in result if 1 <= n <= max_val]

def perform_deletion(groups):
    global SPACE_SAVED_BYTES
    count = 0
    for group in groups:
        try:
            f_size = os.path.getsize(fix_path(group[0]))
            for f in group[1:]:
                try:
                    send2trash(fix_path(f))
                    print(f"  {RED}🗑️ Trashed:{RESET} {f}")
                    count += 1
                    SPACE_SAVED_BYTES += f_size
                except Exception as e: print(f"  ❌ Error: {e}")
        except: continue
    return count

def review_menu(items):
    curr = 0
    page_size = 10
    while curr < len(items):
        end = min(curr + page_size, len(items))
        print(f"\n{BOLD}{CYAN}=== REVIEWING DUPLICATES {curr+1}-{end} (Total: {len(items)}) ==={RESET}")
        
        for i in range(curr, end):
            group = items[i]
            try:
                size_mb = os.path.getsize(fix_path(group[0])) / (1024*1024)
                color = get_color_for_size(size_mb)
                print(f"\n{BOLD}[{i+1}] {len(group)} COPIES - {color}{size_mb:.2f} MB each{RESET}")
                for path in group: print(f"    -> {path}")
            except: print(f"[{i+1}] Inaccessible")

        print(f"\n{BOLD}COMMAND OPTIONS:{RESET}")
        print(f"  {YELLOW}1 3 5-7{RESET}  -> Delete specific groups")
        print(f"  {YELLOW}page{RESET}     -> Delete this page")
        print(f"  {YELLOW}nuclear{RESET}  -> Delete ALL duplicates in entire scan")
        print(f"  {YELLOW}n{RESET}        -> Next Page")
        print(f"  {YELLOW}p{RESET}        -> Previous Page")
        print(f"  {YELLOW}q{RESET}        -> Back to Main Menu")
        
        cmd = input("\nSelection > ").strip().lower()
        if cmd == 'q': break
        if cmd == 'n': 
            if curr + page_size < len(items): curr += page_size
            else: print(f"{YELLOW}You are on the last page.{RESET}")
            continue
        if cmd == 'p':
            curr = max(0, curr - page_size)
            continue
        
        selected, indices = [], []
        if cmd == 'nuclear':
            confirm = input(f"{RED}⚠️  WARNING: Delete ALL duplicates? (y/n): {RESET}")
            if confirm.lower() == 'y':
                perform_deletion(items)
                items.clear()
                break
        elif cmd == 'page':
            indices = list(range(curr + 1, end + 1))
            selected = items[curr:end]
            perform_deletion(selected)
            for i in sorted(indices, reverse=True): items.pop(i-1)
        else:
            indices = parse_selection(cmd, len(items))
            if indices:
                selected = [items[idx-1] for idx in indices]
                perform_deletion(selected)
                for i in sorted(indices, reverse=True): items.pop(i-1)

def review_empties(items):
    curr = 0
    page_size = 10
    while curr < len(items):
        end = min(curr + page_size, len(items))
        print(f"\n{CYAN}--- EMPTY FOLDERS {curr+1}-{end} ---{RESET}")
        for i in range(curr, end): print(f"[{i+1}] {items[i]}")
        
        print(f"\n{BOLD}COMMANDS:{RESET} [indices], [page], [nuclear], [n] Next, [p] Previous, [q] Back")
        cmd = input("Selection > ").strip().lower()
        
        if cmd == 'q': break
        if cmd == 'n': 
            if curr + page_size < len(items): curr += page_size
            continue
        if cmd == 'p':
            curr = max(0, curr - page_size)
            continue
        
        selected, indices = [], []
        if cmd == 'nuclear':
            selected, indices = items, list(range(1, len(items) + 1))
        elif cmd == 'page':
            selected, indices = items[curr:end], list(range(curr + 1, end + 1))
        else:
            indices = parse_selection(cmd, len(items))
            selected = [items[i-1] for i in indices]
            
        if selected:
            for d in selected:
                try: send2trash(fix_path(d)); print(f"  🗑️ Removed: {d}")
                except: pass
            for i in sorted(indices, reverse=True): items.pop(i-1)
    return items

def main():
    os.system('') # Enable colors
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", default=".")
    parser.add_argument("-r", "--recursive", action="store_true")
    args = parser.parse_args()

    root = os.path.abspath(args.folder)
    dups = find_duplicates(root, args.recursive)
    empties = find_empty_folders(root, args.recursive)

    while True:
        saved_mb = SPACE_SAVED_BYTES / (1024*1024)
        print(f"\n{BOLD}{CYAN}===== DUPLICATE SCANNER: {root} ====={RESET}")
        print(f"Duplicates: {YELLOW}{len(dups)}{RESET} | Empty Folders: {YELLOW}{len(empties)}{RESET}")
        print(f"Total Space Recovered: {GREEN}{saved_mb:.2f} MB{RESET}")
        print("-" * 40)
        print("1) Review Duplicates (Largest First)")
        print("2) Review Empty Folders")
        print("3) Refresh Scan")
        print("4) Exit")
        
        choice = input("> ").strip()
        if choice == "1":
            review_menu(dups)
            empties = find_empty_folders(root, args.recursive)
        elif choice == "2":
            empties = review_empties(empties)
        elif choice == "3":
            dups = find_duplicates(root, args.recursive)
            empties = find_empty_folders(root, args.recursive)
        elif choice == "4": 
            print(f"\n{BOLD}{GREEN}Final Space Recovered: {saved_mb:.2f} MB. Goodbye!{RESET}")
            break

if __name__ == "__main__":

    main()
