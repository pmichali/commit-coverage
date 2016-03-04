import mock
import os
import pytest
import shutil
import subprocess
import sys
import tempfile

import my_coverage as cover

if sys.version_info > (3, ):
    import builtins
else:
    import __builtin__ as builtins


@pytest.fixture()
def fake_cover_project(request):
    cover_project_area = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(cover_project_area)
    os.mkdir('cover')
    os.chdir(cwd)

    def fin():
        shutil.rmtree(cover_project_area)
    request.addfinalizer(fin)
    return cover_project_area


@pytest.fixture()
def fake_project(request):
    project_area = tempfile.mkdtemp()

    def fin():
        shutil.rmtree(project_area)
    request.addfinalizer(fin)
    return project_area


def test_extract_no_added_line_diffs():
    diffs = """diff --git a/whodunit.py b/whodunit.pyindex acd6edc..513b410 100644
--- a/whodunit.py
+++ b/whodunit.py
@@ -1,3 +1,2 @@
 #!/usr/bin/env python
-# whodunit
 #
"""
    source_file, lines = cover.parse_diffs(diffs)
    expected = [cover.SourceLine(1), cover.SourceLine(2)]
    assert source_file == 'whodunit.py'
    assert lines == expected


def test_extract_single_added_line():
    diffs = """diff --git a/path/file.py b/path/file.py
index 0fa872e..77ebfef 100644
--- a/path/file.py
+++ b/path/file.py
@@ -59,6 +59,7 @@ INSTANCE_2 = 'testvm2'
 INSTANCE_PC = 'testpcvm'
 INSTANCE_DUAL = 'testdualvm'
 
+NEXUS_BAREMETAL_PORT_1 = 'Ethernet 1/10'
 NEXUS_PORT_1 = 'ethernet:1/10'
 NEXUS_PORT_2 = 'ethernet:1/20'
 NEXUS_DUAL1 = 'ethernet:1/3'
"""
    source_file, lines = cover.parse_diffs(diffs)
    expected = [
        cover.SourceLine(59), cover.SourceLine(60), cover.SourceLine(61),
        cover.SourceLine(62, False),
        cover.SourceLine(63), cover.SourceLine(64), cover.SourceLine(65)
    ]
    assert source_file == 'path/file.py'
    assert lines == expected
    assert lines[0].code == "INSTANCE_PC = 'testpcvm'"
    assert lines[1].code == "INSTANCE_DUAL = 'testdualvm'"
    assert lines[2].code == ""
    assert lines[3].code == "NEXUS_BAREMETAL_PORT_1 = 'Ethernet 1/10'"
    assert lines[4].code == "NEXUS_PORT_1 = 'ethernet:1/10'"
    assert lines[5].code == "NEXUS_PORT_2 = 'ethernet:1/20'"
    assert lines[6].code == "NEXUS_DUAL1 = 'ethernet:1/3'"


def test_extract_multiple_lines():
    diffs = """diff --git a/path/constants.py b/path/constants.py
index 8c57e4a..983de98 100644
--- a/path/constants.py
+++ b/path/constants.py
@@ -42,6 +42,7 @@ PORT_PROFILE_NAME_PREFIX = "OS-PP-"
 CLIENT_PROFILE_NAME_PREFIX = "OS-CL-"
 CLIENT_PROFILE_PATH_PREFIX = "/cl-"
 
-ETH0 = "/ether-eth0"
-ETH1 = "/ether-eth1"
+ETH0 = "eth0"
+ETH1 = "eth1"
+ETH_PREFIX = "/ether-"
 DUPLICATE_EXCEPTION = "object already exists"
"""
    source_file, lines = cover.parse_diffs(diffs)
    expected = [
        cover.SourceLine(42), cover.SourceLine(43), cover.SourceLine(44),
        cover.SourceLine(45, False), cover.SourceLine(46, False),
        cover.SourceLine(47, False),
        cover.SourceLine(48)
    ]
    assert source_file == 'path/constants.py'
    assert lines == expected


