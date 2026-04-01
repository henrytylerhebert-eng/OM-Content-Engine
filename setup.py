"""Legacy setuptools shim for older pip editable installs."""

from setuptools import find_packages, setup


setup(
    name="om-content-engine",
    version="0.1.0",
    description="Read-optimized ecosystem intelligence layer for Opportunity Machine.",
    packages=find_packages(),
    install_requires=["sqlmodel>=0.0.22"],
    extras_require={"dev": ["pytest>=8.0"]},
)
