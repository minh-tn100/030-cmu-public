"""Skill loader (post-capstone extension, after the Agent Skills pattern): progressive disclosure for an assistant around DesignBench.
Level 1 = name + description in the prompt; level 2 = SKILL.md body, only through load_skill. Read-only: this module never runs scripts.
It is NOT given to the review agent, whose only tool stays `retrieve`."""
from __future__ import annotations
import pathlib, re
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "skills"
NAME_OK, MAX_BODY = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$"), 20_000

def index_skills(root: pathlib.Path = ROOT) -> dict:
    """Level 1: parse ONLY the frontmatter. A malformed skill is skipped, never fatal."""
    catalog = {}
    for f in sorted(pathlib.Path(root).glob("*/SKILL.md")):
        try:
            _, front, _body = f.read_text(encoding="utf-8").split("---", 2)
            meta = yaml.safe_load(front)
            name, desc = meta["name"], str(meta["description"]).strip()
            if name != f.parent.name or not NAME_OK.match(name) or not desc:
                continue                                    # folder name must equal skill name: no shadowing
            catalog[name] = {"desc": desc, "path": f}
        except (ValueError, KeyError, TypeError, yaml.YAMLError, OSError):
            continue
    return catalog

CATALOG = index_skills()

def menu(catalog: dict | None = None) -> str:
    return "\n".join(f"- {n}: {s['desc']}" for n, s in (catalog or CATALOG).items())

def load_skill(name: str, catalog: dict | None = None) -> str:
    """Level 2: return the SKILL.md body. Lookup is by catalog key only, so no caller-supplied path is ever opened."""
    cat = CATALOG if catalog is None else catalog
    if not isinstance(name, str) or name not in cat:
        return f"Unknown skill. Available: {', '.join(cat) or 'none'}"          # fail gracefully: return the menu
    text = cat[name]["path"].read_text(encoding="utf-8")
    return text[:MAX_BODY]

def as_tool():
    from langchain_core.tools import tool
    @tool
    def load_skill_tool(name: str) -> str:
        """Load the full instructions for a skill by name."""
        return load_skill(name)
    load_skill_tool.name = "load_skill"
    return load_skill_tool
