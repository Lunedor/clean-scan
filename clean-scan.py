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
    if os.name == 'nt':  # Apply long path fix only on Windows
        if abs_path.startswith("\\\\?\\"): 
            return abs_path
        return "\\\\?\\" + abs_path
    return abs_path      # Return normal absolute path on Unix/Linux

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
    except Exception: return None

def get_color_for_size(mb):
    if mb > 100: return RED
    if mb > 10: return YELLOW
    return GREEN

def find_duplicates(roots, recursive):
    size_map = defaultdict(list)
    print(f"{CYAN}🔍 Scanning for duplicates across {len(roots)} location(s)...{RESET}")
    
    def files_iter():
        seen = set()
        for root in roots:
            if recursive:
                for d, _, files in os.walk(root):
                    for f in files: 
                        p = os.path.abspath(os.path.join(d, f))
                        if p not in seen:
                            seen.add(p)
                            yield p
            else:
                try:
                    for f in os.listdir(root):
                        p = os.path.abspath(os.path.join(root, f))
                        if os.path.isfile(p) and p not in seen:
                            seen.add(p)
                            yield p
                except OSError: 
                    pass

    for path in files_iter():
        try: size_map[os.path.getsize(fix_path(path))].append(path)
        except Exception: continue

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
            if len(g) > 1:
                # Keep the shortest path as the primary original
                g.sort(key=len)
                final.append(g)
    final.sort(key=lambda x: os.path.getsize(fix_path(x[0])) * (len(x)-1), reverse=True)
    return final

def find_empty_folders(roots, recursive):
    empty = []
    seen = set()
    for root in roots:
        if not os.path.isdir(root): continue
        
        if not recursive:
            try:
                root_abs = os.path.abspath(root)
                if root_abs not in seen and not os.listdir(root_abs): 
                    empty.append(root_abs)
                    seen.add(root_abs)
            except OSError: pass
            continue

        for d, subdirs, files in os.walk(root, topdown=False):
            d_abs = os.path.abspath(d)
            if d_abs == os.path.abspath(root) or d_abs in seen: continue 
            seen.add(d_abs)
            try:
                if not os.listdir(fix_path(d_abs)): empty.append(d_abs)
            except OSError: pass
    return empty
    
def parse_selection(selection, max_val):
    result = set()
    for part in selection.replace(",", " ").split():
        if "-" in part:
            try:
                s, e = map(int, part.split("-"))
                # Ensure range is valid and ascending
                if s <= e:
                    result.update(range(s, e + 1))
            except ValueError: 
                continue
        elif part.isdigit(): 
            result.add(int(part))
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

def review_menu(items, roots, recursive):
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
            except Exception: print(f"[{i+1}] Inaccessible")

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
            
            # TRIGGER DRILL-DOWN: If only one group is selected, open the inspection menu
            if len(indices) == 1:
                idx = indices[0] - 1
                target_group = items[idx]
                
                if inspect_and_trash(target_group):
                    # If 1 or 0 files remain, it's no longer a duplicate group. Remove it from the main list.
                    if len(target_group) < 2:
                        items.pop(idx)
                    curr = 0  # Reset pagination to prevent skipping
                continue
                
            # TRIGGER BATCH AUTO-DELETE: If multiple groups are selected
            else:
                selected = [items[i-1] for i in indices]

        if selected:
            perform_deletion(selected)
            for i in sorted(indices, reverse=True): items.pop(i-1)
            curr = 0  
            if cmd == 'nuclear': break

def review_empties(items, roots, recursive):
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
                except Exception: pass
            items[:] = find_empty_folders(roots, recursive)
            curr = 0  # FIX: Reset view after list mutation
            if not items: break
    return items

def inspect_and_trash(group):
    global SPACE_SAVED_BYTES
    print(f"\n{BOLD}{CYAN}=== INSPECTING DUPLICATE GROUP ==={RESET}")
    
    for i, path in enumerate(group):
        try:
            mtime = os.path.getmtime(fix_path(path))
            date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            print(f"[{i+1}] {date_str} | {path}")
        except Exception:
            print(f"[{i+1}] Unknown Date | {path}")
            
    print(f"\n{YELLOW}Enter indices of files to TRASH (e.g., '1 3'), or 'q' to cancel:{RESET}")
    cmd = input("> ").strip().lower()
    if cmd == 'q' or not cmd: 
        return False
        
    to_trash = parse_selection(cmd, len(group))
    if not to_trash: 
        return False
        
    for i in sorted(to_trash, reverse=True):
        f = group[i-1]
        try:
            f_size = os.path.getsize(fix_path(f))
            send2trash(fix_path(f))
            print(f"  {RED}🗑️ Trashed:{RESET} {f}")
            SPACE_SAVED_BYTES += f_size
            group.pop(i-1)
        except Exception: 
            pass
            
    return True # Indicates the group was modified
    
def main():
    os.system('') 
    parser = argparse.ArgumentParser(description="Scan for duplicate files and empty folders.")
    
    # No positional arguments required anymore.
    # The script always assumes the Current Working Directory is the primary target.
    parser.add_argument("-a", "--add", action="append", default=[], help="Additional directories to include")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories")
    args = parser.parse_args()
    
    # 1. Start with the Current Working Directory
    # 2. Add any folders passed via -a
    # 3. Deduplicate and fix paths
    raw_roots = [os.getcwd()] + args.add
    roots = list(dict.fromkeys(os.path.abspath(f) for f in raw_roots))

    dups = find_duplicates(roots, args.recursive)
    empties = find_empty_folders(roots, args.recursive)

    while True:
        saved_mb = SPACE_SAVED_BYTES / (1024*1024)
        display_roots = ", ".join(roots)
        
        print(f"\n{BOLD}{CYAN}===== DUPLICATE SCANNER ====={RESET}")
        print(f"Scanning: {display_roots}")
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
            review_menu(dups, roots, args.recursive)
            empties = find_empty_folders(roots, args.recursive) 
        elif choice == "2":
            empties = review_empties(empties, roots, args.recursive)
        elif choice == "3":
            confirm = input(f"{RED}⚠️ This will trash ALL duplicates and ALL empty folders. Proceed? (y/n): {RESET}").lower()
            if confirm == 'y':
                perform_deletion(dups)
                dups.clear()
                
                while True:
                    current_empties = find_empty_folders(roots, args.recursive)
                    if not current_empties: break
                    
                    deleted_any = False
                    for d in current_empties:
                        try: 
                            send2trash(fix_path(d))
                            deleted_any = True
                        except OSError: pass
                            
                    if not deleted_any: break
                        
                empties.clear()
                print(f"{GREEN}✅ System Cleaned.{RESET}")
        elif choice == "4":
            dups = find_duplicates(roots, args.recursive)
            empties = find_empty_folders(roots, args.recursive)
        elif choice == "5": break

if __name__ == "__main__":
    main()
