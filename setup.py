#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-pepperjam',
      version='2.0.0',
      description='Singer.io tap for extracting data from the Pepperjam Advertiser API',
      author='jeff.huth@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_pepperjam'],
      install_requires=[
          'backoff==2.2.1',
          'requests==2.33.1',
          'singer-python==6.8.0'
      ],
      entry_points='''
          [console_scripts]
          tap-pepperjam=tap_pepperjam:main
      ''',
      packages=find_packages(),
      package_data={
          'tap_pepperjam': [
              'schemas/*.json'
          ]
      })
