#!/usr/bin/env python3
"""
Generate all_code.txt with file tree and contents of .py and .json files
Excludes __pycache__, logs, and other unnecessary files
"""

import os
import fnmatch

def should_include_file(filepath):
    """Check if file should be included in output"""
    # Skip if in __pycache__ directory
    if '__pycache__' in filepath:
        return False
    
    # Skip log files
    if filepath.endswith('.log') or 'logs/' in filepath or '/logs/' in filepath:
        return False
    
    # Skip all_code.txt itself
    if filepath.endswith('all_code.txt'):
        return False
    
    # Include only .py and .json files
    return filepath.endswith('.py') or filepath.endswith('.json')

def generate_tree(startpath, prefix="", is_last=True, is_root=False):
    """Generate tree structure of directory"""
    tree_lines = []
    entries = []
    
    # Get all entries in directory
    try:
        for entry in os.listdir(startpath):
            if entry.startswith('.'):
                continue
            if entry == '__pycache__':
                continue
            if entry == 'logs':
                continue
            if entry == 'all_code.txt':
                continue
            entries.append(entry)
    except PermissionError:
        return tree_lines
    
    entries.sort()
    
    for i, entry in enumerate(entries):
        path = os.path.join(startpath, entry)
        is_last_entry = i == len(entries) - 1
        
        # Draw tree branch
        if is_root:
            current_prefix = ""
            extension = ""
        else:
            current_prefix = prefix + ("└── " if is_last_entry else "├── ")
            extension = prefix + ("    " if is_last_entry else "│   ")
        
        tree_lines.append(current_prefix + entry + ("/" if os.path.isdir(path) else ""))
        
        # Recurse for directories
        if os.path.isdir(path):
            tree_lines.extend(generate_tree(path, extension, is_last_entry))
    
    return tree_lines

def main():
    """Main function to generate all_code.txt"""
    output_file = "all_code.txt"
    current_dir = os.getcwd()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write(f"Project Code Overview: {os.path.basename(current_dir)}\n")
        f.write("=" * 80 + "\n\n")
        
        # Write file tree
        f.write("FILE TREE:\n")
        f.write("-" * 40 + "\n")
        tree_lines = generate_tree(current_dir, "", True, True)
        for line in tree_lines:
            f.write(line + "\n")
        f.write("\n")
        
        # Collect all relevant files
        files_to_include = []
        for root, dirs, files in os.walk(current_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__' and d != 'logs' and not d.startswith('.')]
            
            for file in files:
                filepath = os.path.join(root, file)
                if should_include_file(filepath):
                    files_to_include.append(filepath)
        
        # Sort files for consistent output
        files_to_include.sort()
        
        # Write file contents
        f.write("\n" + "=" * 80 + "\n")
        f.write("FILE CONTENTS:\n")
        f.write("=" * 80 + "\n")
        
        for filepath in files_to_include:
            relative_path = os.path.relpath(filepath, current_dir)
            
            f.write("\n" + "-" * 80 + "\n")
            f.write(f"FILE: {relative_path}\n")
            f.write("-" * 80 + "\n\n")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    f.write(content)
                    if not content.endswith('\n'):
                        f.write('\n')
            except Exception as e:
                f.write(f"ERROR reading file: {e}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF CODE OVERVIEW\n")
        f.write("=" * 80 + "\n")
    
    print(f"Successfully generated {output_file}")
    print(f"Total files included: {len(files_to_include)}")

if __name__ == "__main__":
    main()