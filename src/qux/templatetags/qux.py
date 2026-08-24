import datetime
import os
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.contrib.staticfiles.finders import find as staticfiles_find
from django.templatetags.static import static
from django.utils.safestring import mark_safe

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
    except (TypeError, ZeroDivisionError):
        return None


@register.filter
def atleast(value, arg):
    try:
        return arg if arg > value else value
    except TypeError:
        return value


@register.filter(name="min")
def qux_min(value, minvalue):
    try:
        return min(value, minvalue)
    except TypeError:
        return value


@register.filter(name="qux_floatformat_in")
def qux_floatformat_in(value, precision):
    return qux_floatformat(value, precision, "in")


@register.filter(name="qux_floatformat_us")
def qux_floatformat_us(value, precision):
    return qux_floatformat(value, precision, "us")


def qux_floatformat(value, precision, locale):
    try:
        value = Decimal(value)
    except InvalidOperation:
        return value

    if value == 0:
        return "-"

    value = round(value, precision)
    negative = value < 0
    value = abs(value)
    right = value - int(value)
    left = int(value)
    result = ""

    for n, c in enumerate(reversed(str(left))):
        if locale == "in":
            result = f"{c},{result}" if (n > 1 and n % 2 == 1) else f"{c}{result}"
        else:
            result = f"{c},{result}" if (n > 1 and (n + 1) % 3 == 1) else f"{c}{result}"

    if right:
        result = f"{result}{str(right)[1:]}"

    if negative:
        result = f"-{result}"

    return result


@register.filter(name="strip")
def strip(value, stripchar):
    if isinstance(value, str):
        return value.strip(stripchar)

    return value


@register.filter(name="date_before")
def date_before(days):
    dt = datetime.date.today() - datetime.timedelta(days=days)
    return dt.isoformat()


@register.filter(name="addstr")
def addstr(a, b):
    return f"{a}_{b}"


# https://stackoverflow.com/a/36288962/
@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context["request"].GET.copy()
    for kwarg in kwargs:
        if kwarg in query:
            query.pop(kwarg)
    query.update(kwargs)
    return urlencode(query)


GETCONFIG_BLOCKED = {
    "SECRET_KEY",
    "DATABASE_PASSWORD",
    "DATABASES",
    "EMAIL_HOST_PASSWORD",
    "SENDGRID_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET",
}


@register.filter(name="getconfig")
def getconfig(setting: str, default_value: str = None):
    """
    Usage: {{ 'SETTING'|getconfig }}
    :param setting:
    :param default_value:
    :return:
    """
    upper = setting.upper()
    if upper in GETCONFIG_BLOCKED or "SECRET" in upper or "PASSWORD" in upper:
        return default_value
    return getattr(settings, setting, default_value)


# https://stackoverflow.com/a/50630001/
@register.tag
def lineless(parser, token):
    nodelist = parser.parse(("endlineless",))
    parser.delete_first_token()
    return LinelessNode(nodelist)


class LinelessNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        input_str = self.nodelist.render(context)
        output_str = ""
        for line in input_str.splitlines():
            if line.strip():
                output_str = "\n".join((output_str, line))
        return output_str


@register.simple_tag
def qux_static(path, lazy=True, optional=False):
    """Render a <link>/<script> tag for a static asset.

    Args:
        path: Static path, as given to ``{% static %}``.
        lazy: Load without blocking render — ``media="print" onload`` for CSS,
            ``defer`` for JS. Pass False for assets that must apply before first
            paint.
        optional: Render nothing when the file cannot be found. For project
            theme hooks (``css/forms.css`` and friends) that qux references but
            does not ship: under ``ManifestStaticFilesStorage`` a reference to a
            file that was never collected is a hard 404 with no unhashed
            fallback, so a project that supplies no such file would otherwise
            take a broken asset on every page qux renders.

    Returns:
        The markup, or the URL for non-CSS/JS extensions, or "" when
        ``optional`` and the file is absent.
    """
    # Debug-aware min/max switching
    if not settings.DEBUG:
        name, ext = os.path.splitext(path)
        if not name.endswith(".min"):
            min_path = f"{name}.min{ext}"
            if staticfiles_find(min_path):
                path = min_path

    if optional and not staticfiles_find(path):
        return ""

    url = static(path)
    ext = os.path.splitext(path)[1].lower()

    if ext == ".css":
        if lazy:
            return mark_safe(
                f'<link rel="stylesheet" href="{url}" media="print" onload="this.media=\'all\'">'
                f'<noscript><link rel="stylesheet" href="{url}"></noscript>'
            )
        return mark_safe(f'<link rel="stylesheet" href="{url}">')

    if ext == ".js":
        if lazy:
            return mark_safe(f'<script src="{url}" defer></script>')
        return mark_safe(f'<script src="{url}"></script>')

    return mark_safe(url)
