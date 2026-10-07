"""Check publishable files, local Markdown links, and evidence consistency."""

import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "OpenAI token": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b"),
}
PRIVATE_ROOTS = {".agents", ".freebuff", ".local", ".venv", "venv"}


def candidates():
    raw = subprocess.check_output(["git", "ls-files", "-z", "--cached",
                                   "--others", "--exclude-standard"], cwd=ROOT)
    return sorted({ROOT / name.decode("utf-8") for name in raw.split(b"\0") if name})


def exact_case_exists(path):
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    current = ROOT
    for part in parts:
        if not current.is_dir() or part not in {p.name for p in current.iterdir()}:
            return False
        current /= part
    return current.exists()


def main():
    errors = []
    files = [path for path in candidates() if path.is_file()]
    for path in files:
        relative = path.relative_to(ROOT)
        if relative.parts[0] in PRIVATE_ROOTS:
            errors.append(f"Local-only file tracked: {relative}")
        if path.suffix.lower() in {".step", ".stl"}:
            errors.append(f"Uncleared CAD asset tracked: {relative}")
        if path.suffix.lower() not in {".md", ".py", ".c", ".h", ".json", ".yml", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            errors.append(f"Non-UTF-8 text file: {relative}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"Possible {label}: {relative} (value withheld)")
        if path.suffix == ".md":
            # Avoid examples inside fenced code blocks.
            prose = re.sub(r"```.*?```", "", text, flags=re.S)
            for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", prose):
                target = target.strip().split(' "', 1)[0].strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("#"):
                    continue
                if not exact_case_exists((path.parent / unquote(parsed.path)).resolve()):
                    errors.append(f"Broken local link: {relative} -> {target}")
        if path.suffix == ".json":
            try:
                json.loads(text, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            except ValueError:
                errors.append(f"Invalid/non-finite JSON: {relative}")
    for name in ("mpc_model.h", "learned_model.h"):
        if (ROOT / "results" / name).read_bytes() != (ROOT / "firmware/Core/Inc" / name).read_bytes():
            errors.append(f"Firmware export differs from published snapshot: {name}")
    if not errors:
        subprocess.run([sys.executable, str(ROOT / "scripts/summarize_results.py"), "--check"],
                       check=True, cwd=ROOT)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(f"Repository checks passed ({len(files)} publishable files inspected)")


if __name__ == "__main__":
    main()
