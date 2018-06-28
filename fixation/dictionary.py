from collections import OrderedDict, namedtuple
import logging

import untangle

from fixation import constants, exceptions


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


FixDictField = namedtuple('FixDictField', ['tag', 'name', 'type', 'values'])
FixDictFieldValue = namedtuple('FixDictFieldValue', ['enum', 'description'])
FixDictMessage = namedtuple('FixDictMessage', ['name', 'msg_type', 'msg_cat', 'fields'])
FixDictComponent = namedtuple('FixDictComponent', ['name', 'fields'])
FixDictGroup = namedtuple('FixDictGroup', ['name', 'required', 'fields'])
FixDictComponentReference = namedtuple('FixDictComponentReference', ['name', 'required'])
FixDictFieldReference = namedtuple('FixDictFieldReference', ['name', 'required'])


class FixDictionary:

    def __init__(self):
        self.version = None
        self.header = OrderedDict()
        self.trailer = OrderedDict()
        self.messages = OrderedDict()
        self.components = OrderedDict()
        self.fields = OrderedDict()

    def parse_block_item(self, block_item):
        name = block_item['name']
        element = block_item._name

        if element == 'message':
            msg_type = block_item['msgtype']
            msg_type = constants.FixMsgType(msg_type.encode())

            fields = OrderedDict()
            for c in block_item.children:
                fields[c['name']] = self.parse_block_item(c)
            return FixDictMessage(
                name=name,
                msg_type=msg_type,
                msg_cat=block_item['msgcat'],
                fields=fields
            )

        required = block_item['required'] == 'Y'

        if element == 'group':
            fields = OrderedDict()
            for c in block_item.children:
                fields[c['name']] = self.parse_block_item(c)
            return FixDictGroup(
                name=name,
                required=required,
                fields=fields
            )

        if element == 'component':
            return FixDictComponentReference(
                name=name,
                required=required
            )

        return FixDictFieldReference(
            name=name,
            required=required
        )

    def parse_block(self, block):
        fields = OrderedDict()
        for c in block.children:
            fields[c['name']] = self.parse_block_item(c)
        return fields

    @staticmethod
    def parse_field_values(values):
        parsed = OrderedDict()
        for v in values:
            enum_repr = v['enum']
            parsed[enum_repr] = FixDictFieldValue(
                enum=enum_repr,
                description=v['description']
            )
        return parsed

    def parse_fields(self, fields):
        parsed = OrderedDict()
        for f in fields.children:
            tag = int(f['number'])
            try:
                tag = constants.FixTag(tag)
            except ValueError:
                if 5000 <= tag <= 9999:
                    pass
                else:
                    raise exceptions.InvalidFixDictTag
            values = {}
            if hasattr(f, 'value'):
                values = self.parse_field_values(f.children)

            parsed[tag] = FixDictField(
                name=f['name'],
                tag=tag,
                type=f['type'],
                values=values
            )
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

        self.header = self.parse_block(doc.header)
        self.trailer = self.parse_block(doc.trailer)
        self.messages = self.parse_block(doc.messages)
        self.fields = self.parse_fields(doc.fields)
