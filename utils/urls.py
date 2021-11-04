import os
from urllib.error import URLError
from urllib.request import urlopen

import requests


def fetchurl(urlstr: str):
    """

    :param urlstr: url of content to download
    :return:
    """
    try:
        response = requests.get(urlstr)
        contents = response.content
    except requests.exceptions.InvalidSchema:
        try:
            response = urlopen(urlstr)
            contents = response.read()
        except URLError:
            return None, None
    except requests.exceptions.ConnectionError:
        return None, None

    return contents, response.status_code


def fetchurl_to_file(urlstr: str, target: str):
    """

    :param urlstr: url of content to download
    :param target: filename with path to store downloaded file
    :return:
    """
    contents, status_code = fetchurl(urlstr)
    if contents is None or status_code != 200: return

    with open(target, 'wb') as fhandle:
        fhandle.write(contents)

    if os.path.getsize(target) == 0:
        os.remove(target)

    return True
