import datetime
import hashlib
import os
import pathlib

from django.conf import settings


def filedate(filename):
    if not os.path.exists(filename):
        return

    f = pathlib.Path(filename)
    result = datetime.datetime.fromtimestamp(f.stat().st_mtime)
    return result


def uploadfile(source, target=None):
    print(f"file.py:uploadfile({source}, {target})")

    if target is None:
        basepath = os.path.join(settings.BASE_DIR, "data/upload")
        filename = os.path.join(basepath, source.name)
    else:
        filename = target

    try:
        with open(filename, "wb+") as fhandle:
            for chunk in source.chunks():
                fhandle.write(chunk)
        result = True
    except:
        result = False

    print(f"file.py:uploadfile({source}, {filename}) => {result}")

    return result, filename


def filehash(filename, block_size=2**14):
    """
    Generate a unique key from the contents of a file with md5 hashing
    :param filename:
    :param block_size:
    :result:
    """
    try:
        md5 = hashlib.md5()
        f = open(filename, "rb")
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        f.close()
    except:
        return

    return md5.hexdigest()
