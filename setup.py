#!/usr/bin/env python3
"""
setup.py for chionecast.
"""

from setuptools import setup

setup(
    name="chionecast",
    version="1.0.0",
    description="Native Linux driver, telemetry monitor, and display tool for the GAMDIAS CHIONE P3 AIO liquid cooler",
    author="Dhyanesh Damania",
    url="https://github.com/dhyanesh/chionecast",
    license="MIT",
    py_modules=["chione_device", "display_renderer", "system_stats", "chione_cli"],
    install_requires=[
        "pillow>=10.0.0",
        "psutil>=5.9.0",
        "nvidia-ml-py>=12.0.0",
        "hidapi>=0.14.0",
    ],
    entry_points={
        "console_scripts": [
            "chionecast=chione_cli:main",
        ],
    },
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
)
