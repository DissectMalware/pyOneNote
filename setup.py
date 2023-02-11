from pyOneNote import __version__
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

project_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(project_dir, 'README.md')) as f:
    long_description = f.read()

entry_points = {
    'console_scripts': [
        'pyonenote=pyOneNote.Main:main',
    ],
}

setup(
    name="pyOneNote",
    version=__version__,
    author="Amirreza Niakanlahiji",
    author_email="aniakan+pyonenote@gmail.com",
    description=(
        "pyOneNote is a lightweight python library to read OneNote files."
        " The main goal of this parser is to allow cybersecurity analyst to extract useful information,"
        " such as embedded files, from OneNote files."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DissectMalware/pyOneNote",
    packages=["pyOneNote"],
    entry_points=entry_points,
    license='Apache License 2.0',
    python_requires='>=3.4',
    install_requires=[
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
