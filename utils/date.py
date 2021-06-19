import datetime


def eomonth(dt, nummonths):
    """
    Return the date reflecting the end-of-month for dt
    Result: date
    """
    eomyr = dt.year + ((dt.month + nummonths) // 12)
    eommo = (dt.month + nummonths) % 12
    result = datetime.date(eomyr, eommo + 1, 1) + datetime.timedelta(days=-1)
    return result


def fomonth(dt, nummonths):
    x = eomonth(dt, nummonths - 1)
    return x + datetime.timedelta(days=1)