def test_extract_multiple_ranges_for_file():
    """Check multiple ranges in a single file.

    Note: Final region is at end of file and does not have a trailing
    context line.
    """
    diffs = """diff --git a/whodunit.py b/whodunit.py
index 2af698e..79da120 100644
--- a/whodunit.py
+++ b/whodunit.py
@@ -475,8 +484,8 @@ def build_owner(args):
                           args.verbose, args.max)
 
 
-def main(args):
-    args.root = os.path.abspath(args.root)
+def main(parser):
+    args = validate(parser)
     owners = build_owner(args)
 
     # Generators to get the owner info
@@ -491,7 +500,7 @@ def main(args):
         all_authors += top_n
         # Don't alter ordering, as names in sort (date/size) order
         print("(%s)" % ', '.join(top_n))
-        if args.details:
+        if owners.details:
             owners.show_details(args.max)
     print("\\n\\nAll authors: %s" % ', '.join(sort_by_name(all_authors)))
 
@@ -517,5 +526,4 @@ def setup_parser():
     return parser
 
 if __name__ == "__main__":
-    parser = setup_parser()
-    main(parser.parse_args())
+    main(setup_parser())
"""
    source_file, lines = cover.parse_diffs(diffs)
    expected = [
        cover.SourceLine(484), cover.SourceLine(485), cover.SourceLine(486),
        cover.SourceLine(487, False), cover.SourceLine(488, False),
        cover.SourceLine(489), cover.SourceLine(490), cover.SourceLine(491),

        cover.SourceLine(500), cover.SourceLine(501), cover.SourceLine(502),
        cover.SourceLine(503, False),
        cover.SourceLine(504), cover.SourceLine(505), cover.SourceLine(506),

        cover.SourceLine(526), cover.SourceLine(527), cover.SourceLine(528),
        cover.SourceLine(529, False)
    ]
    assert source_file == 'whodunit.py'
    assert len(lines) == 19
    print("%r" % lines)
    print("%r" % expected)
    assert lines == expected


def test_extract_file_with_one_line_only():
    """Special case test of file with no context lines available."""
    diffs = """diff --git a/dummy b/dummy
new file mode 100644
index 0000000..257cc56
--- /dev/null
+++ b/dummy
@@ -0,0 +1 @@
+foo
"""
    source_file, lines = cover.parse_diffs(diffs)
    assert source_file == 'dummy'
    assert lines == [cover.SourceLine(1, is_context=False)]


def test_extract_no_context_no_added_lines():
    """Context is set to zero and there are no added lines."""
    diffs = """diff --git a/dummy b/dummy
index 7a47da8..7ee1d92 100644
--- a/dummy
+++ b/dummy
@@ -65 +35,0 @@ check_pot_files_errors () {
-check_opinionated_shell
"""
    source_file, lines = cover.parse_diffs(diffs)
    assert source_file == 'dummy'
    assert lines == []


def test_extract_one_line_deleted_and_added():
    """Special case where both diff markers have no commas.

    Indicates that one line deleted and one line added.
    """
    diffs = """diff --git a/devstack/saf/cisco_saf b/devstack/saf/cisco_saf
index 2498062..efcc602 100644
--- a/devstack/saf/cisco_saf
+++ b/devstack/saf/cisco_saf
@@ -1 +1 @@
-#!/bin/bash
+#!/usr/bin/env bash
"""
    source_file, lines = cover.parse_diffs(diffs)
    assert source_file == 'devstack/saf/cisco_saf'
    assert lines == [cover.SourceLine(1, is_context=False)]


