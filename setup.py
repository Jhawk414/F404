import re
import sys

from setuptools import setup

__version__ = re.findall(
    r"""__version__ = ["']+([0-9\.\-dev]*)["']+""",
    open('pycycle/__init__.py').read(),
)[0]

# optional dependencies, by category (currently just 'test')
optional_dependencies = {
    'test': [
        # testflo/parameterized drive the vendored pycycle/ suite upstream;
        # pytest drives the F404 suite under tests/ (pythonpath ini needs 7+).
        'testflo>=1.3.6',
        'parameterized',
        'pytest>=7.0',
        'pytest-cov',
    ]
}

# Add an optional dependency that concatenates all others
optional_dependencies['all'] = sorted([
    dependency
    for dependencies in optional_dependencies.values()
    for dependency in dependencies
])

setup(name='om-pycycle',
      version=__version__,
      description="pyCycle -- Thermodynamic Cycle modeling library",
      long_description="""pyCycle is an open-source library for modeling of turbine based propulsion and power generation systems.
      It is a modular library, allowing you to build up a turbine based system from basic blocks like `inlet`, `compressor`, `turbine`, and `nozzle`. 
      """,

      packages=[
          # F404 application code (src/ layout). Shares this distribution with
          # the vendored library rather than carrying a second setup.py, so a
          # single `pip install -e .` covers the whole repo.
          'F404_pycycle',
          'pycycle',
          'pycycle.elements',
          'pycycle.elements.test',
          'pycycle.maps',
          'pycycle.maps.test',
          'pycycle.thermo',
          'pycycle.thermo.cea',
          'pycycle.thermo.cea.test',
          'pycycle.thermo.cea.thermo_data',
          'pycycle.thermo.tabular',
          'pycycle.thermo.tabular.test',
          'pycycle.thermo.test',
          'pycycle.tests',
      ],
      install_requires=[
        'openmdao>=3.10.0',
        # numpy arrives transitively via openmdao, but F404_pycycle imports it
        # directly, so it is declared rather than relied on.
        'numpy',
        # F404_pycycle only: SweepRunner collects results into a DataFrame and
        # write_deck_csv serialises the cycle deck from it.
        'pandas',
      ],
    package_dir={'F404_pycycle': 'src/F404_pycycle'},
    package_data={
        'pycycle.elements.test': ['reg_data/*.csv'],
        'pycycle.thermo.test': ['*.csv'],
        'pycycle.thermo.tabular': ['*.pkl'],
    },
    extras_require=optional_dependencies,
)
