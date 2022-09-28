"""Base for other SCRAPI classes."""

# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import json

from typing import Dict
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import json_format  # type: ignore

from proto.marshal.collections import repeated
from proto.marshal.collections import maps
class ScrapiBase:
    """Core Class for managing Auth and other shared functions."""

    global_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/dialogflow",
    ]

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str,str] = None,
        creds: service_account.Credentials =None,
        scope=False,
        agent_id=None,
    ):

        self.scopes = ScrapiBase.global_scopes
        if scope:
            self.scopes += scope

        if creds:
            self.creds = creds
            self.creds.refresh(Request())
            self.token = self.creds.token
        elif creds_path:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=self.scopes
            )
            self.creds.refresh(Request())
            self.token = self.creds.token
        elif creds_dict:
            self.creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.scopes
            )
            self.creds.refresh(Request())
            self.token = self.creds.token
        else:
            self.creds = None
            self.token = None

        if agent_id:
            self.agent_id = agent_id

    @staticmethod
    def _set_region(item_id):
        """Different regions have different API endpoints

        Args:
          item_id: agent/flow/page - any type of long path id like
            `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
          A dictionary containing the api_endpoint to use when 
          instantiating other library client objects, or None
          if the location is "global"
        """
        try:
            location = item_id.split("/")[3]
        except IndexError as err:
            logging.error("IndexError - path too short? %s", item_id)
            raise err

        if location != "global":
            api_endpoint = f"{location}-dialogflow.googleapis.com:443"
            client_options = {"api_endpoint": api_endpoint}
            return client_options

        else:
            return None  # explicit None return when not required

    @staticmethod
    def pbuf_to_dict(pbuf):
        """Extractor of json from a protobuf"""
        blobstr = json_format.MessageToJson(
            pbuf
        )  # i think this returns JSON as a string
        blob = json.loads(blobstr)
        return blob

    @staticmethod
    def cx_object_to_json(cx_object):
        """Response objects have a magical _pb field attached"""
        return ScrapiBase.pbuf_to_dict(cx_object._pb)  # pylint: disable=W0212

    @staticmethod
    def cx_object_to_dict(cx_object):
        """Response objects have a magical _pb field attached"""
        return ScrapiBase.pbuf_to_dict(cx_object._pb)  # pylint: disable=W0212

    @staticmethod
    def extract_payload(msg):
        """Convert to json so we can get at the object"""
        blob = ScrapiBase.cx_object_to_dict(msg)
        return blob.get("payload")  # deref for nesting

    def recurse_proto_repeated_composite(self, repeated_object):
        repeated_list = []
        for item in repeated_object:
            if isinstance(item, repeated.RepeatedComposite):
                item = self.recurse_proto_repeated_composite(item)
                repeated_list.append(item)
            elif isinstance(item, maps.MapComposite):
                item = self.recurse_proto_marshal_to_dict(item)
                repeated_list.append(item)
            else:
                repeated_list.append(item)

        return repeated_list

    def recurse_proto_marshal_to_dict(self, marshal_object):
        new_dict = {}
        for k,v in marshal_object.items():
            if isinstance(v, maps.MapComposite):
                v = self.recurse_proto_marshal_to_dict(v)
            elif isinstance(v, repeated.RepeatedComposite):
                v = self.recurse_proto_repeated_composite(v)
            new_dict[k] = v

        return new_dict
