import datetime
from decimal import Decimal
from decimal import InvalidOperation
from urllib.parse import urlencode

from django import template
from django.conf import settings

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


@register.filter(name="qux_floatformat_in")
def qux_floatformat_in(value, precision):
    qux_floatformat(value, precision, 'in')


@register.filter(name="qux_floatformat_us")
def qux_floatformat_us(value, precision):
    qux_floatformat(value, precision, 'us')


def qux_floatformat(value, precision, locale):
    try:
        value = Decimal(value)
    except InvalidOperation:
        return value

    if value == 0:
        return "-"

    value = round(value, precision)
    right = value - int(value)
    left = int(value)
    result = ""

    for n, c in enumerate(reversed(str(left))):
        if locale == 'in':
            result = f"{c},{result}" if (n > 1 and n % 2 == 1) else f"{c}{result}"
        else:
            result = f"{c},{result}" if (n > 1 and (n + 1) % 3 == 1) else f"{c}{result}"

    if right:
        result = f"{result}{str(right)[1:]}"

    return result


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


# https://stackoverflow.com/a/36288962/
@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    [query.pop(kwarg) for kwarg in kwargs if kwarg in query]
    query.update(kwargs)
    return urlencode(query)


@register.filter(name="getconfig")
def getconfig(setting: str, default_value: str = None):
    """
    Usage: {{ 'SETTING'|getconfig }}
    :param setting:
    :param default_value:
    :return:
    """
    return getattr(settings, setting, default_value)


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
