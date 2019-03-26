def fix_timestamp_from_date(date, format="%Y%m%d-%H:%M:%S", precision=0):
    timestamp = date.strftime(format)
    if precision == 3:
        timestamp = "%s.%03d" % (timestamp, date.microsecond / 1000)
    elif precision == 6:
        timestamp = "%s.%06d" % (timestamp, date.microsecond)
    elif precision != 0:
        raise ValueError("Precision should be one of 0, 3 or 6 digits")
    return timestamp


def datestring_from_date(date):
    format = "%Y%m%d"
    return fix_timestamp_from_date(date, format)


def timestring_from_date(date):
    format = "%H:%M:%S"
    return fix_timestamp_from_date(date, format)
