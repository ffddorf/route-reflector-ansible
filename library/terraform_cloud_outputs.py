#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import *
from urllib.request import urlopen, Request
from pprint import pprint
import json
import os


class ModuleError(Exception):
    pass


class TerraformCloudOutputsModule:
    def __init__(self, args):
        self.args = args
        self.token = None
        self.init_token()

    def init_token(self):
        path = os.path.expanduser("~/.terraform.d/credentials.tfrc.json")
        with open(path) as f:
            data = json.load(f)
            self.token = data.get("credentials", {}).get(
                "app.terraform.io", {}).get("token")
        if self.token is None:
            self.token = os.environ.get("TF_CLOUD_TOKEN")
        if self.token is None:
            raise ModuleError(
                "Missing Terraform Cloud credential, run `terraform login` or set `TF_CLOUD_TOKEN`")

    def get_outputs(self):
        url = f"https://app.terraform.io/api/v2/workspaces/{self.args['workspace_id']}/current-state-version?include=outputs"
        req = Request(url, headers={"Authorization": f"Bearer {self.token}"})

        with urlopen(req) as resp:
            if resp.status != 200:
                raise ModuleError(f"Invalid status: {resp.status}")

            state_version = json.load(resp)
            output_list = state_version.get("included", [])

            outputs = {}
            for output in output_list:
                attrs = output['attributes']
                if attrs['sensitive'] and not self.args['sensitive']:
                    continue
                outputs[attrs['name']] = attrs['value']
            return outputs


def main():

    arguments = {
        "workspace_id": {
            "required": True,
            "type": "str"
        },
        "sensitive": {
            "default": False,
            "type": "bool"
        },
    }

    ansible_module = AnsibleModule(argument_spec=arguments)

    try:
        module = TerraformCloudOutputsModule(ansible_module.params)
        outputs = module.get_outputs()
        ansible_module.exit_json(changed=False, outputs=outputs)
    except ModuleError as e:
        ansible_module.fail_json(msg=e.str())


if __name__ == '__main__':
    main()
