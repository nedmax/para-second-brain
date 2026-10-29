#!/usr/bin/env python3
"""Read-only PARA checks using only the Python standard library."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import unquote, urlsplit


CATEGORIES = ("Inbox", "Projects", "Areas", "Resources", "Archive")
CLOSED = {"concluido", "concluida", "completed", "complete", "done", "cancelado", "cancelled", "archived", "arquivado", "inativo", "inactive"}
MD_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")
WIKI_LINK = re.compile(r"!?\[\[([^\]\n]+)\]\]")
TODO = re.compile(r"^\s*[-*+]\s+\[ \]\s+\S", re.M)


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def prose(text):
    """Ignore fenced and inline code, including longer/nested fences."""
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            token = match.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(re.sub(r"(`+).*?\1", "", line))
    return "\n".join(lines)


def fields(text):
    result = {}
    for line in prose(text).splitlines():
        match = re.match(r"^\s*(?:[-*]\s+)?([\w À-ÿ]+):\s*(.*?)\s*$", line)
        if match:
            key, value = match.groups()
            result[normalize(key.strip())] = value.strip("\"'")
    return result


def has_goal(text):
    if any(fields(text).get(k) for k in ("objetivo", "resultado", "goal", "outcome")):
        return True
    # A heading alone is not an outcome statement.
    match = re.search(r"^#{1,6}\s+(?:objetivo|resultado|goal|outcome|desired outcome)\s*\n([^#]+)", normalize(prose(text)), re.M)
    return bool(match and match.group(1).strip())


def inside(root, path):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_path(root, path):
    """Refuse symlinks (even within the vault) and paths escaping the root."""
    lexical = Path(os.path.abspath(path))
    if not inside(root, lexical):
        return False
    cursor = root
    for part in lexical.relative_to(root).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return False
    return inside(root, lexical.resolve())


def markdown_files(root):
    files = []
    for base, dirs, names in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(base) / d).is_symlink() and d not in {"node_modules", "__pycache__"})
        for name in sorted(names):
            path = Path(base) / name
            if not name.startswith(".") and path.suffix.lower() == ".md" and safe_path(root, path):
                files.append(path)
    return files


def local_target(root, source, raw):
    raw = raw.strip()
    if raw.startswith("<"):
        raw = raw[1:].split(">", 1)[0]
    else:
        raw = re.split(r'\s+[\"\']', raw, maxsplit=1)[0]
    parsed = urlsplit(raw)
    if not raw or raw.startswith("#") or parsed.scheme or parsed.netloc:
        return None
    # Vault-root absolute paths are never read as filesystem absolute paths.
    base = root if parsed.path.startswith("/") else source.parent
    return Path(os.path.abspath(base / unquote(parsed.path).lstrip("/")))


def validate(root, checks, stale_days=30):
    findings = []
    checked = 0

    def add(level, code, path, message):
        findings.append({"level": level, "code": code, "path": str(path.relative_to(root)), "message": message})

    if "structure" in checks:
        for category in CATEGORIES:
            checked += 1
            path = root / category
            if not path.is_dir() or path.is_symlink():
                add("error", "missing_category", path, "Pasta canônica ausente, não é diretório ou é symlink; confira o esquema antes de criar.")

    # Structure-only intentionally does not traverse or read any note content.
    notes = markdown_files(root) if checks - {"structure"} else []
    cache = {}

    def read(path):
        if path not in cache:
            cache[path] = path.read_text(encoding="utf-8-sig")
        return cache[path]

    if "project-health" in checks and (root / "Projects").is_dir() and not (root / "Projects").is_symlink():
        for entry in sorted((root / "Projects").iterdir()):
            if entry.name.startswith(".") or entry.is_symlink():
                continue
            overview = entry
            if entry.is_dir():
                candidates = {p.name.casefold(): p for p in entry.iterdir() if p.is_file() and not p.is_symlink()}
                overview = next((candidates[n] for n in ("project.md", "readme.md", "index.md", entry.name.casefold() + ".md") if n in candidates), None)
            elif entry.suffix.lower() != ".md":
                continue
            elif entry.stem.casefold() in {"index", "readme"}:
                continue
            checked += 1
            if overview is None:
                add("warning", "missing_overview", entry, "Projeto sem nota de visão geral; use README.md, project.md, index.md ou o nome da pasta.")
                continue
            text = read(overview)
            status = normalize(fields(text).get("status", ""))
            if status in CLOSED:
                add("info", "archive_candidate", entry, "Status encerrado/inativo em Projects; revisar destino de arquivo.")
                continue
            if not status:
                add("warning", "missing_status", overview, "Informe status na nota do projeto.")
            if not has_goal(text):
                add("warning", "missing_goal", overview, "Registre objetivo ou resultado verificável.")
            pending = bool(TODO.search(prose(text)))
            if not pending:
                for raw in MD_LINK.findall(prose(text)):
                    target = local_target(root, overview, raw)
                    if target and safe_path(root, target) and target.is_file() and target.suffix.lower() == ".md" and TODO.search(prose(read(target))):
                        pending = True
                        break
            if not pending:
                add("warning", "missing_next_action", overview, "Registre próxima ação como checkbox pendente, aqui ou em arquivo de tarefas linkado.")
            project_notes = [p for p in notes if inside(entry, p)] if entry.is_dir() else [entry]
            latest = max(p.stat().st_mtime for p in project_notes)
            days = int((time.time() - latest) / 86400)
            if days >= stale_days:
                add("warning", "inactive_project", entry, f"Sem edição há {days} dias; revisar situação, sem inferir conclusão.")

    if "links" in checks:
        for source in notes:
            checked += 1
            text = prose(read(source))
            for raw in MD_LINK.findall(text):
                target = local_target(root, source, raw)
                if target is not None and (not safe_path(root, target) or not target.exists()):
                    add("warning", "unresolved_link", source, "Link local ausente ou fora do escopo permitido: " + raw)
            for raw in WIKI_LINK.findall(text):
                name = raw.split("|", 1)[0].split("#", 1)[0].strip()
                if not name:
                    continue
                relative = Path(name)
                if relative.suffix == "":
                    relative = relative.with_suffix(".md")
                matches = [p for p in (source.parent / relative, root / relative) if safe_path(root, p) and p.is_file()]
                if not matches and "/" not in name:
                    matches = [p for p in notes if p.name == relative.name]
                unique = {p.resolve() for p in matches}
                if not unique:
                    add("warning", "unresolved_wikilink", source, "Wikilink sem arquivo correspondente: " + name)
                elif len(unique) > 1:
                    add("warning", "ambiguous_wikilink", source, "Qualifique o caminho do wikilink: " + name)

    if "daily" in checks:
        for path in notes:
            if path.parent != root or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem):
                continue
            checked += 1
            try:
                date = dt.date.fromisoformat(path.stem)
            except ValueError:
                add("warning", "invalid_daily_date", path, "Data inválida no nome do diário.")
                continue
            if (dt.date.today() - date).days >= 30:
                add("info", "old_daily", path, f"Candidato a revisão para Archive/{date:%Y/%m}/; preservar links.")

    counts = {level: sum(f["level"] == level for f in findings) for level in ("error", "warning", "info")}
    return {"checked": checked, "counts": counts, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    for name in ("structure", "project-health", "links", "daily"):
        parser.add_argument("--" + name, action="store_true")
    parser.add_argument("--stale-days", type=int, default=30)
    args = parser.parse_args(argv)
    if args.stale_days < 1:
        parser.error("--stale-days deve ser positivo")
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        parser.error("O workspace precisa ser um diretório existente")
    checks = {k for k in ("structure", "project-health", "links", "daily") if getattr(args, k.replace("-", "_"))}
    try:
        report = validate(root, checks or {"structure", "project-health", "links", "daily"}, args.stale_days)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Falha ao validar: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("# Validação PARA\n")
        print(f"Itens verificados: {report['checked']}; erros: {report['counts']['error']}; avisos: {report['counts']['warning']}; informações: {report['counts']['info']}\n")
        for finding in report["findings"]:
            print(f"- [{finding['level']}] `{finding['path']}` — {finding['message']}")
        if not report["findings"]:
            print("Nenhum achado nos checks executados.")
    return 1 if report["counts"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
