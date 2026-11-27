# mabos-updates

What MabOS machines check for updates. Public, so machines need no token; it holds data only,
never commands.

## MabOS's programs

MabOS's own programs (Helium, Telegram, freshGram, Vesktop, Discord, Spotify, Claude Code,
Millennium) float: each is updated on its own, apart from MabOS's releases, while MabOS's system
components (niri, Quickshell, Strata, the terminals, the themes) come only with MabOS's releases.

`apps/<branch>.json` lists, per nixpkgs branch MabOS runs on (`26.05`), every program's versions,
the newest first:

```json
{
  "format": 1, "branch": "26.05", "serial": 12, "updated": "2026-11-27",
  "apps": {
    "telegram": {
      "name": "Telegram",
      "versions": [
        { "version": "6.3.4", "source": "nixpkgs", "attr": "telegram-desktop",
          "rev": "<nixpkgs commit>", "narHash": "sha256-…", "date": "2026-11-27" }
      ]
    }
  }
}
```

- `source` `nixpkgs`: the attribute of nixpkgs at `rev` (a nixos-unstable commit whose build of it
  is in cache.nixos.org; unfree programs, which it never builds, repackage their makers' builds).
- `source` `mabos-packages`: the package of [mabos-packages](https://github.com/mabasterYT/mabos-packages)
  at `rev`, a commit built into MabOS's cache for that branch.
- `rev` and `narHash` make each a fixed, checked download. The last 15 versions stay, so a machine
  can go back to any of them. `serial` grows with every change.

`.github/workflows/apps.yml` runs `scripts/update-apps.py` every six hours, by hand, and when
mabos-packages finishes a build. On a machine, `mabos-system` reads this file: Settings › MabOS ›
MabOS's programs (update, auto-update, go back to a version).

## Later

MabOS's own releases and channels (Stable, release candidates, Beta), as `channels.json` and
`releases/`, signed.
