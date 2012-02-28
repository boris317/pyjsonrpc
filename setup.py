from setuptools import setup, find_packages
import sys, os

version = '0.0.1'

setup(name='pyjsonrpc',
      version=version,
      description="json rpc clien and server for python.",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Shawn Adams',
      author_email='boris317@gmail.com',
      url='',
      license='GNU',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "simplejson",
          "webob"
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
