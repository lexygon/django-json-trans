import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-json-trans',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description="A lean approach to model translations for Django with Postgresql's lovely JSONBField",
    long_description=README,
    url='github.com/lexygon',
    author='Ruzgar Burak Topal',
    author_email='hello@ruzgar.me',
    classifiers=[],
    install_requires=['django']
)
