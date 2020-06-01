from setuptools import setup,find_packages
import os

setup(name='openbte',
      version='1.10',
      description='Boltzmann Transport Equation for Phonons',
      author='Giuseppe Romano',
      author_email='romanog@mit.edu',
      classifiers=['Programming Language :: Python :: 3.6'],
      #long_description=open('README.rst').read(),
      install_requires=['shapely',
                        'pyvtk',
                        'googledrivedownloader',
                        'unittest2',
                        'nbsphinx',
                        'future',
                        'termcolor',
                        'alabaster',
                        'deepdish',
                        'dash',
                        'mpi4py',
                        'plotly==4.6.0',
                        'scikit-umfpack',
                        'nbsphinx',
                        'recommonmark',
                        'sphinx>=1.4.6',
                        'sphinx_rtd_theme'
                         ],
      license='GPLv2',\
      packages = ['openbte'],
      package_data = {'openbte':['materials/*.dat','fonts/*.ttf']},
      entry_points = {
     'console_scripts': ['AlmaBTE2OpenBTE=openbte.almabte2openbte:main','Phono3py2OpenBTE=openbte.phono3py:main'],
      },
      zip_safe=False)
