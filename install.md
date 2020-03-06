---
layout: default
title: Install
permalink: /install/
description: Install manual
---


##Anaconda

The easiest way to install OpenBTE on Linux/MacOS/Windows is through Anaconda:

1) Install Anaconda 3
2) On Anaconda Prompt type:

.. code-block:: shell

  conda create -n openbte python=3.6
  activate openbte
  conda install -c conda-forge -c gromano openbte
  
  
For Windows you will have to install MSMPI

If you want to avoid installing Anaconda, you can still use the pip system (see below)


## Linux

Requirements:

apt-get install -y libopenmpi-dev 

pip install --upgrade openbte     

Note that some users report that Gmsh does not work properly if installed via the package manager and launched in parallel. If you have trouble, install Gmsh via command line

.. code-block:: shell

  wget http://geuz.org/gmsh/bin/Linux/gmsh-3.0.0-Linux64.tgz
  tar -xzf gmsh-3.0.0-Linux64.tgz
  cp gmsh-3.0.0-Linux/bin/gmsh /usr/bin/
  rm -rf gmsh-3.0.0-Linux
  rm gmsh-3.0.0-Linux64.tgz


## MacOS

You will have to install gmsh from source, then type

.. code-block:: shell

  pip install --no-cache-dir --upgrade openbte 