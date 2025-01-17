# --------------------------------------------------------------------------
# Copyright (c) 2012, University of Cambridge Computing Service
#
# This file is part of the Lookup/Ibis client library.
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Dean Rasheed (dev-group@ucs.cam.ac.uk)
# --------------------------------------------------------------------------

"""
Connection classes to connect to the Lookup/Ibis web service and allow API
methods to be invoked.
"""

from datetime import date
import urllib.parse
import warnings

import requests

from .dto import IbisDto, IbisError, IbisResult, IbisResultParser

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class IbisException(Exception):
    """
    Exception thrown when a web service API method fails. This is wrapper
    around the :any:`IbisError` object returned by the server, which contains
    the full details of what went wrong.

    .. codeauthor:: Dean Rasheed (dev-group@ucs.cam.ac.uk)
    """
    def __init__(self, error):
        Exception.__init__(self, error.message)
        self.error = error

    def get_error(self):
        """
        Returns the underlying error from the server.

        **Returns**
          :any:`IbisError`
            The underlying error from the server.
        """
        return self.error


class IbisClientConnection:
    """
    Class to connect to the Lookup/Ibis server and invoke web service API
    methods.

    If you want to customise behaviour such as TLS verification, pass a custom
    requests.Session object in via the `session` parameter.

    .. codeauthor:: Dean Rasheed (dev-group@ucs.cam.ac.uk)
    """
    def __init__(self, host, port, url_base, check_certs, *, session=None):
        self.host = host
        self.port = port
        self.url_base = url_base
        self.session = requests.Session() if session is None else session

        if not self.url_base.startswith("/"):
            self.url_base = "/%s" % self.url_base
        if not self.url_base.endswith("/"):
            self.url_base = "%s/" % self.url_base

        if not check_certs:
            self.session.verify = False
            warnings.warn(
                "Setting check_certs=False is dangerous and may not be "
                "supported in a future release of ibisclient.",
                DeprecationWarning
            )

        self.username = None
        self.password = None
        self.set_username("anonymous")

    def _update_authorization(self):
        self.session.auth = (
            self.username if self.username is not None else "anonymous",
            self.password if self.password is not None else ""
        )

    def set_username(self, username):
        """
        Set the username to use when connecting to the Lookup/Ibis web
        service. By default connections are anonymous, which gives read-only
        access. This method enables authentication as a group, using the
        group's password, which gives read/write access and also access to
        certain non-public data, based on the group's privileges.

        This method may be called at any time, and affects all subsequent
        access using this connection, but does not affect any other
        :any:`IbisClientConnection` objects.

        **Parameters**
          `username` : str
            [required] The username to connect as. This should either be
            ``"anonymous"`` (the default) or the name of a group.
        """
        self.username = username
        self._update_authorization()

    def set_password(self, password):
        """
        Set the password to use when connecting to the Lookup/Ibis web
        service. This is only necessary when connecting as a group, in
        which case it should be that group's password.

        **Parameters**
          `password` : str
            [required] The group password.
        """
        self.password = password
        self._update_authorization()

    def _params_to_strings(self, params):
        """
        Convert the values in a parameter map into strings suitable for
        sending to the server. Any null values will be omitted.
        """
        new_params = {}
        for key, value in params.items():
            if value is not None:
                if isinstance(value, bool):
                    if value:
                        new_params[key] = "true"
                    else:
                        new_params[key] = "false"
                elif isinstance(value, date):
                    new_params[key] = "%02d %s %d" % (value.day,
                                                      _MONTHS[value.month-1],
                                                      value.year)
                elif isinstance(value, list) or isinstance(value, tuple):
                    new_params[key] = ",".join(value)
                elif isinstance(value, IbisDto):
                    new_params[key] = value.encoded_string()
                elif not isinstance(value, str):
                    new_params[key] = str(value)
                else:
                    new_params[key] = value

        return new_params

    def _build_url(self, path, path_params={}, query_params={}):
        """
        Build the full URL needed to invoke a method in the web service API.

        The path may contain standard Python format specifiers, which will
        be substituted from the path parameters (suitably URL-encoded). Thus
        for example, given the following arguments:

            * path = "api/v1/person/%(scheme)s/%(identifier)s"
            * path_params = {"scheme": "crsid", "identifier": "dar17"}
            * query_params = {"fetch": "email,title"}

        this method will create a URL like the following:

            api/v1/person/crsid/dar17?fetch=email%2Ctitle

        Note that all parameter values are automatically URL-encoded.
        """
        for key, value in path_params.items():
            path_params[key] = urllib.parse.quote_plus(value)
        path = path % path_params

        if "flatten" not in query_params:
            query_params["flatten"] = "true"
        path += "?%s" % urllib.parse.urlencode(query_params)

        if path.startswith("/"):
            return "%s%s" % (self.url_base, path[1:])
        return "%s%s" % (self.url_base, path)

    def invoke_method(self, method, path, path_params={},
                      query_params={}, form_params={}):
        """
        Invoke a web service GET, POST, PUT or DELETE method.

        The path should be the relative path to the method with standard
        Python format specifiers for any path parameters, for example
        ``"/api/v1/person/%(scheme)s/%(identifier)s"``. Any path parameters
        specified are then substituted into the path.

        **Parameters**
          `method` : str
            [required] The method type (``"GET"``, ``"POST"``, ``"PUT"`` or
            ``"DELETE"``).

          `path` : str
            [required] The path to the method to invoke.

          `path_params` : dict
            [optional] Any path parameters that should be inserted into the
            path in place of any format specifiers.

          `query_params` : dict
            [optional] Any query parameters to add as part of the URL's query
            string.

          `form_params` : dict
            [optional] Any form parameters to submit.

        **Returns**
          :any:`IbisResult`
            The result of invoking the method.
        """
        path_params = self._params_to_strings(path_params)
        query_params = self._params_to_strings(query_params)
        form_params = self._params_to_strings(form_params)

        url = "https://%s:%s%s" % (
            self.host, self.port,
            self._build_url(path, path_params, query_params)
        )
        headers = {"Accept": "application/xml"}

        if len(form_params) > 0:
            response = self.session.request(
                method, url, data=form_params, headers=headers)
        else:
            response = self.session.request(method, url, headers=headers)

        content_type = response.headers["Content-type"]
        if content_type != "application/xml":
            error = IbisError({"status": response.status_code,
                               "code": response.reason})
            error.message = "Unexpected result from server"
            error.details = response.text

            result = IbisResult()
            result.error = error

            return result

        parser = IbisResultParser()
        result = parser.parse_xml(response.content)

        return result


