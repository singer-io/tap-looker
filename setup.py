#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-looker',
      version='0.1.1',
      description='Singer.io tap for extracting data/metadata from the Looker API',
      author='jeff.huth@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_looker'],
      install_requires=[
          'backoff==1.10.0',
          'requests==2.32.5',
          'singer-python==5.14.3'
      ],
      extras_require={
          'dev': [
              'pylint'
          ]
      },
      entry_points='''
          [console_scripts]
          tap-looker=tap_looker:main
      ''',
      packages=find_packages(),
      package_data={
          'tap_looker': [
              'schemas/*.json'
          ]
      })
