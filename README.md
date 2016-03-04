# Nate's API for the 511 API

The goal of this API is to allow continuous access to 511wi.gov's road information for the ReadyBadger apps. There is rate limiting enabled on their API, only allowing authenticated calls to 1 request per minute for each method. In the end, this would return empty responses to the users once that limit is reached.

### To Run

python 511server.py start

### What does it do?

Nate's API for the API runs the request to 511wi every 70 seconds and caches the results to allow unlimited amount of usage.

### How does it work?

##### Get winter road conditions:
 + ```http://eisner.io:5000/conditions/countyname```
  + Returns JSON Array of strings of conditions for the specified county

##### Get road alerts:
 + ```http://eisner.io:5000/alerts/countyname```
  + Returns JSON Array of strings of alerts for the specified county

##### Get road incidents:
 + ```http://eisner.io:5000/incidents/countyname```
  + Returns JSON Array of strings of incidents for the specified county
