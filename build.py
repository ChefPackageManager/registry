#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, AnyStr

import requests

CHEF_HOME = Path.home() / ".chef-package-manager"


@dataclass
class PackageScript:
    build: Path


@dataclass
class Package:
    name: str
    path: Path
    version: str
    url: str
    sha256: str
    script: PackageScript


@dataclass
class Registry:
    path: Path

    def packages(self) -> List[Package]:
        packages = [
            Package(
                path.name,
                path,
                # we add these in the next statement.
                version="",
                url="",
                sha256="",
                script=PackageScript(path / "build.sh"),
            )
            for path in self.path.glob("packages/*/")
        ]

        # add data from the manifest.json file
        for package in packages:
            with open(str(package.path / "manifest.json"), "r") as f:
                metadata = json.load(f)

                package.version = metadata["version"]
                package.url = metadata["url"].format(version=package.version)
                package.sha256 = metadata["sha256"]

        return packages


def create_arg_parser() -> ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Build a Chef registry & compress resulting binaries",
    )

    parser.add_argument(
        "--registry", help="path to the registry to build from", required=True
    )

    return parser


def sh(args: List[str], cwd: Path, env: dict[AnyStr, AnyStr] | None = None) -> None:
    subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def bootstrap() -> None:
    if not CHEF_HOME.exists():
        CHEF_HOME.mkdir()

    for subpath in ["tmp", "installed", "dist"]:
        if not (CHEF_HOME / subpath).exists():
            (CHEF_HOME / subpath).mkdir()


def cleanup() -> None:
    shutil.rmtree(str(CHEF_HOME))


def verify(path: Path, checksum: str) -> bool:
    hasher = hashlib.sha256()

    with open(path, "rb") as f:
        hasher.update(f.read())

    return hasher.hexdigest() == checksum


def download(package: Package) -> Path:
    r = requests.get(package.url)

    try:
        r.raise_for_status()
    except Exception as e:
        raise e

    filename = package.url.split("/")[-1]
    path = CHEF_HOME / "tmp" / filename

    with open(str(path), "wb") as f:
        f.write(r.content)

    if not verify(path, package.sha256):
        raise ValueError("Failed to verify the integrity of the downloaded file!")

    return path


def unpack(path: Path) -> Path:
    if "".join(path.suffixes) == ".tar.gz" or path.suffix == ".tgz":
        with tarfile.open(str(path), "r:gz") as tar:
            extracted_dirname = tar.getnames()[0]
            tar.extractall(path=path.parent, filter="data")

        return path.parent / extracted_dirname

    raise ValueError("Bad archive to unpack!")


def build(package: Package, unpacked: Path) -> Path:
    env = os.environ.copy()
    env["PACKAGE_NAME"] = package.name
    env["CHEF_HOME"] = str(CHEF_HOME)
    env["OS"] = "LINUX" if platform.system() == "Linux" else "MACOS"

    # yes, I know I can use chmod with pure Python, but this solution is less complicated.
    sh(["chmod", "+x", str(package.script.build)], cwd=CHEF_HOME)
    sh([str(package.script.build)], cwd=unpacked, env=env)

    return CHEF_HOME / "bin" / package.name


def pack(source: Path, destination: Path) -> None:
    # creating tar files in pure Python is unnecessarily complicated.
    sh(["tar", "-czf", str(destination), str(source)], cwd=CHEF_HOME)


def main() -> None:
    if CHEF_HOME.exists():
        cleanup()
    bootstrap()

    parsed = create_arg_parser().parse_args()

    registry = Registry(path=Path(parsed.registry).absolute())
    packages = registry.packages()

    print(f"System: {platform.system()} {platform.machine()}")
    for package in packages:
        print(f"==> Downloading '{package.name}'")
        saved = download(package)
        print(f"==> Unpacking '{package.name}'...")
        unpacked = unpack(saved)
        print(f"==> Building '{package.name}'")
        built = build(package, unpacked)
        print(f"==> Packing '{package.name}'")
        pack(built, CHEF_HOME / "dist" / f"{package.name}-{package.version}.tgz")
        print(f"==> Finished building '{package.name}'")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"==> FATAL: {e}")
        cleanup()
