#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT_SCHEMA_KEYS = [
    "Author",
    "Name",
    "InternalName",
    "AssemblyVersion",
    "Description",
    "ApplicableVersion",
    "Tags",
    "LoadRequiredState",
    "LoadSync",
    "CanUnloadAsync",
    "LoadPriority",
    "Punchline",
    "AcceptsFeedback",
    "IsHide",
    "IsTestingExclusive",
    "DownloadLinkInstall",
    "DownloadLinkTesting",
    "DownloadLinkUpdate",
    "ChangeLog",
]

DEFAULTS = {
    "Description": "",
    "ApplicableVersion": "any",
    "Tags": [],
    "LoadRequiredState": 0,
    "LoadSync": False,
    "CanUnloadAsync": False,
    "LoadPriority": 0,
    "Punchline": "",
    "AcceptsFeedback": True,
    "IsHide": False,
    "IsTestingExclusive": False,
    "ChangeLog": "",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def root_order(root_path):
    if not root_path.exists():
        return []

    root_plugins = load_json(root_path)
    return [
        plugin["InternalName"]
        for plugin in root_plugins
        if isinstance(plugin, dict) and plugin.get("InternalName")
    ]


def plugin_dirs(plugins_dir):
    return [path for path in plugins_dir.iterdir() if path.is_dir()]


def find_manifest(plugin_dir):
    expected = plugin_dir / f"{plugin_dir.name}.json"
    if expected.exists():
        return expected

    manifests = sorted(plugin_dir.glob("*.json"))
    if len(manifests) == 1:
        return manifests[0]

    if not manifests:
        raise FileNotFoundError(f"No manifest JSON found in {plugin_dir}")

    raise ValueError(
        f"Expected {expected.name} in {plugin_dir}, but found multiple JSON files"
    )


def build_entry(manifest, repository, branch):
    entry = {}

    for key in ROOT_SCHEMA_KEYS:
        if key == "ChangeLog":
            value = manifest.get("ChangeLog", manifest.get("Changelog", DEFAULTS[key]))
        elif key.startswith("DownloadLink"):
            internal_name = manifest["InternalName"]
            value = (
                f"https://github.com/{repository}/raw/{branch}/"
                f"plugins/{internal_name}/latest.zip"
            )
        else:
            value = manifest.get(key, DEFAULTS.get(key))

        entry[key] = value

    return entry


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild plugins.json from per-plugin manifests."
    )
    parser.add_argument("--repository", required=True, help="GitHub owner/repo value")
    parser.add_argument("--branch", default="main", help="Branch used in download URLs")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root)
    plugins_dir = root / "plugins"
    root_manifest = root / "plugins.json"

    manifests = {}
    for plugin_dir in plugin_dirs(plugins_dir):
        latest_zip = plugin_dir / "latest.zip"
        if not latest_zip.exists():
            raise FileNotFoundError(f"Missing {latest_zip}")

        manifest_path = find_manifest(plugin_dir)
        manifest = load_json(manifest_path)
        internal_name = manifest.get("InternalName")

        if not internal_name:
            raise ValueError(f"{manifest_path} is missing InternalName")
        if internal_name != plugin_dir.name:
            raise ValueError(
                f"{manifest_path} InternalName is {internal_name}, "
                f"but its folder is {plugin_dir.name}"
            )

        manifests[internal_name] = manifest

    existing_order = root_order(root_manifest)
    ordered_names = [
        name for name in existing_order if name in manifests
    ]
    ordered_names.extend(
        sorted(name for name in manifests if name not in existing_order)
    )

    plugins = [
        build_entry(manifests[name], args.repository, args.branch)
        for name in ordered_names
    ]

    root_manifest.write_text(
        json.dumps(plugins, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
