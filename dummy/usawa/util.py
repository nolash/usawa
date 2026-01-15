import datetime


def to_datestring(v):
    return datetime.datetime.strftime(v, '%Y-%m-%dT%H:%M:%SZ')
