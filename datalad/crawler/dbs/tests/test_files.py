# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
from os.path import join as opj, curdir, sep
from ..files import PhysicalFileStatusesDB, JsonFileStatusesDB

from ....tests.utils import with_tree
from ....tests.utils import assert_equal
from ....tests.utils import assert_false
from ....tests.utils import assert_true
from ....tests.utils import chpwd
from ....support.annexrepo import AnnexRepo

@with_tree(
    tree={'file1.txt': 'load1',
          '2git': 'load',
          'd': {
              'file2.txt': 'load2'
          }})
def _test_AnnexDB(cls, path):
    filepath1 = opj(path, 'file1.txt')
    filep2 = opj('d', 'file2.txt')
    filepath2 = opj(path, filep2)

    annex = AnnexRepo(path, create=True)
    # PhysicalFileStatusesDB relies on information in annex so files
    # must be committed first
    annex.annex_add('file1.txt')
    annex.git_commit("initial commit")
    db = cls(annex=annex)

    def set_db_status_from_file(fpath):
        """To test JsonFileStatusesDB we need to keep updating status stored"""
        if cls is JsonFileStatusesDB:
            # we need first to set the status
            db.set(fpath, db._get_fileattributes_status(fpath))

    set_db_status_from_file('file1.txt')
    status1 = db.get('file1.txt')
    assert(status1.size)

    status1_ = db.get('file1.txt')
    assert_equal(status1, status1_)
    assert_false(db.is_different('file1.txt', status1))
    assert_false(db.is_different('file1.txt', status1_))
    # even if we add a filename specification
    status1_.filename = 'file1.txt'
    assert_false(db.is_different('file1.txt', status1_))
    status1_.filename = 'different.txt'
    assert_true(db.is_different('file1.txt', status1_))


    os.unlink(filepath1)  # under annex- - we don't have unlock yet and thus can't inplace augment
    with open(filepath1, 'a') as f:
        f.write('+')
    set_db_status_from_file(filepath1)
    assert(db.is_different('file1.txt', status1))

    # we should be able to get status of files out and inside of git
    set_db_status_from_file('2git')
    status_git1 = db.get('2git')
    annex.git_add('2git')
    annex.git_commit("added 2git")
    assert_equal(db.get('2git'), status_git1)

    # we should be able to get status of files with relative path to top dir and abs path
    set_db_status_from_file(filep2)
    status2 = db.get(filep2)
    status2_full = db.get(filepath2)
    assert_equal(status2, status2_full)
    # TODO? what about relative to curdir??
    #with chpwd(opj(path, 'd')):
    #    status2_dir = db.get('./file2.txt')
    #    assert_equal(status2, status2_dir)

    # since we asked about each file we added to DB/annex -- none should be
    # known as "deleted"
    assert_equal(db.get_obsolete(), [])

    # Possibly save its state to persistent storage
    #import pdb; pdb.set_trace()
    db.save()

    # but if we create another db which wasn't queried yet
    db2 = cls(annex=annex)
    # all files should be returned
    assert_equal(
            set(db2.get_obsolete()),
            {opj(path, p) for p in ['file1.txt', filep2, '2git']})
    # and if we query one, it shouldn't be listed as deleted any more
    status2_ = db2.get(filep2)
    assert_equal(status2, status2_)
    assert_equal(
            set(db2.get_obsolete()),
            {opj(path, p) for p in ['file1.txt', '2git']})

    # and if we queried with ./ prefix, should work still
    db2.get(curdir + sep + 'file1.txt')
    assert_equal(
            set(db2.get_obsolete()),
            {opj(path, p) for p in ['2git']})

    # and if we queried with full path, should work still
    db2.get(opj(path, '2git'))
    assert_equal(db2.get_obsolete(), [])

def test_AnnexDBs():
    for cls in (PhysicalFileStatusesDB,
                JsonFileStatusesDB,):
        yield _test_AnnexDB, cls