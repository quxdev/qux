import os
import json
from typing import Optional

import xmltodict
import dicttoxml


def alchemy_xmltodict(filepath_or_buffer) -> Optional[dict]:
    is_file = os.path.exists(filepath_or_buffer)
    is_buffer = hasattr(filepath_or_buffer, "read")

    if is_file:
        with open(filepath_or_buffer) as xmlfile:
            xmldict = xmltodict.parse(xmlfile.read())
    elif is_buffer:
        xmldict = xmltodict.parse(filepath_or_buffer.read())
    else:
        return

    result = json.loads(json.dumps(xmldict))

    return result


def alchemy_dictoxml(data) -> str:
    """
    Data returned in child elements

    :param data:
    :return:
    """
    result = dicttoxml.dicttoxml(data, attr_type=False, root=False)

    return result


def dict2xml_attr(data, rootnode=None):
    """
    StackOverflow: https://stackoverflow.com/a/16149359/2193381
    Github: https://gist.github.com/reimund/5435343/

    :param data:
    :param rootnode:
    :return:
    """
    wrap = False if rootnode is None or isinstance(data, list) else True
    root = "objects" if rootnode is None else rootnode
    root_singular = root[:-1] if "s" == root[-1] and rootnode is None else root
    xml = ""
    children = []

    if isinstance(data, dict):
        for key, value in dict.items(data):
            if isinstance(value, dict):
                children.append(dict2xml_attr(value, key))
            elif isinstance(value, list):
                children.append(dict2xml_attr(value, key))
            else:
                xml = xml + " " + key + '="' + str(value) + '"'
    else:
        for value in data:
            children.append(dict2xml_attr(value, root_singular))

    end_tag = ">" if 0 < len(children) else "/>"

    if wrap or isinstance(data, dict):
        xml = "<" + root + xml + end_tag

    if 0 < len(children):
        for child in children:
            xml = xml + child

        if wrap or isinstance(data, dict):
            xml = xml + "</" + root + ">"

    return xml
