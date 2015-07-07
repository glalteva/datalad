# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test implementation of class HandleRepo

"""

from os.path import join as opj, exists, basename, islink

from nose.tools import assert_raises, assert_is_instance, assert_true, \
    assert_equal, assert_false, assert_is_not_none, assert_not_equal, assert_in
from git.exc import GitCommandError
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, FOAF

from ..support.handlerepo import HandleRepo
from ..support.exceptions import FileInGitError
from .utils import with_tempfile, with_testrepos, assert_cwd_unchanged, \
    ignore_nose_capturing_stdout, \
    on_windows, ok_clean_git, ok_clean_git_annex_proxy, \
    get_most_obscure_supported_name, swallow_outputs, ok_


# For now (at least) we would need to clone from the network
# since there are troubles with submodules on Windows.
# See: https://github.com/datalad/datalad/issues/44
local_flavors = ['network-clone' if on_windows else 'local']

@ignore_nose_capturing_stdout
@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
@with_tempfile
def test_Handle(src, dst):

    ds = HandleRepo(dst, src)
    assert_is_instance(ds, HandleRepo, "HandleRepo was not created.")
    assert_true(exists(opj(dst, '.datalad')))

    #do it again should raise GitCommandError since git will notice there's already a git-repo at that path
    assert_raises(GitCommandError, HandleRepo, dst, src)

@ignore_nose_capturing_stdout
@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
@with_tempfile
def test_Handle_direct(src, dst):

    ds = HandleRepo(dst, src, direct=True)
    assert_is_instance(ds, HandleRepo, "HandleRepo was not created.")
    assert_true(exists(opj(dst, '.datalad')))
    assert_true(ds.is_direct_mode(), "Forcing direct mode failed.")
    

@ignore_nose_capturing_stdout
@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
def test_Handle_instance_from_existing(path):

    gr = HandleRepo(path)
    assert_is_instance(gr, HandleRepo, "HandleRepo was not created.")
    assert_true(exists(opj(path, '.datalad')))


@ignore_nose_capturing_stdout
@assert_cwd_unchanged
@with_tempfile
def test_Handle_instance_brand_new(path):

    gr = HandleRepo(path)
    assert_is_instance(gr, HandleRepo, "HandleRepo was not created.")
    assert_true(exists(opj(path, '.datalad')))


@ignore_nose_capturing_stdout
@with_testrepos(flavors=['network'])
@with_tempfile
def test_Handle_get(src, dst):

    ds = HandleRepo(dst, src)
    assert_is_instance(ds, HandleRepo, "AnnexRepo was not created.")
    testfile = 'test-annex.dat'
    testfile_abs = opj(dst, testfile)
    assert_false(ds.file_has_content("test-annex.dat"))
    with swallow_outputs() as cmo:
        ds.get(testfile)
    assert_true(ds.file_has_content("test-annex.dat"))
    f = open(testfile_abs, 'r')
    assert_equal(f.readlines(), ['123\n'], "test-annex.dat's content doesn't match.")


@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
@with_tempfile
def test_Handle_add_to_annex(src, dst):

    ds = HandleRepo(dst, src)
    filename = get_most_obscure_supported_name()
    filename_abs = opj(dst, filename)
    with open(filename_abs, 'w') as f:
        f.write("What to write?")
    ds.add_to_annex(filename)

    if not ds.is_direct_mode():
        assert_true(islink(filename_abs), "Annexed file is not a link.")
        ok_clean_git(dst, annex=True)
    else:
        assert_false(islink(filename_abs), "Annexed file is link in direct mode.")
        ok_clean_git_annex_proxy(dst)

    key = ds.get_file_key(filename)
    assert_false(key == '')
    # could test for the actual key, but if there's something and no exception raised, it's fine anyway.



@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
@with_tempfile
def test_Handle__add_to_git(src, dst):

    ds = HandleRepo(dst, src)

    filename = get_most_obscure_supported_name()
    filename_abs = opj(dst, filename)
    with open(filename_abs, 'w') as f:
        f.write("What to write?")
    ds.add_to_git(filename_abs)

    if ds.is_direct_mode():
        ok_clean_git_annex_proxy(dst)
    else:
        ok_clean_git(dst, annex=True)
    assert_raises(FileInGitError, ds.get_file_key, filename)


@assert_cwd_unchanged
@with_testrepos(flavors=local_flavors)
@with_tempfile
def test_Handle_commit(src, path):

    ds = HandleRepo(path, src)
    filename = opj(path, get_most_obscure_supported_name())
    with open(filename, 'w') as f:
        f.write("File to add to git")
    ds.annex_add(filename)

    if ds.is_direct_mode():
        assert_raises(AssertionError, ok_clean_git_annex_proxy, path)
    else:
        assert_raises(AssertionError, ok_clean_git, path, annex=True)

    ds._commit("test _commit")
    if ds.is_direct_mode():
        ok_clean_git_annex_proxy(path)
    else:
        ok_clean_git(path, annex=True)


@with_tempfile
@with_tempfile
def test_Handle_id(path1, path2):

    # check id is generated:
    handle1 = HandleRepo(path1)
    id1 = handle1.datalad_id()
    assert_is_not_none(id1)
    assert_is_instance(id1, basestring)
    assert_equal(id1,
                 handle1.repo.config_reader().get_value("annex", "uuid"))

    # check clone has same id:
    handle2 = HandleRepo(path2, path1)
    assert_equal(id1, handle2.datalad_id())


@with_tempfile
@with_tempfile
def test_Handle_equals(path1, path2):

    handle1 = HandleRepo(path1)
    handle2 = HandleRepo(path1)
    ok_(handle1 == handle2)
    assert_equal(handle1, handle2)
    handle2 = HandleRepo(path2)
    assert_not_equal(handle1, handle2)
    ok_(handle1 != handle2)

@with_tempfile
def test_Handle_metadata(path):

    handle = HandleRepo(path)
    md = handle.get_metadata()
    # TODO: Currently saved default subject in HandleRepo()
    # is generated bei URIRef(path). Stored as is, but if reloaded
    # is not equal to URIRef(path) but prefixed by "file://"
    # Therefore not a straightforward test:
    is_datalad_handle = list(md.subjects(RDF.type, Literal('Datalad HandleRepo')))
    assert_equal(len(is_datalad_handle), 1)
    assert_in(path, is_datalad_handle[0])
    assert_in((is_datalad_handle[0], FOAF.name, Literal(basename(path))), md)