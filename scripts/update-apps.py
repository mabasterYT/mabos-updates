#!/usr/bin/env python3
"""Moves MabOS's programs to their newest versions in apps/<branch>.json.

MabOS's programs float: each is offered on its own, apart from MabOS's releases. For every program
this finds the newest build machines can download and, when its version is new, puts it first in
the program's list (older entries stay, for rolling back):

- "nixpkgs" programs (plain nixpkgs packages): the newest nixos-unstable whose build of the
  program is in cache.nixos.org (unfree ones, which it never builds, as soon as the snapshot has
  them: they only repackage their makers' builds);
- "mabos-packages" programs: the newest commit of mabasterYT/mabos-packages its workflow marked as
  built into MabOS's cache (built for this branch's nixpkgs, as Millennium must be).

Each entry: {version, source, attr, rev, narHash, date}; a machine takes the attribute from that
exact revision (rev and narHash make it a fixed, checked download).

  update-apps.py <branch>        e.g. 26.05; writes apps/26.05.json, prints what changed
"""
import datetime
import json
import os
import subprocess
import sys

KEEP = 15  # versions kept per program, the newest first
SYSTEM = "x86_64-linux"

# MabOS's programs: the name a machine knows them by (its apps.json), how Settings shows them,
# where they come from and their attribute there
APPS = {
    "helium": {"name": "Helium", "source": "mabos-packages", "attr": "helium"},
    "telegram": {"name": "Telegram", "source": "nixpkgs", "attr": "telegram-desktop"},
    "freshgram": {"name": "freshGram", "source": "mabos-packages", "attr": "freshgram"},
    "vesktop": {"name": "Vesktop", "source": "nixpkgs", "attr": "vesktop"},
    "discord": {"name": "Discord", "source": "nixpkgs", "attr": "discord"},
    "spotify": {"name": "Spotify", "source": "nixpkgs", "attr": "spotify"},
    "claude-code": {"name": "Claude Code", "source": "nixpkgs", "attr": "claude-code"},
    "millennium": {"name": "Millennium", "source": "mabos-packages", "attr": "millennium"},
}


def run(*command, check=True):
    done = subprocess.run(command, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])}…: {done.stderr.strip()[-400:]}")
    return done.stdout.strip() if done.returncode == 0 else None


def nar_hash(flake_ref):
    return json.loads(run("nix", "flake", "prefetch", "--json", flake_ref))["hash"]


def nixpkgs_snapshot():
    rev = run("git", "ls-remote", "https://github.com/NixOS/nixpkgs", "refs/heads/nixos-unstable").split()[0]
    return rev, nar_hash(f"github:NixOS/nixpkgs/{rev}")


def nixpkgs_eval(rev, narhash, attr, field):
    expr = (f'(import (builtins.fetchTree {{ type = "github"; owner = "NixOS"; repo = "nixpkgs"; '
            f'rev = "{rev}"; narHash = "{narhash}"; }}) {{ system = "{SYSTEM}"; config.allowUnfree = true; }})'
            f'.{attr}.{field}')
    return run("nix", "eval", "--raw", "--expr", expr)


def cached(out_path):
    return run("nix", "path-info", "--store", "https://cache.nixos.org", out_path, check=False) is not None


def unfree(rev, narhash, attr):
    expr = (f'let p = import (builtins.fetchTree {{ type = "github"; owner = "NixOS"; repo = "nixpkgs"; '
            f'rev = "{rev}"; narHash = "{narhash}"; }}) {{ system = "{SYSTEM}"; config.allowUnfree = true; }}; '
            f'in if p.{attr}.meta.unfree or false then "yes" else "no"')
    return run("nix", "eval", "--raw", "--expr", expr) == "yes"


def mabos_packages_built():
    """The newest commit of mabos-packages its workflow built into the cache (a built-<sha> mark)."""
    names = run("gh", "release", "view", "cache", "-R", "mabasterYT/mabos-packages",
                "--json", "assets", "--jq", ".assets[].name").split()
    marks = [name[len("built-"):] for name in names if name.startswith("built-")]
    if not marks:
        return None
    rev = marks[0]
    return rev, nar_hash(f"github:mabasterYT/mabos-packages/{rev}")


def main():
    branch = sys.argv[1]
    path = os.path.join("apps", f"{branch}.json")
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"format": 1, "branch": branch, "serial": 0, "apps": {}}

    today = datetime.date.today().isoformat()
    snapshot = nixpkgs_snapshot()
    built = mabos_packages_built()
    changes = []
    for app, info in APPS.items():
        entry = data["apps"].setdefault(app, {"versions": []})
        entry["name"] = info["name"]
        try:
            if info["source"] == "nixpkgs":
                rev, narhash = snapshot
                version = nixpkgs_eval(rev, narhash, info["attr"], "version")
                if not unfree(rev, narhash, info["attr"]) and not cached(nixpkgs_eval(rev, narhash, info["attr"], "outPath")):
                    print(f"{app}: {version} not built by cache.nixos.org yet")
                    continue
            else:
                if built is None:
                    continue
                rev, narhash = built
                # Not every package has `version` (Millennium's doesn't): then its name's
                version = run("nix", "eval", "--raw",
                              f"github:mabasterYT/mabos-packages/{rev}#packages.{SYSTEM}.{info['attr']}",
                              "--apply", "p: p.version or (builtins.parseDrvName p.name).version")
        except RuntimeError as error:
            print(f"{app}: skipped ({error})")
            continue
        newest = entry["versions"][0] if entry["versions"] else None
        if newest and newest["version"] == version:
            continue
        entry["versions"] = ([{"version": version, "source": info["source"], "attr": info["attr"],
                               "rev": rev, "narHash": narhash, "date": today}]
                             + [v for v in entry["versions"] if v["version"] != version])[:KEEP]
        changes.append(f"{info['name']} {version}")

    if changes:
        data["serial"] += 1
        data["updated"] = today
        os.makedirs("apps", exist_ok=True)
        with open(path + ".new", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(path + ".new", path)
    print("; ".join(changes) if changes else "no new versions")


if __name__ == "__main__":
    main()
