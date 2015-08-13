import sys
import pkg_resources
from cx_Freeze import setup, Executable
from subprocess import call
import os
import sys
import random
import os

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
target_name = "coinbend"
if sys.platform == "win32":
    base = "Console"
    target_name = "coinbend.exe"



# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["coinbend", "zope.interface"], "includes": ["os", "oursql", "colorama", "bitcoin", "spydht", "zope.interface", "pkg_resources", "netifaces", "cherrypy", "cherrypy.wsgiserver", "cherrypy.wsgiserver.wsgiserver3"], "excludes": ["tkinter"], 'namespace_packages': ['zope'], 'copy_dependent_files': True, 'include_msvcr': True}


setup(name='coinbend',
    version='0.1',
    description='An open-source, peer-to-peer, multi-currency, altcoin exchange.',
    url='http://github.com/robertsdotpm/coinbend',
    author='Matthew Roberts',
    author_email='matthew@roberts.pm',
    license='',
    options = {"build_exe": build_exe_options},
    executables = [Executable("import_coinbend.py", base = base, targetName=target_name)]
)





