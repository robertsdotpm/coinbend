#!/usr/bin/env python

from setuptools import setup, find_packages
import spydht

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name="spydht",
    version=spydht.__version__,
    description='Python DHT with signed messages',
    long_description=readme,
    author='Isaac Zafuta, kohlrabi',
    url='https://github.com/kohlrabi23/spydht',
    license=license,
    packages=find_packages(exclude=('tests','docs'))
)
