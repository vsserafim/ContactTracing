#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import ContactTracing.ExternalFuncions as ExtFunc


def tracing_key():
    return ExtFunc.crng(32)


def daily_tracing_key(tk, dn):
    return ExtFunc.hkdf(tk, None, "CT-DTK".encode("utf-8") + dn.to_bytes(4, 'little'), 16)


def rolling_proximity_identifier(dtk, tin):
    hmac = ExtFunc.hmac(dtk, "CT-RPI".encode("utf-8") + bytes([tin]))
    return ExtFunc.truncate(hmac, 16)

