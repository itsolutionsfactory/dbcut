#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals, print_function
import os
import re

from io import open
import datetime
import subprocess

from argparse import RawTextHelpFormatter, ArgumentParser, FileType


def generate_changelog_title(version):
    version_title = "Version %s" % version
    return version_title + "\n" + "-" * len(version_title)


def get_release_date():
    dt = datetime.date.today()
    if 4 <= dt.day <= 20 or 24 <= dt.day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][dt.day % 10 - 1]
    return dt.strftime("%%B %%d%s %%Y" % suffix)


def bump_release_version(args):
    """Automated software release workflow

  * Bumps the release version number (with .bumpversion.cfg)
  * Preloads the correct changelog template for editing
  * Builds a source distribution
  * Sets release date
  * Tags the release

You can run it like::

    $ python bumpversion.py

which will create a 'release' version (Eg. 0.7.2-dev => 0.7.2).

    """
    # Dry run 'bumpversion' to find out what the new version number
    # would be. Useful side effect: exits if the working directory is not
    # clean.
    changelog = args.changelog.name
    bumpver = subprocess.check_output(
        ['bumpversion', 'release', '--dry-run', '--verbose'],
        stderr=subprocess.STDOUT)
    m = re.search(r'Parsing version \'(\d+\.\d+\.\d+)\.dev0\'', bumpver)
    current_version = m.groups(0)[0] + ".dev0"
    m = re.search(r'New version will be \'(\d+\.\d+\.\d+)\'', bumpver)
    release_version = m.groups(0)[0]

    date = get_release_date()

    current_version_title = generate_changelog_title(current_version)
    release_version_title = generate_changelog_title(release_version)
    changes = ""
    with open(changelog) as fd:
        changes += fd.read()

    changes = changes.replace(current_version_title, release_version_title)\
                     .replace("**unreleased**", "Released on %s" % date)

    with open(changelog, "w") as fd:
            fd.write(changes)

    # Tries to load the EDITOR environment variable, else falls back to vim
    editor = os.environ.get('EDITOR', 'vim')
    os.system("{} {}".format(editor, changelog))

    subprocess.check_output(['python', 'setup.py', 'sdist'])

    # Have to add it so it will be part of the commit
    subprocess.check_output(['git', 'add', changelog])
    subprocess.check_output(
        ['git', 'commit', '-m', 'Changelog for {}'.format(release_version)])

    # Really run bumpver to set the new release and tag
    bv_args = ['bumpversion', 'release']

    bv_args += ['--new-version', release_version]

    subprocess.check_output(bv_args)


def bump_new_version(args):
    """Increment the version number to the next development version

  * Bumps the development version number (with .bumpversion.cfg)
  * Preloads the correct changelog template for editing

You can run it like::

    $ python bumpversion.py newversion

which, by default, will create a 'patch' dev version (0.0.1 => 0.0.2-dev).

You can also specify a patch level (patch, minor, major) to change to::

    $ python bumpversion.py newversion major

which will create a 'major' release (0.0.2 => 1.0.0-dev)."""
    pass
    # Dry run 'bumpversion' to find out what the new version number
    # would be. Useful side effect: exits if the working directory is not
    # clean.
    changelog = args.changelog.name
    part = args.part
    bumpver = subprocess.check_output(
        ['bumpversion', part, '--dry-run', '--verbose'],
        stderr=subprocess.STDOUT)
    m = re.search(r'Parsing version \'(\d+\.\d+\.\d+)\'', bumpver)
    current_version = m.groups(0)[0]
    m = re.search(r'New version will be \'(\d+\.\d+\.\d+)\.dev0\'', bumpver)
    next_version = m.groups(0)[0] + ".dev0"

    current_version_title = generate_changelog_title(current_version)
    next_version_title = generate_changelog_title(next_version)

    next_release_template = "%s\n\n**unreleased**\n\n" % next_version_title

    changes = ""
    with open(changelog) as fd:
        changes += fd.read()

    changes = changes.replace(current_version_title,
                              next_release_template + current_version_title)

    with open(changelog, "w") as fd:
            fd.write(changes)

    # Tries to load the EDITOR environment variable, else falls back to vim
    editor = os.environ.get('EDITOR', 'vim')
    os.system("{} {}".format(editor, changelog))

    subprocess.check_output(['python', 'setup.py', 'sdist'])

    # Have to add it so it will be part of the commit
    subprocess.check_output(['git', 'add', changelog])
    subprocess.check_output(
        ['git', 'commit', '-m', 'Changelog for {}'.format(next_version)])

    # Really run bumpver to set the new release and tag
    bv_args = ['bumpversion', part, '--no-tag', '--new-version', next_version]

    subprocess.check_output(bv_args)


def main():
    '''Parse command-line arguments and execute bumpversion command.'''

    parser = ArgumentParser(prog='bumpversion',
                            description='Bumpversion wrapper')

    default_changelog = os.path.join(os.getcwd(), 'CHANGES.rst')

    subparsers = parser.add_subparsers(title='bumpversion wrapper commands')
    # release command
    release_doc = bump_release_version.__doc__
    subparser = subparsers.add_parser("release",
                                      description=release_doc,
                                      formatter_class=RawTextHelpFormatter)
    subparser.add_argument('--changelog', help='Project changelog',
                           type=FileType(),
                           default=default_changelog)
    subparser.set_defaults(func=bump_release_version)
    # newversion command
    newversion_doc = bump_new_version.__doc__
    subparser = subparsers.add_parser("newversion",
                                      description=newversion_doc,
                                      formatter_class=RawTextHelpFormatter)
    subparser.add_argument('--changelog', help='Project changelog',
                           type=FileType(),
                           default=default_changelog)
    subparser.add_argument('part', help='Part of the version to be bumped',
                           choices=['patch', 'minor', 'major'])
    subparser.set_defaults(func=bump_new_version)
    # Parse argv arguments
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
