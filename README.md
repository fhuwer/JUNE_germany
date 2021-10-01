# JUNE Germany: open-source individual-based epidemiology simulation

This is the repository of the JUNE Germany project. It is based on version 1 of the JUNE project by the IDAS-Durham group [see JUNE](https://github.com/IDAS-Durham/JUNE) with minor changes to work for Germany.

# Dataset
Due to licenses the dataset is not shared publicly. If you are interested in receiving a copy of
the dataset, please contact Friedemann Neuhaus (<fneuhaus@cern.ch>) and Matthias Schott
(<mschott@cern.ch>).

# Setup
To install JUNE Germany, clone the repository and install it using
```
pip install -e .
```

This should be done in a virtual environment.
It will require a working installation of OpenMPI or IntelMPI to compile ``mpi4py``. 

We tested everything with python3.8 only!

# How to use the code
In ``Notebooks/quickstart.ipynb`` a small introduction is given on how JUNE Germany works. It is
mostly the same as in the original JUNE project.

# Tests
Run the tests with

```
cd test_june
pytest
```

# Thanks
We would like to thank the original authors of the JUNE project for laying the groundwork of this
project and their support for adapting it to Germany.
