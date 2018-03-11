import http.server
import os
import subprocess
import urllib.parse as URL

class ServerException(Exception):
    def __init__(self, message):
        self.message = message

class ResultNoFile(object):
    ''' file or directory does not exist '''
    def test(self, req_handler):
        return not os.path.exists(req_handler.full_path)

    def act(self, req_handler):
        server_err = "'{0}' not found".format(req_handler.url_components.path)
        raise ServerException(server_err)

class ResultEndpoint(object):
    ''' directory contains API endpoints '''
    def is_endpoints_path(self, dirname):
        return os.path.isfile(os.path.join(dirname, '__endpoints__.txt'))

    def test(self, req_handler):
        if os.path.isdir(req_handler.full_path):
            return self.is_endpoints_path(req_handler.full_path)
        else:
            return self.is_endpoints_path(os.path.dirname(req_handler.full_path))

    def act(self, req_handler):
        req_handler.handle_endpoint(req_handler.full_path)

class ResultExistingFile(object):
    ''' file exists '''
    def test(self, req_handler):
        return os.path.isfile(req_handler.full_path)

    def act(self, req_handler):
        req_handler.handle_file()

class ResultDefault(object):
    ''' default case '''
    def test(self, req_handler):
        return True

    def act(self, req_handler):
        raise ServerException("unknown object '{0}'".format(req_handler.path))

class GenericRequestHandler(http.server.BaseHTTPRequestHandler):

    default_page = "{0}"
    error_page = '<html>\n<body>\n<h1>Server Error</h1>\n<p>{0}</p>\n</body>\n</html>\n'

    extensions = {
	    '.css': 'text/css',
        '.html': 'text/html',
        '.txt': 'text/html'
    }

    possible_results = [
        ResultEndpoint(),
        ResultNoFile(),
        ResultExistingFile(),
        ResultDefault()
    ]

    def do_GET(self):
        self.method = 'show'
        self.handle_request(self.query_from_url)

    def do_POST(self):
        self.method = 'new'
        self.handle_request(self.query_from_content)

    def query_from_content(self):
        content_len = int(self.headers.get('content-length'))
        query = self.rfile.read(content_len)
        return query.decode()

    def query_from_url(self):
        return self.url_components.query

    def handle_request(self, set_query):
        try:
            # get the request details
            cleaned_path = URL.unquote_plus(self.path)
            self.url_components = URL.urlparse(cleaned_path)
            self.full_path = os.getcwd() + self.url_components.path
            print(self.full_path)
            print(os.getcwd())
            self.query = set_query()
            # try to handle the request
            for res in self.possible_results:
                req_handler = res
                if req_handler.test(self):
                    req_handler.act(self)
                    break
        except ServerException as err_msg:
            self.handle_error(err_msg)

    def handle_file(self):
        # check if file type is supported
        file_path, file_ext = os.path.splitext(self.full_path)
        if file_ext not in self.extensions.keys():
            err_msg = "'{0}' filetype not supported".format(file_ext)
            raise ServerException(err_msg)
        self.mime_type = self.extensions[file_ext]
        # read the file
        try:
            with open(self.full_path, 'rb') as requested_file:
                content = requested_file.read()
            self.create_page(content)
        except IOError as err_msg:
            server_err = "cannot read file '{0}' [{1}]".format(self.url_components.path, err_msg)
            self.handle_error(server_err)

    def handle_endpoint(self, endpoints_path):
        if os.path.isdir(endpoints_path):
            endpoint_name = os.path.basename(endpoints_path)
            target = ""
        else:
            endpoints_path, target = os.path.split(endpoints_path)
            endpoint_name = os.path.basename(endpoints_path)
        endpoint_name = '{0}{1}.py'.format(self.method, endpoint_name)
        endpoint_path = os.path.join(endpoints_path, endpoint_name)
        results = subprocess.run(['python', endpoint_path, target, self.query], stdout=subprocess.PIPE)
        self.mime_type = 'text/html'
        self.create_page(results.stdout)

    def handle_error(self, err_msg):
        content = self.error_page.format(err_msg)
        self.mime_type = 'text/html'
        self.send_page(content.encode(), 404)

    def create_page(self, msg):
        self.send_page(msg)

    def send_page(self, content, status=200):
        self.send_response(status)
        self.send_header('Content-Type', self.mime_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

HOST_NAME = 'localhost'
PORT_NUM = 55124

http_server = http.server.HTTPServer((HOST_NAME, PORT_NUM), GenericRequestHandler)
http_server.serve_forever()
http_server.close()
