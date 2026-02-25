#!/usr/bin/env python3
"""
Inject category and priority into NEU repo item JSONs for better REI ordering.
Overwrites category/priority only; deterministic and idempotent.
"""

from pathlib import Path
import json
import re
import sys

# Repo root: script lives in scripts/, items live in items/
REPO_ROOT = Path(__file__).resolve().parent.parent
ITEMS_DIR = REPO_ROOT / "items"

# Category order for priority (lower = earlier in REI). Unlisted categories sort last.
CATEGORY_ORDER = [
    "minions",
    "enchants",
    "pets",
    "rift",
    "accessories",
    "weapons",
    "armor",
    "tools",
    "blocks",
    "consumables",
    "vanilla",
    "misc",
]

# Rules: (pattern_type, pattern, category)
# - "prefix": internalname.startswith(pattern)
# - "suffix": internalname.endswith(pattern)
# - "contains": pattern in internalname (substring)
# - "regex": re.search(pattern, internalname)
# - "itemid": item["itemid"] matches (pattern is itemid prefix e.g. "minecraft:enchanted_book")
# First matching rule wins.
RULES = [
    # Enchants: enchanted books (itemid) or enchant runes
    ("itemid", "minecraft:enchanted_book", "enchants"),
    ("contains", "ENCHANT_RUNE", "enchants"),
    ("contains", "_RUNE;", "enchants"),
    # Minions: minion upgrades and minion items
    ("contains", "MINION", "minions"),
    # Pets: pet items and skins (PET_ prefix or ;tier skulls)
    ("prefix", "PET_SKIN_", "pets"),
    ("prefix", "PET_", "pets"),
    ("regex", r";\d+$", "pets"),  # WOLF;1, ZOMBIE;2 etc. - pet tiers (after MINION so MINION_* wins)
    # Rift
    ("contains", "RIFT", "rift"),
    # Accessories
    ("suffix", "_TALISMAN", "accessories"),
    ("suffix", "_RING", "accessories"),
    ("suffix", "_ARTIFACT", "accessories"),
    ("contains", "BRACELET", "accessories"),
    ("contains", "NECKLACE", "accessories"),
    ("contains", "CLOAK", "accessories"),
    ("contains", "GLOVES", "accessories"),
    ("contains", "BELT", "accessories"),
    ("contains", "GAUNTLET", "accessories"),
    ("contains", "ACCESSORY", "accessories"),
    ("suffix", "_HAT", "accessories"),  # HAT as accessory (e.g. REAPER_MASK style could be armor; we use _HAT suffix)
    ("contains", "TALISMAN_", "accessories"),
    # Armor (after accessories so TALISMAN doesn't match ARMOR)
    ("suffix", "_HELMET", "armor"),
    ("suffix", "_CHESTPLATE", "armor"),
    ("suffix", "_LEGGINGS", "armor"),
    ("suffix", "_BOOTS", "armor"),
    ("contains", "_ARMOR_", "armor"),
    # Weapons
    ("suffix", "_SWORD", "weapons"),
    ("suffix", "_BOW", "weapons"),
    ("suffix", "_CROSSBOW", "weapons"),
    ("contains", "LONGSWORD", "weapons"),
    # Tools
    ("suffix", "_PICKAXE", "tools"),
    ("suffix", "_AXE", "tools"),
    ("suffix", "_HOE", "tools"),
    ("suffix", "_SHOVEL", "tools"),
    ("suffix", "_DRILL", "tools"),
    ("suffix", "_FISHING_ROD", "tools"),
    ("contains", "WAND", "tools"),
    ("contains", "SHEARS", "tools"),
    # Blocks (common block-like names)
    ("prefix", "ENCHANTED_", "blocks"),  # enchanted materials (crafting blocks)
    ("suffix", "_BLOCK", "blocks"),
    ("suffix", "_LOG", "blocks"),
    ("suffix", "_PLANKS", "blocks"),
    ("suffix", "_STONE", "blocks"),
    # Consumables
    ("prefix", "POTION_", "consumables"),
    ("contains", "POTION", "consumables"),
    ("contains", "STEW", "consumables"),
    ("contains", "SOUP", "consumables"),
    # Vanilla: plain minecraft items (no SkyBlock id in typical slots)
    ("itemid", "minecraft:stick", "vanilla"),
    ("itemid", "minecraft:dirt", "vanilla"),
]


def get_category(data: dict, internalname: str) -> str:
    itemid = (data.get("itemid") or "").strip()
    for rule_type, pattern, category in RULES:
        if rule_type == "itemid":
            if itemid == pattern or itemid.startswith(pattern + " "):
                return category
            continue
        if rule_type == "prefix" and internalname.startswith(pattern):
            return category
        if rule_type == "suffix" and internalname.endswith(pattern):
            return category
        if rule_type == "contains" and pattern in internalname:
            return category
        if rule_type == "regex" and re.search(pattern, internalname):
            return category
    return "misc"


def get_priority(category: str) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


def inject_one(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Read error {path}: {e}", file=sys.stderr)
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON error {path}: {e}", file=sys.stderr)
        return False

    internalname = data.get("internalname")
    if not internalname:
        # Derive from filename (e.g. FROG_ANIMAL.json -> FROG_ANIMAL)
        internalname = path.stem
    internalname = str(internalname).strip()

    category = get_category(data, internalname)
    priority = get_priority(category)

    data["category"] = category
    data["priority"] = priority

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if path.read_text(encoding="utf-8") != out:
        path.write_text(out, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not ITEMS_DIR.is_dir():
        print(f"Items dir not found: {ITEMS_DIR}", file=sys.stderr)
        sys.exit(1)
    changed = 0
    for path in sorted(ITEMS_DIR.glob("*.json")):
        if inject_one(path):
            changed += 1
    print(f"Injected categories: {changed} files updated.")


if __name__ == "__main__":
    main()
