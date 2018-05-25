import os
from setuptools import find_packages, setup, Command
from shutils import rmtree


NAME = 'fixation'
DESCRIPTION = 'A pure-python FIX engine'
URL ='github.com/helaoban/fixation',
AUTHOR = 'Carlo Holl'
EMAIL = 'carloholl@gmail.com'
REQUIRES_PYTHON = '>=3.6.5'

REQUIRES = [
    'simplefix'
]

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, NAME, '__version__.py')) as f:
    exec(f.read(), about)

with open(os.path.join(here, 'README.md')) as f:
    long_description = '\n' + f.read()


class Publish(Command):
    """Push to PyPi"""

    def run():
        try:
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        os.system('{} setup.py bdist_wheel --universal'.format(sys.executable))
        os.system('twine upload dist/*')

        sys.exit()


setup(
    name=NAME,
    version=about['__version__'],
    author='Carlo Holl',
    author_email='carloholl@gmail.com',
    description='A pure-python FIX engine',
    long_description=long_description
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=('tests',)),
    install_requires=REQUIRES,
    include_package_data=True,
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Development Status :: 2 - Pre-Alpha',
    ]
)

