#!/usr/bin/env python
#
# Copyright (c) 2016 Paul Michali, Cisco Systems Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# commit_coverage
#
# Indicates the coverage for diffs specified in the command. It assumes that
# coverage was run before using this tool (and report should be on what is
# in the repo currently).
#
# Usage:
#    commit_coverage.py [-h] [-c CONTEXT] [-w WHICH] repo-dir
# Where:
# -h, --help     Show this help message and exit.
# -c CONTEXT, --context CONTEXT
#                       Number of context lines around diff regions.
#                       Default=3.
# -w COMMITS, --which COMMITS
#                       Which commit(s) to compare. Use 'working', 'committed',
#                       or custom commit specification. Latest should be same
#                       as cover run. Default='working'.
#
# For the commit selection, you want the latest to match what the coverage
# was done on. This translates into the commit specification for 'git diff'.
# If you have uncommitted changes, you can use (the default) 'working',
# which will use 'HEAD'. If you've already committed, you can use 'commit',
# which will use 'HEAD^'. Otherwise, you can use any valid 'git diff' commit
# specification. Just make sure that the newer commit must match what was
# used in the coverage report created.
#
# You can adjust the number of lines of context surrounding the diff lines,
# just as is done with 'git diff'.
#
# The output will show each file from the diffs along with a report on
# the coverage. Each line (including surrounding context lines) with line
# number, coverage indication, diff indication, and the source line.
#
# The coverage indication is 'run' meaning the line is covered, 'mis'
# meaning the line is missing coverage, 'par' meaning the line is partially
# covered, or '   ' meaning the line is ignored w.r.t. coverage.
#
# There is a summary of covered, missing, partial, and ignored lines
# that were added/changed (only - no context lines).
#
# The diff indication will be a '+' for lines added/changed by the diff,
# or ' ' for context lines. Note: if a diff is at the start or end of a
# file, there may not be coverage lines.
#
# If the file was not exercised as part of coverage, or if the file did
# not have any added/changed lines, it will be indicated.

from __future__ import print_function

import argparse
from collections import Counter
import os
import re
import subprocess

file_re = re.compile(r'diff --git a/(\S+)')
diff_region_re = re.compile(r'@@\s[-]\S+\s[+](\S+)\s@@')
source_line_re = re.compile(r'<p id="n(\d+)" class="([^"]+)"')
title_re = re.compile(r'\s*<title>Coverage for [^:]+:\s+(\d+%)<\/title>')
summary_end_re = re.compile(r'\s+<td class="text">')

__version__ = "0.2"


class DiffCollectionFailed(Exception):
    pass


class SourceLine(object):

    def __init__(self, line_number, is_context=True, code=''):
        self.line_number = line_number
        self.is_context = is_context
        self.code = code
        self.status = '???'

    def __eq__(self, other):
        return (self.line_number == other.line_number and
                self.is_context == other.is_context)

    def __repr__(self):
        return "SourceLine(line_number=%d, is_context=%s)" % (self.line_number,
                                                              self.is_context)


class SourceModule(object):

    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.line_num_map = {l.line_number: l for l in lines}
        self.cover_file = (filename.replace('/', '_').replace('.', '_') +
                           ".html")
        self.have_report = False
        self.coverage = '??%'

    def update_line_status(self, line_number, status):
        if line_number in self.line_num_map:
            line = self.line_num_map[line_number]
            if status.startswith('pln'):
                line.status = '   '
            else:
                line.status = status[4:7]

    def report(self):
        output = self.filename
        if not self.have_report:
            return "%s (No coverage data)\n" % output
        if not self.lines or all(l.is_context for l in self.lines):
            return "%s (No added/changed lines)\n" % output
        stats = Counter([l.status for l in self.lines if not l.is_context])
        output += " (run={}, mis={}, par={}, ign={}) {}\n".format(
            stats['run'], stats['mis'], stats['par'], stats['   '],
            self.coverage)
        last_line = None
        for line in self.lines:
            if last_line and line.line_number != (last_line + 1):
                output += "\n"
            output += "{:5d} {} {} {}\n".format(
                line.line_number, line.status,
                ' ' if line.is_context else '+', line.code)
            last_line = line.line_number
        return output


