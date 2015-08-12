from setuptools import setup, find_packages


setup(
    version='0.1',
    description='An open-source, peer-to-peer, multi-currency, altcoin exchange.',
    url='http://github.com/robertsdotpm/coinbend',
    author='Matthew Roberts',
    author_email='matthew@roberts.pm',
    license='pending licensing',
    packages=find_packages(exclude=('tests','docs'))
)


