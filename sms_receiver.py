from datetime import timezone, datetime
from io import StringIO
import json

from flask import Flask, request, session, Response
import jinja2

APP = Flask(__name__)


class LoggingMiddleware(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, environ, resp):
        errorlog = environ['wsgi.errors']

        length = int(environ.get('CONTENT_LENGTH', '0'))
        body = StringIO(environ['wsgi.input'].read(length).decode('utf-8'))
        environ['wsgi.input'] = body
        req = {k: v for k, v in environ.items() if 'HTTP' in k}
        req['REQUEST_BODY'] = str(body.getvalue())
        print(json.dumps({'request': req}), file=errorlog)

        def log_response(status, headers, *args):
            print(json.dumps({'reponse': {'status': status, 'headers': headers}}), file=errorlog)
            return resp(status, headers, *args)

        return self._app(environ, log_response)


SMSCOL = list()


@APP.route('/api/v1/sms', methods=['POST'])
def receive_sms():
    global SMSCOL
    # If we can't parse the data, then just shove it in there and let
    parse_funcs = [
        lambda x: json.loads(x.data.encode('utf-8')), lambda x: dict(x.form), lambda x: list()[4], lambda x: {
            'message': x.data.encode('utf-8')
        }
    ]
    for pfn in parse_funcs:
        sms = parse_funcs[-1](request)
        try:
            sms = pfn(request)
            break
        except:
            pass
    received_time = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    sms['ReceivedTime'] = received_time
    SMSCOL.insert(0, sms)
    # We only keep the last 250 SMS's
    SMSCOL = SMSCOL[:250]
    response = Response("<Response></Response>")
    return response


@APP.route('/api/v1/sms/search', methods=['GET'])
@APP.route('/api/v1/sms/find', methods=['GET'])
def search():
    '''
    :param to_number: Limits messages returned to only those with a `To` field
                      containing `to_number`
    :param body_contains: Limits messages to only those where
                          `body_contains in sms.body.lowercase()`
    :param received_gt: Limits messages to only those where `ReceivedTime` is
                        greater than `received_gt`
    :param received_lt: Limits messages to only those where `ReceivedTime` is
                        less than `received_lt`
    '''
    global SMSCOL
    results = list()
    for sms in SMSCOL:
        if not request.args.get('to_number', '') in sms.get('To', ''):
            continue
        if not request.args.get('body_contains', '') in sms.get('Body', ''):
            continue
        rt = sms['ReceivedTime']
        received_gt = int(request.args.get('received_gt', rt - 1))
        received_lt = int(request.args.get('received_lt', rt + 1))
        if not sms['ReceivedTime'] > received_gt:
            continue
        if not sms['ReceivedTime'] < received_lt:
            continue
        results.append(sms)
    return Response(json.dumps(results), content_type='application/json')


@APP.route('/api/v1/sms/jinja_search', methods=['POST'])
def jinja_search():
    '''
    Uses the entire body of the POST as a Jinja template which is evaluated in
    order to filter in/out each result. Allows for super custom queries and
    recieving super custom messages.
    '''
    global SMSCOL
    results = list()
    filt = request.data
    for sms in SMSCOL:
        tmpl = jinja2.Template(filt.decode('utf-8'))
        should_include = tmpl.render(sms=sms)
        if should_include.strip():
            results.append(sms)
    return Response(json.dumps(results), content_type='application/json')


@APP.route('/api/v1/sms/', methods=['GET'])
def view_sms():
    global SMSCOL
    style = "table {margin-top: 3rem;font-family:monospace;}"
    view = '''<!DOCTYPE HTML>
    <html>
        <head>
            <title>SMS received</title>
            <style>{}</style>
        </head>
        <body>{}</body>
    </html>
    '''

    def sms_to_table(sms):
        table = "<table><tbody>{}</tbody></table>"
        keys = sorted(sms.keys())
        rows = list()
        for k in keys:
            rows.append('<tr><td>{}</td><td>{}</td></tr>'.format(k, sms[k]))
        table = table.format('\n'.join(rows))
        return table

    return view.format(style, '\n'.join(sms_to_table(sms) for sms in SMSCOL))


if __name__ == '__main__':
    APP.wsgi_app = LoggingMiddleware(APP.wsgi_app)
    APP.debug = True
    APP.run('127.0.0.1', port=9002, threaded=False)
