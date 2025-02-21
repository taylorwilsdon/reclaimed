from setuptools import setup, find_packages

setup(
    name="disk_scanner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "rich",
    ],
    entry_points={
        'console_scripts': [
            'disk-scanner=disk_scanner.cli:main',
        ],
    },
)
