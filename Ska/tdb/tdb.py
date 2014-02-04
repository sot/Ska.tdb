"""Ska.tdb: Access the Chandra Telemetry Database

:Author: Tom Aldcroft
:Copyright: 2012 Smithsonian Astrophysical Observatory
"""
import os
import re
import numpy as np

from .version import version as __version__

TDB_VERSIONS = (4, 6, 7, 8, 9, 10)
TDB_VERSION = 10

# Set None values for module globals that are set in set_tdb_version
DATA_DIR = None
tables = None
msids = None

# Tables with MSID column.  Might not be complete.
MSID_TABLES = ['tmsrment', 'tpc', 'tsc', 'tpp', 'tlmt', 'tcntr',
               'tsmpl', 'tloc']

TMSRMENT_COLS = """
                MSID
                TECHNICAL_NAME
                DATA_TYPE
                CALIBRATION_TYPE
                ENG_UNIT
                LOW_RAW_COUNT
                HIGH_RAW_COUNT
                TOTAL_LENGTH
                PROP
                COUNTER_MSID
                RANGE_MSID
                CALIBRATION_SWITCH_MSID
                CALIBRATION_DEFAULT_SET_NUM
                LIMIT_SWITCH_MSID
                LIMIT_DEFAULT_SET_NUM
                ES_SWITCH_MSID
                ES_DEFAULT_SET_NUM
                OWNER_ID
                DESCRIPTION
                EHS_HEADER_FLAG
                """.lower().split()


def set_tdb_version(version):
    """
    Set the version of the TDB which is used.

    :param version: TDB version (integer, e.g. 10)
    """
    global TDB_VERSION
    global DATA_DIR
    global tables
    global msids
    if version not in TDB_VERSIONS:
        raise ValueError('TDB version must be one of the following: {}'.format(TDB_VERSIONS))

    TDB_VERSION = version
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'p{:03d}'.format(TDB_VERSION))
    tables = TableDict()
    msids = MsidView()


def get_tdb_version():
    """
    Get the version of the TDB which is used, e.g. 10.
    """
    return TDB_VERSION


class TableDict(dict):
    def __getitem__(self, item):
        if item not in self:
            try:
                filename = os.path.join(DATA_DIR, item + '.npy')
                self[item] = TableView(np.load(filename))
            except IOError:
                raise KeyError("Table {} not in TDB files".format(item))
        return dict.__getitem__(self, item)

    def keys(self):
        import glob
        files = glob.glob(os.path.join(DATA_DIR, '*.npy'))
        return [os.path.basename(x)[:-4] for x in files]


class TableView(object):
    """Access TDB tables directly.

    This class should be used through the module-level ``tables`` variable.
    The ``tables`` variable is a special dict object that returns a
    ``TableView`` object when you ask for a TDB table such as ``tmsrment``
    (MSID descriptions) or ``tsc`` (MSID state codes).

    For tables that have an MSID column you can filter on the MSID to see only
    entries for that MSID.  The MSID names are case-insensitive.

    Examples::

      from Ska.tdb import tables

      tables.keys()  # show all available tables
      tmsrment = tables['tmsrment']
      tmsrment  # show the table
      tmsrment.colnames  # column names for this table
      tmsrment['technical_name']
      tmsrment['tephin']  # only TEPHIN entries
      tables['tsc']['aoattqt4']  # State codes for AOATTQT4
      tables['tpp']['TEPHIN']  # Point pair for TEPHIN
    """
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        if isinstance(item, basestring):
            item = item.upper()
            if (item not in self.data.dtype.names and
                    'MSID' in self.data.dtype.names):
                ok = self.data['MSID'] == item
                new_data = self.data[ok]
                if len(new_data) == 1:
                    new_data = new_data[0]
                return TableView(new_data)

        return self.data[item]

    @property
    def colnames(self):
        return self.data.dtype.names

    def __repr__(self):
        return self.data.__repr__()

    def __len__(self):
        try:
            return len(self.data)
        except TypeError:
            return 1


class MsidView(object):
    """View TDB data related to a particular MSID.

    This class should be used through the module-level ``msids`` variable.
    This allows access to TDB table entries for the MSID (attributes starting
    with "T") and TDB ``tmsrment`` table columns (lower-case attributes).

    Examples::

      from Ska.tdb import msids
      msids.<TAB>  # See available attributes

      tephin = msids['tephin']
      tephin.<TAB>  # See available attributes
      tephin.Tmsrment  # MSID definition (description, tech name etc)
      tephin.Tpp  # Calibration point pair values
      tephin.Tsc  # No state codes so it returns None
      tephin.technical_name
      tephin.data_type

      msids['aopcadmd'].Tsc  # state codes
      msids['aopcadmd'].description  # description from tmsrment
    """
    def __init__(self, msid=None):
        self._msid = msid

        # If not done already set up class properties to access attributes
        if not hasattr(self.__class__, 'msid'):
            for attr in MSID_TABLES:
                setattr(self.__class__, attr.title(),
                        property(MsidView._get_table_func(attr)))
            for attr in TMSRMENT_COLS:
                setattr(self.__class__, attr,
                        property(MsidView._get_tmsrment_func(attr)))

    def find(self, match):
        """Find MSIDs with ``match`` in the ``msid``, ``description`` or
        ``technical_name``.

        :param match: regular expression to match
        :returns: list of matching MSIDs as MsidView objects
        """
        match_re = re.compile(match, re.IGNORECASE)
        ok0 = [match_re.search(x) is not None
               for x in msids.msid]
        ok1 = [match_re.search(x) is not None
               for x in msids.description.filled('')]
        ok2 = [match_re.search(x) is not None
               for x in msids.technical_name.filled('')]
        ok = np.array(ok0) | np.array(ok1) | np.array(ok2)
        return [msids[x] for x in tables['tmsrment']['MSID'][ok]]

    def __getitem__(self, item):
        if item.upper() in tables['tmsrment']['MSID']:
            return MsidView(item)
        else:
            raise KeyError('No MSID {} in TDB'.format(item))

    @staticmethod
    def _get_table_func(tablename):
        def _func(self):
            if self._msid:
                val = tables[tablename][self._msid]
                if len(val) == 0:
                    val = None
                return val
            else:
                return tables[tablename]
        return _func

    @staticmethod
    def _get_tmsrment_func(tmsrment_col):
        def _func(self):
            tablename = 'tmsrment'
            if self._msid:
                val = tables[tablename][self._msid][tmsrment_col]
                return val
            else:
                return tables[tablename][tmsrment_col]
        return _func

    def __repr__(self):
        if self._msid:
            return '<MsidView msid="{}" technical_name="{}">'.format(
                self.msid, self.technical_name)
        else:
            return object.__repr__(self)


set_tdb_version(TDB_VERSION)
