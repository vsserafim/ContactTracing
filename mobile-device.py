#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import os
import sys
import time
import json
import random
import select
import socket
import binascii
import ContactTracing.ExternalFuncions as ExtFunc
import ContactTracing.KeySchedule as KeySch

tk_filename = "tracingkey.bin"
tk = None

database = {}
database_file = "rpis_database.json"

reported_rpis = []

# Diagnosis Server
host, port = "localhost", 1919


# check if a contagious encounter occurred
def check_c19(dtk, dn):

    dtk = binascii.a2b_hex(dtk)
    dn = int(dn)

    # generate Rolling Proximity Identifiers for each 10min slot
    # for the given Day Tracing Key
    for tin in range(0, 144):

        rpi = KeySch.rolling_proximity_identifier(dtk, tin)
        rpi = binascii.hexlify(rpi).decode('utf-8')

        # skip already reported rpis
        if rpi in reported_rpis:
            continue

        # compare with the collected Rolling Proximity Identifiers
        if rpi in database:

            reported_rpis.append(rpi)

            # "recover" date and time from Day Number and Time Interval Number
            tepoch = ExtFunc.dntin2uetime(dn, tin)

            # report covid contact
            print("COVID-19: rpi=%s %s \"%s\"!"
                  % (rpi, ExtFunc.epoch2str(tepoch), database[rpi]))


# download Rolling Proximity Identifiers for current location (this simulates bluetooth transmission)
# and Diagnosis Keys (dtk, dn). Diagnosis Keys are the only data sent to the server in the real
# protocol implementation.
def download_data(geotag):

    # request download operation
    json_data = {
        'type': 'download',
        'geotag': geotag,
    }

    json_data = json.dumps(json_data)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(json_data, "utf-8"), (host, port))

    # now it is time to read server response
    try:

        sock.setblocking(0)

        while True:

            # wait socket to be ready for reading with 1s timeout
            ready = select.select([sock], [], [], 1)

            # got data
            if ready[0]:

                # read data from socket and decode as json
                json_data = json.loads(str(sock.recv(1024), "utf-8"))

                # got a Diagnosis Key
                if 'dtk' in json_data:
                    local_dtk = KeySch.daily_tracing_key(tk, json_data['dn'])
                    local_dtk = binascii.hexlify(local_dtk).decode('utf -8')

                    # ignoring my own DTKs
                    if local_dtk == json_data['dtk']:
                        continue

                    check_c19(json_data['dtk'], json_data['dn'])

                # just received a RPI via bluetooth
                elif 'rpi' in json_data:

                    # this simulates the receiving device geotagging the received RPI
                    database[json_data['rpi']] = geotag

                    # save the rpi in the local database for future check
                    with open(database_file, 'w') as fd:
                        json.dump(database, fd)

                else:
                    return

            # time out
            else:
                return

    except Exception as e:
        return


# send notification to the Diagnosis Server
def send_notification(daytracing_key, day_number):

    json_data = {
        'type': 'c19',
        'dtk': binascii.hexlify(daytracing_key).decode('utf-8'),
        'dn': day_number
    }

    data = json.dumps(json_data)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(data, "utf-8"), (host, port))


# send data to geolocation simulation (this never happens in the actual protocol implementation)
def send_broadcast(geotag, rolling_proximity_identifier):

    json_data = {
        'type': 'rpi',
        'geotag': geotag,
        'rpi': binascii.hexlify(rolling_proximity_identifier).decode('utf-8'),
    }

    data = json.dumps(json_data)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(data, "utf-8"), (host, port))


# main function
if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("usage: %s <geotag> [<c19>]" % (sys.argv[0]))
        exit(1)

    geotag = sys.argv[1]

    c19 = False
    if len(sys.argv) == 3:
        c19 = sys.argv[2] == 'c19'

    if os.path.isfile(tk_filename):
        # get previous generated tracing key
        with open(tk_filename, 'rb') as fd:
            tk = fd.read()
    else:
        # generate new tracing key and store locally
        print("Generating and saving new Tracing Key...")
        tk = ExtFunc.crng(32)
        with open(tk_filename, 'wb') as fd:
            fd.write(tk)

    if os.path.isfile(database_file):
        with open(database_file, 'r') as fd:
            database = json.load(fd)

    last_printed_rpi = None

    # main loop
    while True:

        tepoch = time.time()

        # get day number
        dn = ExtFunc.day_number(tepoch)

        # generate Day Tracing Key
        dtk = KeySch.daily_tracing_key(tk, dn)

        # get Time Interval Number
        tin = ExtFunc.time_interval_number(tepoch)

        # generate Rolling Proximity Identifier
        # in production should happen each time the Bluetooh MAC address changes
        rpi = KeySch.rolling_proximity_identifier(dtk, tin)

        if last_printed_rpi != rpi:
            last_printed_rpi = rpi
            print("Broadcasting: %s @ %s" % (binascii.hexlify(rpi).decode('utf-8'), geotag))
            sys.stdout.flush()

        # broadcast rpi "via bluetooth"
        send_broadcast(geotag, rpi)

        # send positive notification
        if c19:
            print("Sending notification to Diagnosis Server: dtk=%s dn=%s" % (binascii.hexlify(dtk).decode('utf-8'), dn))
            send_notification(dtk, dn)

        # download and check
        download_data(geotag)

        time.sleep(1)
