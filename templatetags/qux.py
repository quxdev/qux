import datetime

from urllib.parse import urlencode

from django import template
from django.contrib.auth.models import User
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except TypeError:
        return None


@register.filter
def divide(value, arg):
    try:
        return value / arg
    except TypeError:
        return None


@register.filter
def atleast(value, arg):
    try:
        return arg if arg > value else value
    except TypeError:
        return value


@register.filter(name="min")
def qux_max(value, minvalue):
    try:
        return min(value, minvalue)
    except TypeError:
        return value


@register.filter(name="max")
def qux_max(value, maxvalue):
    try:
        return max(value, maxvalue)
    except TypeError:
        return value


@register.filter(name="strip")
def strip(value, stripchar):
    if type(value) is str:
        return value.strip(stripchar)
    else:
        return value


@register.filter(name="date_before")
def date_before(days):
    dt = datetime.date.today() - datetime.timedelta(days=days)
    return dt.isoformat()


@register.filter(name="addstr")
def addstr(a, b):
    return '{}_{}'.format(a, b)


@register.filter(name="userclass")
def userclass(user: User):
    if user is None or isinstance(user, str):
        result = 'anonymous'
    elif user.is_superuser:
        result = 'superuser'
    elif user.is_staff:
        result = 'staff'
    elif user.is_authenticated:
        result = 'user'
    else:
        result = 'anonymous'
    return result


# https://stackoverflow.com/a/36288962/
@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    [query.pop(kwarg) for kwarg in kwargs if kwarg in query]
    query.update(kwargs)
    return urlencode(query)


# https://stackoverflow.com/a/50630001/
@register.tag
def lineless(parser, token):
    nodelist = parser.parse(('endlineless',))
    parser.delete_first_token()
    return LinelessNode(nodelist)


class LinelessNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        input_str = self.nodelist.render(context)
        output_str = ''
        for line in input_str.splitlines():
            if line.strip():
                output_str = '\n'.join((output_str, line))
        return output_str
