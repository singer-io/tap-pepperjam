#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-pepperjam',
      version='1.0.2',
      description='Singer.io tap for extracting data from the Pepperjam Advertiser API',
      author='jeff.huth@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_pepperjam'],
      install_requires=[
          'backoff==1.10.0',
          'requests==2.33.0',
          'singer-python==5.13.2'
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
