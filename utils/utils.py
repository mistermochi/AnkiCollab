import json
import shutil
import hashlib
import os
from pprint import pprint
from sqlite3 import OperationalError
try:
    unicode('')
except NameError:
    unicode = str

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def add_column(db, table_name, column_name, default_value="\"\""):
    try:
        db.execute('ALTER TABLE {} ADD COLUMN {} TEXT DEFAULT {};'.format(table_name, column_name, default_value))
    except OperationalError as e:
        # The point is to ignore error if there is already the column
        pprint(e)


def add_absent_field(object_to_modify, field_name, default_value=None):
    """
    Add field to the object if it does not exist yet.
    :param object_to_modify:
    :param field_name:
    :param default_value:
    :return:
    """
    setattr(object_to_modify, field_name, getattr(object_to_modify, field_name, default_value))


def json_compare(first, second):
    """
    Json comparison for complex objects. Should be JsonSerializable
    """
    return json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def fs_remove(path):
    """
    Remove file or directory (recursively). Ignore if it did not exist before.
    :param path:
    :return:
    """

    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(unicode(str(path)))
    else:
        os.remove(unicode(str(path)))

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def md5_from_feed(f):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: f.read(4096), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()

def md5_from_infolist(infolist):
    CRClist = [];
    for fileinfo in infolist:
        CRClist.append(fileinfo.CRC)
    hash_md5 = hashlib.md5(json.dumps(CRClist).encode('utf-8'))   # using CRC of each file as a surrogate
    return hash_md5.hexdigest()
