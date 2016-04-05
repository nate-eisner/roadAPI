import datetime
import logging
import logging.handlers
import os
import sys
import thread
from threading import Timer
from xml.etree.ElementTree import Element, tostring
import requests
from daemon import Daemon
from flask import Flask, json, request, Response

app = Flask(__name__)
conditions_url = 'http://www.511wi.gov/web/api/winterroadconditions'
incidents_url = 'http://www.511wi.gov/web/api/incidents'
alerts_url = 'http://www.511wi.gov/web/api/alerts'
key_and_format = '?key=APIKEY!!!!!&format=json'
JSON_conditions = ''
JSON_incidents = ''
JSON_alerts = ''
c_lock = thread.allocate_lock()
i_lock = thread.allocate_lock()
a_lock = thread.allocate_lock()

LOGGING_MSG_FORMAT = '%(name)-14s > [%(levelname)s] [%(asctime)s] : %(message)s'
LOGGING_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(
    level=logging.DEBUG,
    format=LOGGING_MSG_FORMAT,
    datefmt=LOGGING_DATE_FORMAT
)
handler = logging.handlers.TimedRotatingFileHandler("logs/server.log", 'midnight', 1)
handler.suffix = "%Y-%m-%d"
root_logger = logging.getLogger()
root_logger.addHandler(handler)


def xml_response(results, mytype):
    root = Element('data')
    for result in results:
        child = Element(mytype)
        child.text = result
        root.append(child)
    return Response('<?xml version="1.0" encoding="UTF-8"?>' + tostring(root), mimetype='text/xml')


def json_response(results, mytype):
    json_data = []
    for result in results:
        json_data.append({mytype: result})
    return json.dumps(json_data)


def get_all_conditions():
    global JSON_conditions
    try:
        response = requests.get(conditions_url + key_and_format, timeout=40)
        logging.info("conditions - " + str(response.status_code))
        conditions = response.text
        encoding = response.encoding
        c_lock.acquire()
        JSON_conditions = json.loads(conditions.decode(encoding))
        c_lock.release()
        return True
    except Exception as e:
        logging.warning("conditions Error - " + str(e.message) + str(datetime.datetime.now()))
        return False


def get_all_incidents():
    global JSON_incidents
    try:
        response = requests.get(incidents_url + key_and_format, timeout=40)
        logging.info("incidents - " + str(response.status_code))
        conditions = response.text
        encoding = response.encoding
        i_lock.acquire()
        JSON_incidents = json.loads(conditions.decode(encoding))
        i_lock.release()
        return True
    except Exception as e:
        logging.warning("incidents Error - " + str(e.message) + str(datetime.datetime.now()))
        return False


def get_all_alerts():
    global JSON_alerts
    try:
        response = requests.get(alerts_url + key_and_format, timeout=40)
        logging.info("alerts - " + str(response.status_code))
        alerts = response.text
        a_lock.acquire()
        JSON_alerts = json.loads(alerts)
        a_lock.release()
        return True
    except Exception as e:
        logging.warning("alerts Error - " + str(e.message) + str(datetime.datetime.now()))
        return False


@app.route('/')
def hello_world():
    return 'road api is working'


@app.route('/conditions/')
def show_all_conditions():
    c_lock.acquire()
    results = JSON_conditions
    c_lock.release()
    return json_response(results, 'condition')


@app.route('/conditions/<county_name>')
def show_conditions(county_name):
    return_format = request.args.get('format', '')
    results = []
    county_name = county_name.upper()
    c_lock.acquire()
    for roadSeg in JSON_conditions:
        if roadSeg['EndCounty'].upper() == county_name or \
                        roadSeg['StartCounty'].upper() == county_name:
            results.append(str(roadSeg['Condition'] + ' ' + roadSeg['LocationDescription']))
    c_lock.release()
    if 'xml' in return_format:
        return xml_response(results, 'condition')
    else:
        return json_response(results, 'condition')


@app.route('/incidents/')
def show_all_incidents():
    i_lock.acquire()
    results = JSON_incidents
    i_lock.release()
    return json_response(results, 'incident')


@app.route('/incidents/<county_name>')
def show_incidents(county_name):
    return_format = request.args.get('format', '')
    county_name = county_name.upper()
    results = []
    i_lock.acquire()
    for incident in JSON_incidents:
        if incident['CountyName'].upper() == county_name:
            results.append(str(incident['Description']) + ': ' + str(incident['DirectionOfTravel']) + ' ' +
                           str(incident['RoadwayName']) + ' ' + str(incident['Location']))
    i_lock.release()
    if 'xml' in return_format:
        return xml_response(results, 'incident')
    else:
        return json_response(results, 'incident')


@app.route('/alerts/')
def show_all_alerts():
    a_lock.acquire()
    results = JSON_alerts
    a_lock.release()
    return json_response(results, 'alert')


@app.route('/alerts/<county_name>')
def show_alerts(county_name):
    return_format = request.args.get('format', '')
    results = []
    county_name = county_name.upper()
    a_lock.acquire()
    for alert in JSON_alerts:
        for name in alert['CountyNames']:
            if name.upper() == county_name or name.upper() == 'ALL':
                if alert['Message']:
                    message = alert['Message']
                results.append(message)
    a_lock.release()
    if 'xml' in return_format:
        return xml_response(results, 'alert')
    else:
        return json_response(results, 'alert')


def make_thread():
    thread.start_new_thread(get511, ())


def get511():
    success = True
    start = 'getting 511 data - ' + str(datetime.datetime.now())
    logging.info(start)
    success = success and get_all_conditions()
    success = success and get_all_incidents()
    success = success and get_all_alerts()
    end = 'done getting data - ' + str(datetime.datetime.now())
    logging.info(end)
    if success:
        Timer(70, make_thread).start()
    else:
        Timer(30, make_thread).start()
    return


class MyDaemon(Daemon):
    def run(self):
        make_thread()
        print 'Server starting!'
        app.run(host='0.0.0.0')
        logging.info('started server - ' + str(datetime.datetime.now()))


if __name__ == "__main__":
    daemon = MyDaemon(os.getcwd() + '/daemon-511server.pid')
    if len(sys.argv) >= 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
            print 'Server stopped!'
        elif 'restart' == sys.argv[1]:
            daemon.restart()
            print 'Server restarted!'
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
