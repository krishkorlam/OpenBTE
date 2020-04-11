from setuptools import setup,find_packages
import os

setup(name='openbte',
      version='0.9.89',
      description='Boltzmann Transport Equation for Phonons',
      author='Giuseppe Romano',
      author_email='romanog@mit.edu',
      classifiers=['Programming Language :: Python :: 3.6'],
      #long_description=open('README.rst').read(),
      install_requires=['numpy',
                        'scipy',
                        'sparse',
                        'shapely',
                        'networkx',
                        'pyvtk',
                        'googledrivedownloader',
                        'unittest2',
                        'nbsphinx',
                        'ipython',
                        'future',
                        'termcolor',
                        'alabaster',
                        'deepdish',
                        'mpi4py',
                        'matplotlib',
                         ],
      license='GPLv2',\
      packages = ['openbte'],
      package_data = {'openbte':['materials/*.dat','fonts/*.ttf']},
      entry_points = {
     'console_scripts': ['AlmaBTE2OpenBTE=openbte.almabte2openbte:main'],
      },
      zip_safe=False)
