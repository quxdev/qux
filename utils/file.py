import os
import pathlib
import datetime
import hashlib

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
        basepath = os.path.join(settings.BASE_DIR, 'data/upload')
        filename = os.path.join(basepath, source.name)
    else:
        filename = target

    try:
        with open(filename, 'wb+') as fhandle:
            for chunk in source.chunks():
                fhandle.write(chunk)
        result = True
    except:
        result = False

    print(f"file.py:uploadfile({source}, {filename}) => {result}")

    return result, filename