def check_coverage_status(coverage_info, module):
    for coverage_line in coverage_info:
        m = title_re.match(coverage_line)
        if m:
            module.coverage = m.group(1)
            continue
        if summary_end_re.match(coverage_line):
            return
        m = source_line_re.match(coverage_line)
        if m:
            line_num = int(m.group(1))
            status = m.group(2)
            module.update_line_status(line_num, status)


def check_coverage_file(root, module):
    """Check the lines in coverage file and report coverage status."""
    report_file = os.path.join(root, 'cover', module.cover_file)
    if not os.path.isfile(report_file):
        return  # No coverage data for file
    with open(report_file) as coverage_info:
        coverage_lines = coverage_info.readlines()
        check_coverage_status(coverage_lines, module)
        module.have_report = True


def collect_diff_lines(diff_region, start, last):
    """Find added and context lines in a diff region.

    Note: If the diff region is at the start or end of the file, there
    may not be context lines.
    """
    lines = []
    line_num = start
    while line_num <= last:
        line = next(diff_region)
        if line.startswith('-'):
            continue
        lines.append(SourceLine(line_num, is_context=line.startswith(' '),
                                code=line[1:]))
        line_num += 1
    return lines


def parse_diffs(diff_output):
    """Collect the file and ranges of diffs added, if any."""
    added_lines = []
    source_file = ''
    diff_lines = iter(diff_output.splitlines())
    for line in diff_lines:
        m = file_re.match(line)
        if m:
            source_file = m.group(1)
            continue
        m = diff_region_re.match(line)
        if m:
            start, comma, num = m.group(1).partition(',')
            start = int(start)
            if num:
                last = start + int(num) - 1
            else:
                last = start
            added_lines += collect_diff_lines(diff_lines, start, last)
    return (source_file, added_lines)


def collect_diffs_for_files(root, versions, source_files, context_lines):
    """Generator to obtain the diffs for files."""
    os.chdir(root)
    for filename in source_files:
        command = ['git', 'diff', '-U%d' % context_lines,
                   '-w', versions, '--', filename]
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff_lines, err = p.communicate()
        if err:
            raise DiffCollectionFailed(
                "Unable to collect diffs for file %s/%s: %s" %
                (root, filename, err))
        yield diff_lines


def collect_diff_files(root, versions):
    """Generator to obtain all the diff files."""
    command = ['git', 'diff', '--name-only', versions]
    os.chdir(root)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        raise DiffCollectionFailed("Unable to find diff files to examine "
                                   "in %s: %s" % (root, err))
    for filename in out.splitlines():
        if not os.path.basename(filename).startswith('.'):
            yield filename


def validate(parser, provided_args=None):
    args = parser.parse_args(provided_args)
    args.root = os.path.abspath(args.root)
    if not os.path.isdir(args.root):
        parser.error("The repo-dir must be a directory pointing to the top "
                     "of the Git repo")
    if not os.path.isdir(os.path.join(args.root, 'cover')):
        parser.error("Missing cover directory for project")
    if args.commits == 'working':
        args.commits = 'HEAD'
    elif args.commits == 'committed':
        args.commits = 'HEAD^..HEAD'
    return args


def main():
    args = validate(setup_parser())
    files = collect_diff_files(args.root, args.commits)
    diff_files = collect_diffs_for_files(args.root, args.commits, files,
                                         args.context)
    for diffs in diff_files:
        source_file, lines = parse_diffs(diffs)
        module = SourceModule(source_file, lines)
        check_coverage_file(args.root, module)
        print(module.report())


def setup_parser():
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument(
        '-c', '--context', action='store', type=int, default=3,
        help='Number of context lines around diff regions. Default=3.')
    parser.add_argument(
        '-w', '--which', action='store', default="working", dest='commits',
        help="Which commit(s) to compare. Use 'working', 'commit', or "
        "custom commit specification. Latest should be same as cover run. "
        "Default='working'.")
    parser.add_argument(dest='root', metavar='repo-dir',
                        help="Root of Git repo")
    return parser


if __name__ == "__main__":
    main()
