import os
import ast
import re
import subprocess

root_dir = r"c:\Users\hp\OneDrive\Pictures\Documents\Desktop\MantraSetu\FINAL ai Mantra setu\MantraSetu-Saarthi-feature-ai-intent-engine"

def get_purpose(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return "Cannot read"
    
    if file_path.endswith('.py'):
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            if docstring:
                return docstring.split("\n")[0][:100].strip()
            
            # Imports
            imports = [n.names[0].name for n in tree.body if isinstance(n, ast.Import)]
            import_froms = [n.module for n in tree.body if isinstance(n, ast.ImportFrom) and n.module]
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
            
            if classes:
                return f"Defines classes: {', '.join(classes[:3])}"
            elif funcs:
                return f"Defines functions: {', '.join(funcs[:3])}"
            elif imports or import_froms:
                return f"Imports: {', '.join(imports[:2] + import_froms[:2])}"
            else:
                return "No explicit docstring, classes, functions, or imports"
        except Exception:
            pass
    
    # fallback
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith(('#', '//')):
            return line[:100]
    return "Empty or comments only"

files_data = []
for d in ['app', 'tests']:
    d_path = os.path.join(root_dir, d)
    for root, dirs, files in os.walk(d_path):
        if '__pycache__' in root:
            continue
        for f in files:
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, root_dir)
            files_data.append((rel_path, get_purpose(path)))

# Secrets regex
secrets_regex = re.compile(r'(API_KEY\s*=|sk-[a-zA-Z0-9]{32,}|Bearer\s+[A-Za-z0-9\-\._~+\/]{15,}={0,2}|password\s*=\s*[\'"].+[\'"]|secret\s*=\s*[\'"].+[\'"])', re.IGNORECASE)

secrets_found = []
# Exclude known files/dirs
exclude_dirs = ['.git', '.pytest_cache', '__pycache__', 'scratch', 'phase1_output', 'k8s', 'docs', '.ruff_cache', 'sprint_x_enablement']
exclude_files = ['audit_result.json', 'architecture_lifecycle_summary.json', 'ai_intelligence_validation_v2_report.json', 'audit_summary.json', 'deep_20_gate_audit_summary.json']
for root, dirs, files in os.walk(root_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for f in files:
        if f in exclude_files or f.endswith(('.wav', '.mp3', '.pyc', '.exe', '.dll')):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, "r", encoding="utf-8") as file:
                for i, line in enumerate(file):
                    if secrets_regex.search(line):
                        secrets_found.append(f"{os.path.relpath(path, root_dir)}:{i+1}")
        except Exception:
            pass

# Env var fallbacks
env_regex = re.compile(r'(os\.getenv\([\'"][^\'"]+[\'"]\s*,\s*[\'"][^\'"]*[\'"]\)|os\.environ\.get\([\'"][^\'"]+[\'"]\s*,\s*[\'"][^\'"]*[\'"]\))')
env_simple_regex = re.compile(r'(os\.getenv\([\'"][^\'"]+[\'"]\)|os\.environ\.get\([\'"][^\'"]+[\'"]\))')

fallbacks_found = []
for root, dirs, files in os.walk(os.path.join(root_dir, 'app')):
    if '__pycache__' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
                # find explicit default string fallbacks
                for i, line in enumerate(content.split('\n')):
                    if env_regex.search(line):
                        fallbacks_found.append(f"{os.path.relpath(path, root_dir)}:{i+1} - {line.strip()}")
                    elif env_simple_regex.search(line):
                        # check if it's checked for None
                        if 'is None' not in content and 'not ' not in content and 'raise' not in content:
                           # This is crude but catches unchecked ones, let's just log the line
                           # fallbacks_found.append(f"{os.path.relpath(path, root_dir)}:{i+1} - {line.strip()} (potential silent)")
                           pass
        except Exception:
            pass

# check git history for .env
try:
    git_log = subprocess.check_output(['git', 'log', '--all', '--full-history', '--', '.env'], cwd=root_dir, stderr=subprocess.STDOUT).decode('utf-8')
    if git_log.strip():
        git_status = ".env found in git history!"
    else:
        git_status = ".env NOT found in git history."
except Exception as e:
    git_status = f"Failed to check git history: {str(e)}"

# check gitignore
try:
    with open(os.path.join(root_dir, '.gitignore'), "r") as f:
        gitignore_content = f.read()
        if '.env' in gitignore_content:
            gitignore_status = ".env is in .gitignore"
        else:
            gitignore_status = ".env is NOT in .gitignore"
except Exception:
    gitignore_status = "Could not read .gitignore"

with open(os.path.join(root_dir, "scratch", "audit_report.txt"), "w", encoding="utf-8") as out:
    out.write("INVENTORY\n=========\n")
    for rp, purp in files_data:
        out.write(f"{rp}: {purp}\n")
    
    out.write("\nSECRETS FOUND\n=============\n")
    if secrets_found:
        for s in secrets_found:
            out.write(f"{s}\n")
    else:
        out.write("none found\n")
        
    out.write("\nENV FALLBACKS\n=============\n")
    if fallbacks_found:
        for f in fallbacks_found:
            out.write(f"{f}\n")
    else:
        out.write("none found\n")
        
    out.write("\nGIT STATUS\n==========\n")
    out.write(f"{git_status}\n")
    out.write(f"{gitignore_status}\n")
