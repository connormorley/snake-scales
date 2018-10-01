from os import path

import cgi
import requests

from snake import config
from snake import error
from snake import fields
from snake import scale


# Global things
API_KEY = config.scale_configs['virustotal']['api_key']
IS_PRIVATE = bool(config.scale_configs['virustotal']['api_private'])

PROXIES = {}
if config.snake_config['http_proxy']:
    PROXIES['http'] = config.snake_config['http_proxy']
if config.snake_config['https_proxy']:
    PROXIES['https'] = config.snake_config['https_proxy']

HEADERS = {
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": config.constants.USER_AGENT
}


# This feature is only available on the private API
if IS_PRIVATE:
    class Upload(scale.Upload):
        def arguments(self):
            return {
                'hash': fields.Str(required=True)
            }

        def info(self):
            return "fetches files from virustotal and uploads them to snake"

        def upload(self, args, working_dir):
            if not API_KEY:
                raise error.InterfaceError("config variable 'api_key' has not been set")

            params = {
                'apikey': API_KEY,
                'hash': args['hash']
            }
            resp = requests.get('https://www.virustotal.com/vtapi/v2/file/download',
                                params=params,
                                headers=HEADERS,
                                proxies=PROXIES,
                                stream=True,
                                timeout=10)
            if resp.status_code == 204:
                raise error.UploadError("request rate limit exceeded")
            elif resp.status_code == 400:
                raise error.UploadError("bad request")
            elif resp.status_code == 403:
                raise error.UploadError("forbidden")
            name = None
            if 'Content-Disposition' in resp.headers:
                _disp, params = cgi.parse_header(resp.headers['Content-Disposition'])
                if 'filename' in params:
                    name = params['filename']
            if not name:
                name = args['hash']
            with open(path.join(working_dir, name), 'wb') as f:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            return name
