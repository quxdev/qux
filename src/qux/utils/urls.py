"""URL fetching + meta-tag extraction helpers.

NOT to be confused with Django's URL routing — this module deals with HTTP
URLs as data (fetch them, parse them, pull OG / canonical / title metadata
from the HTML).

- ``fetchurl(url)`` — GET via ``requests``, falls back to stdlib ``urlopen``
  for non-http(s) schemes. Returns ``(contents, status_code)`` tuple.
- ``MetaURL`` — class that wraps a fetched HTML page and exposes parsed
  ``<title>``, ``<meta name="description">``, ``og:*``, ``canonical``, and
  ``image`` attributes via BeautifulSoup. ``MetaURL.load(url)`` constructs
  + populates from a URL; ``.to_dict()`` / ``.__str__`` produce dict / JSON
  forms suitable for rendering link previews.

Used by qux.seo and the sitespeed/pagespeed audit commands.
"""

import json
import os
import re
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

from django.http import JsonResponse

import bs4
import requests


def fetchurl(urlstr: str):
    """

    :param urlstr: url of content to download
    :return: (contents, response_status_code)
    """
    try:
        response = requests.get(urlstr, timeout=30)
        contents = response.content
    except requests.exceptions.InvalidSchema:
        try:
            response = urlopen(urlstr, timeout=30)
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
    if contents is None or status_code != 200:
        return None

    with open(target, "wb") as fhandle:
        fhandle.write(contents)

    if os.path.getsize(target) == 0:
        os.remove(target)

    return True


class MetaURL:
    def __init__(self):
        self.orig_url = None
        self.url = None
        self.domain = None
        # https://ogp.me/#types
        # website, profile, book, article, music, video
        self.type = None
        self.title = None
        self.description = None
        self.image = None

    def to_dict(self):
        return {
            "domain": self.domain,
            "url": self.url,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "image": self.image,
        }

    def __str__(self):
        return json.dumps(self.to_dict())

    def load(self):
        """
        Inspired by github.com/vitorfs/bootcamp/blob/master/bootcamp/helpers.py
        """
        self.orig_url = self.url

        parsed_url = urlparse(self.url)
        if not parsed_url.scheme:
            self.url = f"https://{parsed_url.path}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) "
            "AppleWebKit/601.3.9 (KHTML, like Gecko) "
            "Version/9.0.2 Safari/601.3.9"
        }

        try:
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return JsonResponse({"message": "URL appears to be invalid"})
        except requests.exceptions.Timeout:
            return JsonResponse({"message": "Error connecting to site"})

        soup = bs4.BeautifulSoup(response.content, features="html.parser")
        try:
            ogdata = soup.html.head.find_all(property=re.compile(r"^og"))
            ogdata = {og.get("property")[3:]: og.get("content") for og in ogdata}
            found = True
        except AttributeError:
            ogdata = {}
            found = False

        if found:
            if not ogdata.get("url"):
                ogdata["url"] = response.url
            if not ogdata.get("title"):
                ogdata["title"] = soup.html.title.text
            description = ogdata.get("description")
            if description is None:
                ogdata["description"] = None
            self.type = ogdata.get("type", "website")
            self.type = self.type.rsplit(".", 1)[-1]
        else:
            filepath = urlparse(response.url).path
            extension = os.path.splitext(filepath)[1].split(".")[-1]
            extension = extension[:3].lower()
            ogdata = {
                "url": urljoin(response.url, filepath),
                "title": filepath,
                "description": None if self.url == response.url else self.url,
            }
            self.type = {
                "pdf": "file.pdf",
                "xls": "file.xls",
                "doc": "file.doc",
                "ppt": "file.ppt",
            }.get(str(extension), "file.unknown")

        self.domain = urlparse(self.url).netloc

        for x in ["url", "title", "description", "image"]:
            setattr(self, x, ogdata.get(x))

        return ogdata
