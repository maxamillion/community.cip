#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Red Hat Inc.
# MIT (see COPYING or https://opensource.org/licenses/MIT)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: ensure_tags
short_description: Ensure tags have a specific value
description:
    - Ensure tags have a specific value
author:
- Chris Santiago (@resoluteCoder)
options:
  program:
    description:
      - Name of the program
    required: false
    type: str
  tags:
    description:
      - List of tags with name and value
    required: true
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Name of the tag to target
        required: true
        type: str
      value:
        description:
          - Value to ensure the tag is set to.
          - This value is always a string in the playbook and will by typecast
            accordingly
        required: true
        type: str
notes:
    - some tags will fail due to a value being overwritten after a performing a write
"""

EXAMPLES = """
- name: Ensure tags have a specific value for program - Tag Playground
  industrial.logix.ensure_tags:
    program: 'Tag_Playground'
    tags:
      - name: "modified_by_ansible"
        value: False

- name: Ensure tags have a specific value
  industrial.logix.ensure_tags:
    tags:
      - name: "pi"
        value: 3.14
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.industrial.logix.plugins.module_utils.logix import LogixUtil
from ansible_collections.industrial.logix.plugins.module_utils.tags import (TagCheck, TagValueCheck)


def main():

    tag_options = dict(
        name=dict(required=True, type="str"),
        value=dict(requied=True, type="raw"),
    )

    argspec = dict(
        program=dict(type="str", required=False),
        tags=dict(type="list", options=tag_options, elements="dict", required=True),
    )

    module = AnsibleModule(argument_spec=argspec)

    logix_util = LogixUtil(module)
    tags_results = {}
    has_changed = False

    for tag in module.params['tags']:
        if module.params['program']:
            tag_name = 'Program:%s.%s' % (module.params['program'], tag['name'])
        else:
            tag_name = tag['name']

        tag_value = tag['value']

        tags_results[tag_name] = {}
        tags_results[tag_name]['previous_value'] = ""

        # checks tag permissions and if exists
        tag_check = TagCheck(logix_util, tag_name)
        passed, msg = tag_check.verify()
        if not passed:
            module.fail_json(msg=msg)

        # checks tag values
        plc_tag = logix_util.plc.read(tag_name)
        tags_results[tag_name]['previous_value'] = plc_tag.value

        tag_value_check = TagValueCheck(tag_value, plc_tag)
        tag_values_equal = tag_value_check.compare()
        if tag_values_equal:
            tags_results[tag_name]['no_change_need'] = True
            continue

        write_result = logix_util.plc.write(tag_name, tag_value)

        if write_result.error is not None:
            module.fail_json('%s failed to write' % (tag_name))

        updated_tag_value = logix_util.plc.read(tag_name)
        tag_value_check.update_plc_tag(updated_tag_value)
        tag_values_equal = tag_value_check.compare()
        if not tag_values_equal:
            module.fail_json('%s failed to write' % (tag_name))

        # extra output properties
        tags_results[tag_name]['data_type'] = plc_tag.type
        tags_results[tag_name]['value'] = tag_value
        tags_results[tag_name]['write_result'] = write_result

        has_changed = True

    module.exit_json(msg="Tags values", changed=has_changed, ansible_module_results=tags_results)

if __name__ == "__main__":
    main()
