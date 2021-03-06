#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function)

from unittest import TestCase
import pytest 
import warnings, os, shutil

import numpy as np 
from copy import copy, deepcopy 

try:
    import h5py 
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

from astropy.config.paths import _find_home 
from astropy.table import Table
from astropy.table import vstack as table_vstack

from . import helper_functions

from ..halo_table_cache_log_entry import HaloTableCacheLogEntry, get_redshift_string
from ..halo_table_cache import HaloTableCache

from ...custom_exceptions import InvalidCacheLogEntry, HalotoolsError

### Determine whether the machine is mine
# This will be used to select tests whose 
# returned values depend on the configuration 
# of my personal cache directory files
aph_home = u'/Users/aphearin'
detected_home = _find_home()
if aph_home == detected_home:
    APH_MACHINE = True
else:
    APH_MACHINE = False

__all__ = ('TestHaloTableCache',  )

class TestHaloTableCache(TestCase):
    """
    """

    def setUp(self):


        self.dummy_cache_baseloc = helper_functions.dummy_cache_baseloc
        try:
            shutil.rmtree(self.dummy_cache_baseloc)
        except:
            pass
        os.makedirs(self.dummy_cache_baseloc)


        if HAS_H5PY:

            # Create a good halo catalog and log entry
            self.good_table = Table(
                {'halo_id': [1, 2, 3], 
                'halo_x': [1, 2, 3], 
                'halo_y': [1, 2, 3], 
                'halo_z': [1, 2, 3], 
                'halo_mass': [1, 2, 3], 
                })
            self.good_table_fname = os.path.join(self.dummy_cache_baseloc, 
                'good_table.hdf5')
            self.good_table.write(self.good_table_fname, path='data')

            self.good_log_entry = HaloTableCacheLogEntry('good_simname1', 
                'good_halo_finder', 'good_version_name', 
                get_redshift_string(0.0), self.good_table_fname)

            f = h5py.File(self.good_table_fname)
            for attr in self.good_log_entry.log_attributes:
                f.attrs.create(str(attr), str(getattr(self.good_log_entry, attr)))
            f.attrs.create('Lbox', 100.)
            f.attrs.create('particle_mass', 1e8)
            f.close()

            # Create a second good halo catalog and log entry

            self.good_table2 = deepcopy(self.good_table)
            self.good_table2_fname = os.path.join(self.dummy_cache_baseloc, 
                'good_table2.hdf5')
            self.good_table2.write(self.good_table2_fname, path='data')

            self.good_log_entry2 = HaloTableCacheLogEntry('good_simname2', 
                'good_halo_finder2', 'good_version_name', 
                get_redshift_string(1.0), self.good_table2_fname)

            f = h5py.File(self.good_table2_fname)
            for attr in self.good_log_entry2.log_attributes:
                f.attrs.create(str(attr), str(getattr(self.good_log_entry2, attr)))
            f.attrs.create('Lbox', 100.)
            f.attrs.create('particle_mass', 1e8)
            f.close()

            # Create a bad halo catalog and log entry

            self.bad_table = Table(
                {'halo_id': [1, 2, 3], 
                'halo_y': [1, 2, 3], 
                'halo_z': [1, 2, 3], 
                'halo_mass': [1, 2, 3], 
                })
            bad_table_fname = os.path.join(self.dummy_cache_baseloc, 
                'bad_table.hdf5')
            self.bad_table.write(bad_table_fname, path='data')

            self.bad_log_entry = HaloTableCacheLogEntry('1', '2', '3', '4', '5')

    @pytest.mark.skipif('not HAS_H5PY')
    def test_determine_log_entry_from_fname(self):
        cache = HaloTableCache(read_log_from_standard_loc = False)

        entry = self.good_log_entry
        fname = entry.fname
        result = cache.determine_log_entry_from_fname(fname)
        assert result == self.good_log_entry

        entry = self.bad_log_entry
        fname = entry.fname
        result = cache.determine_log_entry_from_fname(fname)
        assert result == "File does not exist"

        entry.fname = self.bad_log_entry.fname
        os.system('touch ' + entry.fname)
        result = cache.determine_log_entry_from_fname(fname)
        assert result == "Can only self-determine the log entry of files with .hdf5 extension"

        entry = self.good_log_entry
        fname = entry.fname
        f = h5py.File(fname)
        tmp = deepcopy(f.attrs['version_name'])
        del f.attrs['version_name']
        f.close()
        result = cache.determine_log_entry_from_fname(fname)
        assert "The hdf5 file is missing the following metadata:" in result

        f = h5py.File(fname)
        f.attrs.create('version_name', tmp)
        f.close()


    @pytest.mark.skipif('not HAS_H5PY')
    def test_add_entry_to_cache_log(self):
        cache = HaloTableCache(read_log_from_standard_loc = False)
        assert len(cache.log) == 0

        with pytest.raises(TypeError) as err:
            cache.add_entry_to_cache_log('abc', update_ascii = False)
        substr = "You can only add instances of HaloTableCacheLogEntry to the cache log"
        assert substr in err.value.message

        cache.add_entry_to_cache_log(self.good_log_entry, update_ascii = False)
        assert len(cache.log) == 1

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cache.add_entry_to_cache_log(self.good_log_entry, update_ascii = False)
            substr = "cache log already contains the entry"
            assert substr in str(w[-1].message)
        assert len(cache.log) == 1

        cache.add_entry_to_cache_log(self.good_log_entry2, update_ascii = False)
        assert len(cache.log) == 2

        with pytest.raises(InvalidCacheLogEntry) as err:
            cache.add_entry_to_cache_log(self.bad_log_entry, update_ascii = False)
        substr = "The input filename does not exist."
        assert substr in err.value.message

    @pytest.mark.skipif('not HAS_H5PY')
    def test_remove_entry_from_cache_log(self):
        cache = HaloTableCache(read_log_from_standard_loc = False)
        cache.add_entry_to_cache_log(self.good_log_entry, update_ascii = False)
        cache.add_entry_to_cache_log(self.good_log_entry2, update_ascii = False)
        assert len(cache.log) == 2

        entry = self.good_log_entry
        args = [getattr(entry, attr) for attr in entry.log_attributes]
        cache.remove_entry_from_cache_log(*args, update_ascii = False)
        assert len(cache.log) == 1

        with pytest.raises(HalotoolsError) as err:
            cache.remove_entry_from_cache_log(*args, update_ascii = False)
        substr = "This entry does not appear in the log."
        assert substr in err.value.message

        cache.remove_entry_from_cache_log(*args, update_ascii = False, 
            raise_non_existence_exception = False)
        assert len(cache.log) == 1

    @pytest.mark.skipif('not HAS_H5PY')
    def test_update_cached_file_location(self):
        """
        """
        cache = HaloTableCache(read_log_from_standard_loc = False)
        cache.add_entry_to_cache_log(self.good_log_entry, update_ascii = False)
        old_fname = self.good_log_entry.fname
        old_basename = os.path.basename(old_fname)
        new_basename = "dummy" + old_basename
        new_fname = os.path.join(os.path.dirname(old_fname), new_basename)
        os.rename(old_fname, new_fname)

        assert self.good_log_entry in cache.log
        cache.update_cached_file_location(new_fname, old_fname, 
            update_ascii = False)
        assert self.good_log_entry not in cache.log

        new_entry = cache.determine_log_entry_from_fname(new_fname)
        assert new_entry in cache.log


    def tearDown(self):
        try:
            shutil.rmtree(self.dummy_cache_baseloc)
        except:
            pass