def test_collecting_diffs(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.side_effect = [('output1', ''),
                                                      ('output2', '')]
        monkeypatch.setattr('os.chdir', lambda x: None)
        diffs = cover.collect_diffs_for_files('/some/path', versions="HEAD",
                                        source_files=['foo', 'bar'],
                                        context_lines=5)
        assert list(diffs) == ['output1', 'output2']

    expected = [
        mock.call(['git', 'diff', '-U5', '-w', 'HEAD', '--', 'foo'],
                  stderr=-1, stdout=-1),
        mock.call().communicate(),
        mock.call(['git', 'diff', '-U5', '-w', 'HEAD', '--', 'bar'],
                  stderr=-1, stdout=-1),
        mock.call().communicate()
    ]
    assert popen.call_count == 2
    popen.assert_has_calls(expected)


def test_fail_collecting_diffs(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = ('', 'bad file')
        monkeypatch.setattr('os.chdir', lambda x: None)

        diffs = cover.collect_diffs_for_files('/some/path', versions="HEAD",
                                        source_files=['foo'],
                                        context_lines=5)
        with pytest.raises(cover.DiffCollectionFailed) as excinfo:
            for diff in diffs:
                pass
        expected_msg = ('Unable to collect diffs for file /some/path/foo: '
                        'bad file')
        assert excinfo.value.args[0] == expected_msg


def test_collecting_diff_files(monkeypatch):
    """Ignores files with leading period."""
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = (
            'foo.py\n.ignored-file\nbar.py\n', '')
        monkeypatch.setattr('os.chdir', lambda x: None)

        diff_files = cover.collect_diff_files(fake_project, 'HEAD')
        assert list(diff_files) == ['foo.py', 'bar.py']


def test_fail_collecting_diff_files(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = ('foo.py', 'no file')
        monkeypatch.setattr('os.chdir', lambda x: None)
        
        diff_files = cover.collect_diff_files('/some/path', 'HEAD')
        with pytest.raises(cover.DiffCollectionFailed) as excinfo:
            for diff_file in diff_files:
                pass
        expected_msg = ('Unable to find diff files to examine in '
                        '/some/path: no file')
        assert excinfo.value.args[0] == expected_msg


def test_determine_coverage_file_name():
    filename = "relative/path/to/file.py"
    module = cover.SourceModule(filename, lines=[])
    assert module.cover_file == 'relative_path_to_file_py.html'


def test_update_status_line():
    line = cover.SourceLine(10, is_context=False)
    module = cover.SourceModule('foo', [line])
    module.update_line_status(10, 'pln')
    assert line.status == '   '
    module.update_line_status(10, 'stm run')
    assert line.status == 'run'
    module.update_line_status(10, 'stm mis')
    assert line.status == 'mis'
    module.update_line_status(10, 'stm par')
    assert line.status == 'par'


def test_fail_update_status_no_matching_line():
    line = cover.SourceLine(10, is_context=False)
    module = cover.SourceModule('foo', [line])
    module.update_line_status(12, 'stm run')
    assert line.status == '???'


def test_check_coverage_no_lines():
    coverage_info = """
<p id="n1" class="pln"><a href="#n1">1</a></p>
<p id="n2" class="pln"><a href="#n2">2</a></p>
<p id="n3" class="pln"><a href="#n3">3</a></p>
""".splitlines()
    module = cover.SourceModule('foo.py', [])
    cover.check_coverage_status(coverage_info, module)
    assert module.lines == []


def test_coverage_status_collection():
    coverage_info = """
...
<title>Coverage for foo.py: 81%</title>
...
<p id="n63" class="pln"><a href="#n63">63</a></p>
<p id="n64" class="stm par run hide_run"><a href="#n64">64</a></p>
<p id="n65" class="stm mis"><a href="#n65">65</a></p>
<p id="n66" class="stm run hide_run"><a href="#n66">66</a></p>
...
            </td>
            <td class="text">
""".splitlines()
    non_executable_line = cover.SourceLine(63)
    partial_covered_line = cover.SourceLine(64, is_context=False)
    missing_line = cover.SourceLine(65, is_context=False)
    covered_line = cover.SourceLine(66, is_context=False)
    module = cover.SourceModule('foo.py', [non_executable_line,
                                           partial_covered_line,
                                           missing_line,
                                           covered_line])
    cover.check_coverage_status(coverage_info, module)
    assert non_executable_line.status == '   '
    assert partial_covered_line.status == 'par'
    assert missing_line.status == 'mis'
    assert covered_line.status == 'run'
    assert module.coverage == '81%'


def test_missing_coverage_file(fake_cover_project):
    module = cover.SourceModule('foo.py', [])
    cover.check_coverage_file(fake_cover_project, module)
    assert not module.have_report


def test_checking_coverage_file(monkeypatch):
    coverage_info = """
...
<title>Coverage for foo.py: 5%</title>
...
<p id="n2" class="stm run"><a href="#n2">2</a></p>
...
            </td>
            <td class="text">
""".splitlines()
    line = cover.SourceLine(2, is_context=False)
    module = cover.SourceModule('foo.py', [line])

    def is_a_file(filename):
        return True
    monkeypatch.setattr(os.path, 'isfile', is_a_file)

    with mock.patch.object(builtins, 'open', mock.mock_open(),
                           create=True) as mock_open:
        mock_open.return_value.readlines.return_value = coverage_info
        cover.check_coverage_file('.', module)
    assert module.have_report
    assert line.status == 'run'
    assert module.coverage == '5%'


def test_report_non_coverage_files():
    module = cover.SourceModule('path/foo.py', [])
    assert module.report() == 'path/foo.py (No coverage data)\n'


def test_report_no_no_added_lines():
    module = cover.SourceModule('path/foo.py', [])
    module.have_report = True
    assert module.report() == 'path/foo.py (No added/changed lines)\n'

    lines = [cover.SourceLine(10, is_context=True),
             cover.SourceLine(12, is_context=True)]
    module = cover.SourceModule('deleted_lines_file', lines)
    module.have_report = True
    assert module.report() == 'deleted_lines_file (No added/changed lines)\n'


def test_report_one_line():
    line = cover.SourceLine(10, is_context=False, code='    x = 1')
    module = cover.SourceModule('path/foo.py', [line])
    module.have_report = True
    module.coverage = '100%'
    line.status = 'run'
    expected = """path/foo.py (run=1, mis=0, par=0, ign=0) 100%
   10 run +     x = 1
"""
    assert module.report() == expected


def test_report_multiple_blocks():
    lines = [cover.SourceLine(10, is_context=False, code='x = 1'),
             cover.SourceLine(11, is_context=False, code='y = 2'),
             cover.SourceLine(20, is_context=False, code='z = 3'),
             cover.SourceLine(21, is_context=False, code='for i in [1, 2]')]
    lines[0].status = 'run'
    lines[1].status = 'mis'
    lines[2].status = 'par'
    lines[3].status = '   '
    module = cover.SourceModule('path/foo.py', lines)
    module.have_report = True
    module.coverage = '50%'

    expected = """path/foo.py (run=1, mis=1, par=1, ign=1) 50%
   10 run + x = 1
   11 mis + y = 2

   20 par + z = 3
   21     + for i in [1, 2]
"""
    assert module.report() == expected


def test_argument_parse_which(fake_cover_project):
    parser = cover.setup_parser()
    args = cover.validate(parser, [fake_cover_project])
    assert args.commits == 'HEAD'
    args = cover.validate(parser, ['-w', 'working', fake_cover_project])
    assert args.commits == 'HEAD'
    args = cover.validate(parser, ['-w', 'committed', fake_cover_project])
    assert args.commits == 'HEAD^..HEAD'
    args = cover.validate(parser, ['-w', 'HEAD~5..HEAD~3', fake_cover_project])
    assert args.commits == 'HEAD~5..HEAD~3'


def test_argument_parse_context(fake_cover_project):
    parser = cover.setup_parser()
    args = cover.validate(parser, ['-c', '10', fake_cover_project])
    assert args.context == 10


def test_validate_directory(fake_cover_project):
    parser = cover.setup_parser()
    assert cover.validate(parser, [fake_cover_project])


def test_validate_no_coverage_area(fake_project):
    parser = cover.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        cover.validate(parser, [fake_project])
    assert str(excinfo.value) == '2'


def test_validate_no_directory():
    parser = cover.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        cover.validate(parser, ['bogus-dir'])
    assert str(excinfo.value) == '2'
