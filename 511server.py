import datetime
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
key_and_format = 'ADD THE 511 KEY HERE'
JSON_conditions = ''
JSON_incidents = ''
JSON_alerts = ''
c_lock = thread.allocate_lock()
i_lock = thread.allocate_lock()
a_lock = thread.allocate_lock()


def xml_response(results, type):
    root = Element('data')
    for result in results:
        child = Element(type)
        child.text = result
        root.append(child)
    return Response('<?xml version="1.0" encoding="UTF-8"?>' + tostring(root), mimetype='text/xml')


def json_response(results, type):
    json_data = []
    for result in results:
        json_data.append({type: result})
    return json.dumps(json_data)


def get_all_conditions():
    global JSON_conditions
    response = requests.get(conditions_url + key_and_format)
    conditions = response.text
    encoding = response.encoding
    c_lock.acquire()
    JSON_conditions = json.loads(conditions.decode(encoding))
    c_lock.release()


def get_all_incidents():
    global JSON_incidents
    response = requests.get(incidents_url + key_and_format)
    conditions = response.text
    encoding = response.encoding
    i_lock.acquire()
    JSON_incidents = json.loads(conditions.decode(encoding))
    i_lock.release()


def get_all_alerts():
    global JSON_alerts
    response = requests.get(alerts_url + key_and_format)
    alerts = response.text
    JSON_alerts = json.loads(alerts)


@app.route('/')
def hello_world():
    return 'road api is working'


@app.route('/conditions/')
def show_all_conditions():
    return json_response(JSON_conditions)


@app.route('/conditions/<county_name>')
def show_conditions(county_name):
    return_format = request.args.get('format', '')
    results = []
    county_name = county_name.upper()
    for roadSeg in JSON_conditions:
        if roadSeg['EndCounty'].upper() == county_name or \
                        roadSeg['StartCounty'].upper() == county_name:
            results.append(str(roadSeg['Condition'] + ' ' + roadSeg['LocationDescription']))
    if 'xml' in return_format:
        return xml_response(results, 'condition')
    else:
        return json_response(results, 'condition')


@app.route('/incidents/')
def show_all_incidents():
    return json_response(JSON_incidents)


@app.route('/incidents/<county_name>')
def show_incidents(county_name):
    return_format = request.args.get('format', '')
    county_name = county_name.upper()
    results = []
    for incident in JSON_incidents:
        if incident['CountyName'].upper() == county_name:
            results.append(str(incident['Description']) + ': ' + str(incident['DirectionOfTravel']) + ' ' +
                           str(incident['RoadwayName']) + ' ' + str(incident['Location']))
    if 'xml' in return_format:
        return xml_response(results, 'incident')
    else:
        return json_response(results, 'incident')


@app.route('/alerts/')
def show_all_alerts():
    return json_response(JSON_alerts)


@app.route('/alerts/<county_name>')
def show_alerts(county_name):
    return_format = request.args.get('format', '')
    results = []
    county_name = county_name.upper()
    for alert in JSON_alerts:
        for name in alert['CountyNames']:
            if name.upper() == county_name or name.upper() == 'ALL':
                if alert['Message']:
                    message = alert['Message']
                results.append(message)
    if 'xml' in return_format:
        return xml_response(results, 'alert')
    else:
        return json_response(results, 'alert')


def make_thread():
    thread.start_new_thread(get511, ())


def get511():
    try:
        start = 'getting 511 data ' + str(datetime.datetime.now())
        print start
        get_all_conditions()
        get_all_incidents()
        get_all_alerts()
        end = 'done getting data ' + str(datetime.datetime.now())
        print end
        Timer(70, make_thread).start()
    except:
        print "connection error"
        Timer(30, make_thread).start()
    return


class MyDaemon(Daemon):
    def run(self):
        make_thread()
        app.run(host='0.0.0.0')


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-511server.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)