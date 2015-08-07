import sys
import pkg_resources
from cx_Freeze import setup, Executable
from subprocess import call
import os
import sys
import random

setup(name='coinbend',
    version='0.1',
    description='An open-source, peer-to-peer, multi-currency, altcoin exchange.',
    url='http://github.com/robertsdotpm/coinbend',
    author='Matthew Roberts',
    author_email='matthew@roberts.pm',
    license='pending licensing',
    packages=['coinbend'],
    install_requires=[
        'oursql',
        'scrypt',
        'pyaudio',
        'colorama',
        'bitcoin'
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False,
    executables = [Executable("main.py", base = "Win32GUI", targetName="coinbend")]
)


