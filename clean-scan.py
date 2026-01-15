#! python
import os
import hashlib
import argparse
import math
from collections import defaultdict
from send2trash import send2trash

# Color codes for Windows CMD
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

SPACE_SAVED_BYTES = 0

def fix_path(path):
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
    final.sort(key=lambda x: os.path.getsize(fix_path(x[0])) * (len(x)-1), reverse=True)
    return final

def find_empty_folders(root, recursive):
    empty = []
    if not os.path.isdir(root): return []
    if not recursive:
        try:
            if not os.listdir(root): empty.append(root)
        except: pass
        return empty

    for d, subdirs, files in os.walk(root, topdown=False):
        if d == root: continue 
        try:
            if not os.listdir(fix_path(d)): empty.append(d)
        except: pass
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
                except: pass
        except: continue
    return count

def review_menu(items, root, recursive):
    curr = 0
    page_size = 10
    while curr < len(items):
        total_pages = math.ceil(len(items) / page_size)
        current_page = (curr // page_size) + 1
        end = min(curr + page_size, len(items))
        
        print(f"\n{BOLD}{CYAN}=== REVIEW DUPLICATES (Page {current_page} of {total_pages}) ==={RESET}")
        for i in range(curr, end):
            group = items[i]
            try:
                size_mb = os.path.getsize(fix_path(group[0])) / (1024*1024)
                print(f"[{i+1}] {len(group)} COPIES - {get_color_for_size(size_mb)}{size_mb:.2f} MB each{RESET}")
                for path in group: print(f"    -> {path}")
            except: print(f"[{i+1}] Inaccessible")

        print(f"\n{BOLD}COMMANDS:{RESET} [indices], [page], [nuclear], [n] Next, [p] Prev, [q] Back")
        cmd = input("Selection > ").strip().lower()
        if cmd == 'q': break
        if cmd == 'n': 
            if curr + page_size < len(items): curr += page_size
            else: print(f"{YELLOW}You are on the last page.{RESET}")
            continue
        if cmd == 'p': curr = max(0, curr - page_size); continue
        
        selected, indices = [], []
        if cmd == 'nuclear':
            if input(f"{RED}⚠️ Delete ALL duplicates? (y/n): {RESET}").lower() == 'y':
                selected, indices = items, list(range(1, len(items) + 1))
        elif cmd == 'page':
            selected, indices = items[curr:end], list(range(curr + 1, end + 1))
        else:
            indices = parse_selection(cmd, len(items))
            selected = [items[i-1] for i in indices]

        if selected:
            perform_deletion(selected)
            for i in sorted(indices, reverse=True): items.pop(i-1)
            if cmd == 'nuclear': break

def review_empties(items, root, recursive):
    curr = 0
    page_size = 10
    while curr < len(items):
        total_pages = math.ceil(len(items) / page_size)
        current_page = (curr // page_size) + 1
        end = min(curr + page_size, len(items))
        
        print(f"\n{CYAN}--- REVIEW EMPTY FOLDERS (Page {current_page} of {total_pages}) ---{RESET}")
        for i in range(curr, end): print(f"[{i+1}] {items[i]}")
        cmd = input("\n[indices], [page], [nuclear], [n] Next, [p] Prev, [q] Back > ").strip().lower()
        if cmd == 'q': break
        if cmd == 'n': 
            if curr + page_size < len(items): curr += page_size
            continue
        if cmd == 'p': curr = max(0, curr - page_size); continue
        
        selected = []
        if cmd == 'nuclear': selected = items[:]
        elif cmd == 'page': selected = items[curr:end]
        else:
            indices = parse_selection(cmd, len(items))
            selected = [items[i-1] for i in indices]
            
        if selected:
            for d in selected:
                try: send2trash(fix_path(d)); print(f"  🗑️ Removed: {d}")
                except: pass
            items[:] = find_empty_folders(root, recursive)
            if not items: break
    return items

def main():
    os.system('') 
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
        print(f"Total Recovered: {GREEN}{saved_mb:.2f} MB{RESET}")
        print("-" * 50)
        print("1) Review Duplicates (Largest First)")
        print("2) Review Empty Folders")
        print(f"3) {RED}FULL AUTO CLEAN (Duplicates & Empties){RESET}")
        print("4) Refresh Scan")
        print("5) Exit")
        
        choice = input("> ").strip()
        if choice == "1":
            review_menu(dups, root, args.recursive)
            empties = find_empty_folders(root, args.recursive) 
        elif choice == "2":
            empties = review_empties(empties, root, args.recursive)
        elif choice == "3":
            confirm = input(f"{RED}⚠️ This will trash ALL duplicates and ALL empty folders. Proceed? (y/n): {RESET}").lower()
            if confirm == 'y':
                perform_deletion(dups)
                dups = []
                while True:
                    current_empties = find_empty_folders(root, args.recursive)
                    if not current_empties: break
                    for d in current_empties:
                        try: send2trash(fix_path(d))
                        except: pass
                empties = []
                print(f"{GREEN}✅ System Cleaned.{RESET}")
        elif choice == "4":
            dups = find_duplicates(root, args.recursive)
            empties = find_empty_folders(root, args.recursive)
        elif choice == "5": break

if __name__ == "__main__":
    main()
