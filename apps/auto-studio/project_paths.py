"""Client-aware project path resolution for the studio toolchain.

Layout supported:
    projects/<project>/                 (flat, legacy)
    projects/<client>/<project>/        (nested, multi-client)

A directory counts as a *project* if it contains PROJECT.yaml or
style_kernel.json. A client folder is any projects/ child that contains
project subdirectories — note a folder can be both (legacy umbrella
projects that now hold per-strip subprojects), so depth-2 is always
scanned.

Resolution order for resolve_project(name):
    1. `name` is an existing directory path (absolute or cwd-relative)
    2. projects/<name>  (slashes allowed: "client/project")
    3. unique basename match across depth-2 (e.g. "broderick_torg"
       -> projects/broderick/broderick_torg)
Ambiguous basenames raise ValueError; a miss returns the projects/<name>
join so callers keep their existing "not found" handling.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))          # apps/auto-studio
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))        # repo root

_MARKERS = ("PROJECT.yaml", "style_kernel.json")


def projects_root() -> str:
    return os.path.join(_REPO_ROOT, "projects")


def is_project_dir(path: str) -> bool:
    return os.path.isdir(path) and any(
        os.path.isfile(os.path.join(path, m)) for m in _MARKERS)


def list_projects():
    """Return sorted [(name, abs_path)]. Flat projects use their folder
    name; nested ones use the qualified "client/project" form. Depth-2 is
    scanned under every projects/ child, including ones that are projects
    themselves."""
    root = projects_root()
    if not os.path.isdir(root):
        return []
    out = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        if is_project_dir(p):
            out.append((d, p))
        for sub in sorted(os.listdir(p)):
            sp = os.path.join(p, sub)
            if is_project_dir(sp):
                out.append((f"{d}/{sub}", sp))
    return out


def resolve_project(name: str) -> str:
    """Resolve a project identifier to a directory path (see module doc)."""
    if os.path.isdir(name):
        return name
    parts = str(name).replace("\\", "/").strip("/").split("/")
    cand = os.path.join(projects_root(), *parts)
    if os.path.isdir(cand):
        return cand
    if len(parts) == 1:
        matches = [p for n, p in list_projects()
                   if os.path.basename(p) == parts[0]]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous project name {name!r}; use client/name. "
                f"Matches: {matches}")
    return cand
