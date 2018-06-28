import collections
import logging

import untangle

from fixation import constants, exceptions


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FixDictionary:

    def __init__(self):
        self.version = None
        self.header = collections.OrderedDict()
        self.trailer = collections.OrderedDict()
        self.messages = collections.OrderedDict()
        self.components = collections.OrderedDict()
        self.fields = collections.OrderedDict()

    def parse_block_item(self, block_item):

        block_item_type = block_item._name

        data = collections.OrderedDict({
            'type': block_item_type,
            'name': block_item['name'],
            'required': block_item['required'] == 'Y'
        })

        if block_item_type == 'group':
            data['children'] = []
            for child in block_item.children:
                data['children'].append(self.parse_block_item(child))

        return data

    @staticmethod
    def parse_field_values(values):
        parsed = collections.OrderedDict()
        for v in values:
            enum_repr = v['enum']
            parsed[enum_repr] = {
                'enum': enum_repr,
                'description': v['description']
            }
        return parsed

    def parse_fields(self, fields):
        parsed = collections.OrderedDict()
        for f in fields:

            tag = int(f['number'])
            try:
                tag = constants.FixTag(tag)
            except AttributeError:
                raise exceptions.InvalidFixDictTag

            values = {}
            if hasattr(f, 'value'):
                values = self.parse_field_values(f.value)

            parsed[tag] = {
                'tag': tag,
                'type': f['type'],
                'values': values
            }
        return parsed

    def parse_dict_file(self, path):
        doc = untangle.parse(path)

        try:
            doc = doc.fix
        except ValueError:
            raise exceptions.InvalidFixDictTag

        version = 'FIX.{}.{}'.format(doc['major'], doc['minor'])
        try:
            self.version = constants.FixVersion(version)
        except ValueError:
            raise exceptions.UnsupportedVersion

        for child in doc.header.children:
            parsed = self.parse_block_item(child)
            self.header[parsed['name']] = parsed

        for child in doc.trailer.children:
            parsed = self.parse_block_item(child)
            self.trailer[parsed['name']] = parsed

        for child in doc.messages.children:
            parsed = self.parse_block_item(child)
            msg_type = child['msgtype']
            msg_type = constants.FixMsgType(msg_type.encode())
            self.messages[msg_type] = {
                'msg_type': msg_type,
                'msg_cat': child['msg_cat'],
                **parsed
            }

        for child in doc.components.children:
            parsed = self.parse_block_item(child)
            self.header[parsed['name']] = parsed

        self.fields = self.parse_fields(doc.fields.children)