def createConnection():
    """
    Create an IbisClientConnection to the Lookup/Ibis web service API at
    https://www.lookup.cam.ac.uk/.

    The connection is initially anonymous, but this may be changed using
    its :any:`set_username() <IbisClientConnection.set_username>` and
    :any:`set_password() <IbisClientConnection.set_password>` methods.

    **Returns**
      :any:`IbisClientConnection`
        A new connection to the Lookup server.
    """
    return IbisClientConnection("www.lookup.cam.ac.uk", 443, "", True)


def createTestConnection():
    """
    Create an IbisClientConnection to the Lookup/Ibis test web service API
    at https://lookup-test.srv.uis.cam.ac.uk/.

    The connection is initially anonymous, but this may be changed using
    its :any:`set_username() <IbisClientConnection.set_username>` and
    :any:`set_password() <IbisClientConnection.set_password>` methods.

    .. note::
      This test server is not guaranteed to always be available, and the data
      on it may be out of sync with the data on the live system.

    **Returns**
      :any:`IbisClientConnection`
        A new connection to the Lookup test server.
    """
    return IbisClientConnection("lookup-test.srv.uis.cam.ac.uk", 443, "", True)


def createLocalConnection():
    """
    Create an IbisClientConnection to a Lookup/Ibis web service API running
    locally on https://localhost:8443/ibis/.

    The connection is initially anonymous, but this may be changed using
    its :any:`set_username() <IbisClientConnection.set_username>` and
    :any:`set_password() <IbisClientConnection.set_password>` methods.

    This is intended for testing during development. The local server is
    assumed to be using self-signed certificates, which will not be checked.

    **Returns**
      :any:`IbisClientConnection`
        A new connection to a Lookup server assumed to be running on
        localhost.
    """
    return IbisClientConnection("localhost", 8443, "ibis", False)
