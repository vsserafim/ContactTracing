#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import os
import sys
import time
import json
import socketserver
from multiprocessing import Lock

rpi_timeout = 10

database = {}
database_file = 'diagnosis_server_database.json'
database_mutex = Lock()

geotagged_rpi_database = {}
geotagged_rpi_database_mutex = Lock()

host = '0.0.0.0'
port = 1919


class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):

        data = self.request[0].strip()
        socket = self.request[1]

        # remove expired RPIs
        temp_database = geotagged_rpi_database.copy()
        for rpi in temp_database:
            if (temp_database[rpi]['tstamp'] + rpi_timeout) < time.time():
                del geotagged_rpi_database[rpi]
                print('-', end='')
                sys.stdout.flush()

        json_data = None

        # do some basic checks on the received data
        try:
            json_data = json.loads(data)

            if json_data['type'] == 'c19':

                if int(json_data['dn']) > 30000:
                    raise ValueError("DN too high.")

                if len(json_data['dtk']) != 32:
                    raise ValueError("Invalid size for DTK.")

            elif json_data['type'] == 'rpi':

                if len(json_data['rpi']) != 32:
                    raise ValueError("Invalid size for RPI.")

                if len(json_data['geotag']) < 1 or len(json_data['geotag']) > 16:
                    raise ValueError("Invalid size for GEOTAG.")

            elif json_data['type'] == 'download':

                if len(json_data['geotag']) < 1 or len(json_data['geotag']) > 16:
                    raise ValueError("Invalid size for GEOTAG.")

            else:
                return

        except Exception as e:
            json_data = None

        if not json_data:
            print('I', end='')
            sys.stdout.flush()
            return

        # new Diagnosis Key received
        if json_data['type'] == 'c19':
            print('C', end='')
            sys.stdout.flush()

            with database_mutex:
                database[json_data['dtk']] = json_data['dn']

                with open(database_file, 'w') as fd:
                    json.dump(database, fd)

        # RPI received
        elif json_data['type'] == 'rpi':

            geotag = json_data['geotag'].lower()

            # if already exists, ignore
            if json_data['rpi'] in geotagged_rpi_database:
                print('.', end='')
                sys.stdout.flush()
                return

            print('r', end='')
            sys.stdout.flush()

            geotagged_rpi_database[json_data['rpi']] = {
                'geotag': geotag,
                'tstamp': int(time.time())
            }

        # someone is asking the current data
        elif json_data['type'] == 'download':
            print('d', end='')
            sys.stdout.flush()

            with geotagged_rpi_database_mutex:

                geotag = json_data['geotag'].lower()

                for rpi in geotagged_rpi_database:
                    if geotagged_rpi_database[rpi]['geotag'] == geotag:
                        data = json.dumps({
                            'rpi': rpi
                        })
                        socket.sendto(bytes(data, "utf-8"), self.client_address)

            with database_mutex:
                for dtk in database:
                    data = json.dumps({
                        'dtk': dtk,
                        'dn': database[dtk]
                    })
                    socket.sendto(bytes(data, "utf-8"), self.client_address)


if __name__ == "__main__":

    if os.path.isfile(database_file):
        with open(database_file, 'r') as fd:
            database = json.load(fd)

    with socketserver.UDPServer((host, port), UDPHandler) as server:
        server.serve_forever()
