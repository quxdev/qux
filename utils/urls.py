import json
import os
import re
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import bs4
import requests
from django.http import JsonResponse


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
    if contents is None or status_code != 200:
        return

    with open(target, "wb") as fhandle:
        fhandle.write(contents)

    if os.path.getsize(target) == 0:
        os.remove(target)

    return True


class MetaURL(object):
    def __init__(self):
        self.url = None
        # https://ogp.me/#types
        # website, profile, book, article, music, video
        self.type = None
        self.title = None
        self.description = None
        self.image = None
        self.domain = None

    def to_dict(self):
        result = {
            "url": self.url,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "image": self.image,
        }
        return result

    def __str__(self):
        return json.dumps(self.to_dict())

    def load(self):
        """
        Inspired by github.com/vitorfs/bootcamp/blob/master/bootcamp/helpers.py
        """
        parsed_url = urlparse(self.url)
        if not parsed_url.scheme:
            self.url = f"https://{parsed_url.path}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) "
            "AppleWebKit/601.3.9 (KHTML, like Gecko) "
            "Version/9.0.2 Safari/601.3.9"
        }

        try:
            response = requests.get(self.url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return JsonResponse({"message": "URL appears to be invalid"})
        except requests.exceptions.Timeout:
            return JsonResponse({"message": "Error connecting to site"})

        soup = bs4.BeautifulSoup(response.content, features="html.parser")
        ogdata = soup.html.head.find_all(property=re.compile(r"^og"))
        ogdata = {og.get("property")[3:]: og.get("content") for og in ogdata}

        # print(json.dumps(ogdata, indent=2))

        if not ogdata.get("url"):
            ogdata["url"] = response.url

        if not ogdata.get("title"):
            ogdata["title"] = soup.html.title.text

        description = ogdata.get("description")

        if description:
            pass
            # description = description.split("\n", 1)[0]
            # description = re.sub("[\r\t]", " ", description)
            # description = re.sub(" +", " ", description)
            # ogdata["description"] = description.strip()[:255]
        else:
            ogdata["description"] = None
            # description = ""
            # for text in soup.body.find_all(string=True):
            #     is_valid = text.parent.name not in ['script', 'style']
            #     is_valid = is_valid and not isinstance(text, bs4.Comment)
            #     if is_valid:
            #         description += text

        self.domain = urlparse(self.url).netloc

        for x in ["url", "title", "description", "image"]:
            setattr(self, x, ogdata.get(x, None))

        self.type = ogdata.get("type", "website")
        self.type = self.type.rsplit(".", 1)[-1]

        return ogdata
