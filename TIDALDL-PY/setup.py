import re
from pathlib import Path

from setuptools import setup, find_packages


def read_version() -> str:
    version_file = Path(__file__).parent / "tidal_dl" / "printf.py"
    match = re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]", version_file.read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError("Unable to find VERSION in tidal_dl/printf.py")
    return match.group(1)

setup(
    name='tidal-dl',
    version=read_version(),
    license="Apache2",
    description="Tidal Music Downloader.",

    author='YaronH',
    author_email="yaronhuang@foxmail.com",

    packages=find_packages(exclude=['tidal_gui*']),
    include_package_data=False,
    platforms="any",
    install_requires=[
        "aigpy>=2022.7.8.1",
        "requests>=2.22.0",
        "pycryptodome",
        "pydub",
        "prettytable",
        "lxml",
        "Flask>=2.3.3",
    ],
    entry_points={'console_scripts': ['tidal-dl = tidal_dl:main', ]}
)
