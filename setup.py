#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
try:
    from setuptools import (
        Command,
        setup,
    )
except ImportError:
    from distutils.core import (
        Command,
        setup,
    )

try:
    from semantic_release import setup_hook
    setup_hook(sys.argv)
except ImportError:
    pass


class NoVersionSet(Exception):
    pass


class PyTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pexpect
        print(
            "To see output, run tests via py.test directly. "
            "This will fail on a headless setup."
        )
        output, errno = pexpect.run(' '.join([
            sys.executable,
            'runtests.py',
            # Since CircleCI puts the venv in the source tree:
            '--ignore', 'venv',
            '-s',
        ]), withexitstatus=True)
        print(output.decode('utf-8'))
        raise SystemExit(errno)


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'wheel==0.24.0',
]

test_requirements = [
    'py==1.4.26',
    'pytest==2.7.0',
    'pexpect==3.3',
]

setup(
    name='hexes',
    version='0.4.0',
    description="Curses for humans.",
    long_description=readme + '\n\n' + history,
    author="Kit La Touche",
    author_email='kit@transneptune.net',
    url='https://github.com/wlonk/hexes',
    packages=[
        'hexes',
    ],
    package_dir={'hexes':
                 'hexes'},
    scripts=(
        'scripts/hexes_example',
    ),
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='hexes',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Environment :: Console',
        'Environment :: Console :: Curses',

    ],
    cmdclass={'test': PyTest},
    test_suite='tests',
    tests_require=test_requirements,
)
