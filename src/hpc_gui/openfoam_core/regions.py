"""Static region and mesh-boundary readers (W65 LINT-COMPAT).

Both helpers inspect already-tokenized static text. Any dynamic marker
(``$variable``, directives, includes) yields ``None`` so callers emit a
contextual diagnostic instead of interpreting the source.
"""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.openfoam_core.document import ParsedDictionary
from hpc_gui.openfoam_core.lexer import lex


@dataclass(frozen=True, slots=True)
class RegionGroup:
    region_type: str
    names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RegionProperties:
    groups: tuple[RegionGroup, ...] = ()
    names: tuple[str, ...] = ()

    @property
    def summary(self) -> str:
        if not self.groups:
            return "no regions declared"
        return "; ".join(
            f"{group.region_type} ({', '.join(group.names)})" for group in self.groups
        )


def parse_region_properties(parsed: ParsedDictionary) -> RegionProperties:
    """Read the static ``regions`` list; raise ``ValueError`` when dynamic."""
    matches = parsed.find("regions", scope=())
    if len(matches) != 1:
        raise ValueError("expected exactly one static regions entry")
    entry = matches[0]
    if entry.is_dictionary or entry.dynamic:
        raise ValueError("regions entry is not a static list")
    atoms = [tok.value for tok in entry.value_tokens if tok.kind in ("atom", "punct")]
    if len(atoms) < 2 or atoms[0] != "(" or atoms[-1] != ")":
        raise ValueError("regions entry is not a static parenthesised list")
    inner = atoms[1:-1]
    groups: list[RegionGroup] = []
    cursor = 0
    while cursor < len(inner):
        region_type = inner[cursor]
        cursor += 1
        if cursor >= len(inner) or inner[cursor] != "(":
            raise ValueError("region declaration is not a static type/name-list pair")
        cursor += 1
        names: list[str] = []
        while cursor < len(inner) and inner[cursor] != ")":
            token = inner[cursor]
            if token in ("(", ")") or "$" in token:
                raise ValueError("region names must be static words")
            names.append(token)
            cursor += 1
        if cursor >= len(inner) or not names:
            raise ValueError("region declaration has no static names")
        cursor += 1
        groups.append(RegionGroup(region_type, tuple(names)))
    if not groups:
        raise ValueError("regions entry declares no regions")
    seen: set[str] = set()
    for group in groups:
        for name in group.names:
            if name in seen:
                raise ValueError(f"duplicate region name {name!r}")
            seen.add(name)
    ordered = [name for group in groups for name in group.names]
    return RegionProperties(groups=tuple(groups), names=tuple(ordered))


def parse_mesh_boundary_names(source: str) -> frozenset[str] | None:
    """Return static patch names, or ``None`` when not statically known."""
    if not isinstance(source, str):
        raise TypeError("mesh boundary source must be str")
    tokens = [t for t in lex(source) if t.kind != "COMMENT"]
    if any(t.kind == "DIRECTIVE" for t in tokens):
        return None
    if any("$" in t.text for t in tokens if t.kind in ("WORD", "NUMBER")):
        return None
    depth = 0
    start = -1
    stop = -1
    for index, tok in enumerate(tokens):
        if tok.text == "(" and tok.kind in ("LPAREN", "WORD"):
            if depth == 0 and start == -1:
                start = index
            depth += 1
        elif tok.text == ")" and tok.kind in ("RPAREN", "WORD"):
            depth = max(0, depth - 1)
            if depth == 0 and start != -1:
                stop = index
                break
    if start == -1 or stop == -1:
        return None
    inner = tokens[start + 1 : stop]
    names: list[str] = []
    cursor = 0
    while cursor < len(inner):
        tok = inner[cursor]
        if tok.kind in ("WORD", "NUMBER", "STRING") and tok.text not in ("{", "}", "(", ")", ";"):
            ahead = inner[cursor + 1] if cursor + 1 < len(inner) else None
            if ahead is not None and ahead.text == "{" and tok.kind == "WORD":
                names.append(tok.text)
                nested = 0
                cursor += 1
                while cursor < len(inner):
                    if inner[cursor].text == "{":
                        nested += 1
                    elif inner[cursor].text == "}":
                        nested -= 1
                        if nested <= 0:
                            break
                    cursor += 1
        cursor += 1
    if not names:
        if not inner or all(tok.kind == "NUMBER" for tok in inner):
            return frozenset()
        return None
    if len(set(names)) != len(names):
        return None
    return frozenset(names)
