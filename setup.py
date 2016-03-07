# -*- coding: utf-8 -*-


"""setup.py: setuptools control."""


import re
from setuptools.command.test import test as TestCommand
from setuptools import setup


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        pytest.main(self.test_args)


version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('commit_coverage/__init__.py').read(),
    re.M
    ).group(1)


with open("README.md", "rb") as f:
    long_descr = f.read()


setup(
    name="commit-coverage",
    packages=["commit_coverage"],
    entry_points={
        "console_scripts": ['commit_coverage = commit_coverage:main']
        },
    version=version,
    description="Reports on (previously run) coverage results for a commit.",
    long_description=long_descr,
    author="Paul Michali",
    author_email="pc@michali.net",
    url="https://github.com/pmichali/commit-coverage",
    license="Apache Software License",
    platforms='any',
    tests_require=['pytest', 'mock'],
    cmdclass={'tests': PyTest},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],)
