#!/usr/bin/env python3
"""
Setup script for MCP MindMup Google Drive server.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mcp-mindmup2-google-drive",
    version="0.1.0",
    author="taurus5650",
    author_email="taurus_5650@hotmail.com",
    description="MCP server for integrating MindMup files with Google Drive",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.13",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mcp-mindmup2-google-drive=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
)