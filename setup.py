from setuptools import setup, find_packages

setup(
    name='dyntamic',
    version='0.0.2',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)