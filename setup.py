from setuptools import setup, find_packages

setup(
    name="madd_xp_cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "simple-salesforce",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "mxp=madd_xp.cli:main",
        ]
    },
)