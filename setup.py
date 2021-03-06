# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}


setup(name='Ska.tdb',
      author='Tom Aldcroft',
      url="http://cxc.harvard.edu/mta/ASPECT/tool_doc/pydocs/Ska.tdb",
      description='Access to Chandra Telemetry Database (TDB)',
      author_email='taldcroft@cfa.harvard.edu',
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      packages=['Ska', 'Ska.tdb', 'Ska.tdb.tests'],
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
