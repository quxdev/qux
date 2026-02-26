import datetime
import hashlib
import logging
import os
import pathlib

from django.conf import settings

logger = logging.getLogger(__name__)


def filedate(filename):
    if not os.path.exists(filename):
        return None

    f = pathlib.Path(filename)
    result = datetime.datetime.fromtimestamp(f.stat().st_mtime)
    return result


def uploadfile(source, target=None):
    logger.debug("uploadfile(%s, %s)", source, target)

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
    except (IOError, OSError):
        result = False

    logger.debug("uploadfile(%s, %s) => %s", source, filename, result)

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
        with open(filename, "rb") as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5.update(data)
    except (IOError, OSError):
        return None

    return md5.hexdigest()
