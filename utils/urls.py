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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        }

        try:
            response = requests.get(self.url, timeout=0.9, headers=headers)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return JsonResponse({"message": "URL appears to be invalid"})
        except requests.exceptions.Timeout:
            return JsonResponse({"message": "Error connecting to site"})

        soup = bs4.BeautifulSoup(response.content, features="html.parser")
        ogdata = soup.html.head.find_all(property=re.compile(r"^og"))
        ogdata = {og.get("property")[3:]: og.get("content") for og in ogdata}

        print(ogdata)

        # URL
        if not ogdata.get("url"):
            ogdata["url"] = self.url

        # Title
        if not ogdata.get("title"):
            ogdata["title"] = soup.html.title.text

        description = ogdata.get("description")
        if not description:
            description = ""
            for text in soup.body.find_all(string=True):
                is_valid = text.parent.name not in ["script", "style"]
                is_valid = is_valid and not isinstance(text, bs4.Comment)
                if is_valid:
                    print("---")
                    print(text)
                    print(description.strip())
                    description += text

        description = re.sub("\n|\r|\t", " ", description)
        description = re.sub(" +", " ", description)
        ogdata["description"] = description.strip()[:255]

        for x in ["type", "title", "description", "image"]:
            setattr(self, x, ogdata.get(x, None))

        return ogdata
