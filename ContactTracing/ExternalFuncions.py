#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import hkdf as hkdf_i
import binascii
import hmac as hmac_i
import numpy
import secrets
import datetime
import time


def hkdf(key, salt, info, output_length):
    f = hkdf_i.Hkdf(salt, key)
    return f.expand(info, output_length)


def hmac(salt, data):
    digest = hmac_i.new(salt, data, "sha256").hexdigest()
    return binascii.a2b_hex(digest)


def truncate(data, len):
    return data[:len]


def day_number(uetime):
    return int(uetime / (60 * 60 * 24))


def time_interval_number(uetime):
    seconds_of_day_number = numpy.uint32(uetime % (60 * 60 * 24))
    return int(seconds_of_day_number / (60 * 10))


def crng(output_length):
    return secrets.token_bytes(output_length)


# extras

def dntin2uetime(day, tin):
    return (day * 60 * 60 * 24) + (tin * 60 * 10)


def datetime2epoch(year=2020, month=1, day=1, hour=0, min=0, sec=0):
    return datetime.datetime(year, month, day, hour, min, sec).timestamp()


def epoch2str(uetime):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(uetime))

