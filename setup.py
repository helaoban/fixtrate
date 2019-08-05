import os
from setuptools import find_packages, setup, Command
from shutil import rmtree
import sys

NAME = 'fixtrate'
DESCRIPTION = 'Tools for interacting with the FIX protocol'
URL = 'github.com/helaoban/fixtrate',
AUTHOR = 'Carlo Holl'
EMAIL = 'carloholl@gmail.com'
REQUIRES_PYTHON = '>=3.6.5'

REQUIRES = [
    'aenum>=2.1.2',
    'async-timeout>=2.0',
    'aioredis>=1.1.0',
    'simplefix>=1.0.12',
    'untangle>=1.1.1',
    'python-dateutil>=2.6.1'
]

EXTRAS_REQUIRE = {
    'test': [
        'pytest',
        'pytest-asyncio'
    ]
}

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, NAME, '__version__.py')) as f:
    exec(f.read(), about)

with open(os.path.join(here, 'README.rst')) as f:
    long_description = '\n' + f.read()


class Publish(Command):
    """Push to PyPi"""

    description = 'Build and publish package to PyPI.'
    user_options = [
        ('test', 't', 'Publish to test.pypi.org'),
    ]
    test_url = 'https://test.pypi.org/legacy/'

    def initialize_options(self):
        self.test = False

    def finalize_options(self):
        pass

    def run(self):
        try:
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        os.system('{} setup.py bdist_wheel --universal'.format(sys.executable))
        os.system('twine upload {}dist/*'.format(
            '--repository-url {} '.format(self.test_url)
            if self.test else ''),
        )
        sys.exit()


setup(
    name=NAME,
    version=about['__version__'],
    author=AUTHOR,
    author_email=EMAIL,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    packages=find_packages(exclude=('tests',)),
    install_requires=REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    include_package_data=True,
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Development Status :: 2 - Pre-Alpha',
    ],
    cmdclass={
        'publish': Publish,
    },
)
