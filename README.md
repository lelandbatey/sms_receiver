# SMS Receiver

This service exists to receive postbacks from services such as Twilio and store
them for a short period of time in memory so that other things may see those
messages. This is useful in cases where you want to automate full end-to-end
tests involving making sure real life actual SMS are being sent correctly.


## Install and Run

```
pip install -r requirements.txt
```

Just run the service:

```
python sms_receiver.py
```


## Configure Webhooks

This service has no control over this part, you have to do this yourself. Go to
your SMS gateway provider (Twilio, Openmarket, etc), and set up a phone number
so that when that phone number receives an SMS, your provider will fire off a
webhook to this service via the public internet. Specifically, point it at the
`POST /api/v1/sms/` endpoint.


## Searching Via Jinja Templates

The most powerful way to search is for by making a POST request to the
`/api/v1/sms/jinja_search` endpoint with a body containing a Jinja template.
Construct your Jinja template so that it will only produce an output when some
criteria of the `sms` variable is met. For example, I can get only the list of
messages which have the word 'hello' in the `sms.Body` parameter with the
following example:

```
curl -X POST http://localhost:9002/api/v1/sms/jinja_search -d '{%if 'hello' in sms.Body %}True{%endif%}'
```

## View all received SMS so far

If you'd like to view ALL the SMS messages received so far in your web browser,
visit the `/api/v1/sms` endpoint in your web browser. You'll be given a very
sparse but functional view of all messages the server has received.
