import aenum
from collections import OrderedDict, namedtuple
import copy
import enum
import logging

import untangle

from . import constants as fc, exceptions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

FixDictFieldSpec = namedtuple(
    'FixDictField', ['tag', 'name', 'type', 'values'])
FixDictFieldValue = namedtuple(
    'FixDictFieldValue', ['enum', 'description'])
FixDictMessage = namedtuple(
    'FixDictMessage', ['name', 'msg_type', 'fields'])
FixDictFieldReference = namedtuple(
    'FixDictFieldReference',
    ['tag', 'required', 'group', 'group_index', 'groupfields'])


class FixDictFieldReference2:

    def __init__(
        self,
        tag,
        required,
        group=None,
        group_index=None,
        groupfields=None
    ):
        self.tag = tag
        self.required = required
        self.group = group
        self.group_index = group_index
        self.groupfields = groupfields or []

    def __str__(self):
        return '<Field: {}({}) Group: {}: Group Index: {}>'.format(
            self.tag, self.tag.name, self.group, self.group_index)

    def __repr__(self):
        return self.__str__()


class CustomFixField(enum.IntEnum):
    pass


class FixXMLParser:

    def __init__(self):
        self.tags = None
        self.custom_fields = CustomFixField
        self.components = OrderedDict()

    @staticmethod
    def parse_version(root):
        version = 'FIX.{}.{}'.format(root['major'], root['minor'])
        try:
            version = fc.FixVersion(version)
        except ValueError:
            raise exceptions.UnsupportedVersion
        return version

    def parse_tag(self, name_or_number):
        for _tags in [
            self.tags,
            self.custom_fields
        ]:
            try:
                if isinstance(name_or_number, int):
                    tag = _tags(name_or_number)
                else:
                    tag = _tags[name_or_number]
                break
            except (KeyError, ValueError):
                continue
        else:
            raise ValueError(
                '{} is not a standard FIX field, nor is it '
                'specified as a custom field in your dictionary. '
                'Please check you dictionary for errors'
                ''.format(name_or_number)
            )

        return tag

    @staticmethod
    def parse_field_spec_values(field):
        if not hasattr(field, 'value'):
            return {}
        parsed = OrderedDict()
        for v in field.children:
            parsed[v['enum']] = FixDictFieldValue(
                v['enum'], v['description'])
        return parsed

    def parse_field_spec(self, fields):
        parsed = OrderedDict()
        for f in fields.children:
            tag = int(f['number'])
            try:
                tag = self.parse_tag(tag)
            except ValueError:
                if 5000 <= tag <= 9999:
                    aenum.extend_enum(self.custom_fields, f['name'], tag)
                    tag = self.custom_fields(tag)
                else:
                    raise exceptions.InvalidFixDictTag
            values = self.parse_field_spec_values(f)
            parsed[tag] = FixDictFieldSpec(f['name'], tag, f['type'], values)
        return parsed

    def has_component_ref(self, node):
        for c in node.children:
            if c._name == 'component':
                return True
            if c.children:
                return self.has_component_ref(c)
        return False

    def parse_group(self, node):
        groupfield = self.parse_field(node)
        cfields = self.parse_children(node)
        # only want direct descendents
        i = 0
        for f in cfields:
            if f.group is None:
                groupfield.groupfields.append(f.tag)
                f.group = groupfield.tag
                f.group_index = i
                i += 1
        return [groupfield, *cfields]

    def parse_field(self, node):
        tag = self.parse_tag(node['name'])
        return FixDictFieldReference2(
            tag=tag,
            required=node['required'] == 'Y',
        )

    def parse_children(self, node):
        fields = []
        for c in node.children:
            pc = self.parse_element(c)
            if isinstance(pc, list):
                fields.extend(pc)
            else:
                fields.append(pc)
        return fields

    def parse_element(self, node):
        return getattr(
            self, 'parse_{}'.format(node._name)
        )(node)

    def parse_message(self, node):
        fields = self.parse_children(node)
        fields = OrderedDict([(f.tag, f) for f in fields])
        return FixDictMessage(
            name=node['name'],
            msg_type=node['msgtype'],
            fields=fields
        )

    def parse_component(self, node):
        try:
            return copy.deepcopy(
                self.components[node['name']])
        except (TypeError, KeyError):
            return self.parse_children(node)

    def parse_component_spec(self, node):
        has_ref = []
        # filter out any components specs with component refs
        for c in node.children:
            if self.has_component_ref(c):
                has_ref.append(c)
            else:
                self.components[c['name']] = self.parse_component(c)
        for c in has_ref:
            self.components[c['name']] = self.parse_component(c)
        return self.components

    def parse_block(self, node):
        fields = self.parse_children(node)
        return OrderedDict([(f.tag, f) for f in fields])

    def parse_messages(self, node):
        fields = self.parse_children(node)
        return OrderedDict([(f.msg_type, f) for f in fields])

    def parse(self, path):

        doc = untangle.parse(path)
        doc = doc.fix

        version = self.parse_version(doc)
        self.tags = getattr(fc.FixTag, version.name)
        field_spec = self.parse_field_spec(doc.fields)

        components = self.parse_component_spec(doc.components)
        header = self.parse_block(doc.header)
        trailer = self.parse_block(doc.trailer)
        messages = self.parse_messages(doc.messages)

        return FixDictionary(
            version=version,
            tags=self.tags,
            header=header,
            trailer=trailer,
            field_spec=field_spec,
            custom_fields=self.custom_fields,
            components=components,
            messages=messages
        )


class FixDictionary:

    class GroupTracker:

        def __init__(self, field, no_entries):
            self.field = field
            self.no_entries = no_entries
            self.delimiter = field.groupfields[0]
            self.entry_count = 0
            self.current_entry = []

        def new_entry(self):
            self.entry_count += 1
            self.current_entry = []

        def is_complete(self):
            return self.entry_count == self.no_entries

    def __init__(
        self,
        version,
        tags,
        header,
        trailer,
        messages,
        components,
        field_spec,
        custom_fields
    ):
        self.version = version
        self.tags = tags
        self.header = header
        self.trailer = trailer
        self.messages = messages
        self.components = components
        self.field_spec = field_spec
        self.custom_fields = custom_fields

    def raise_out_of_order(self, group):
        raise ValueError(
            'Fields out of order for group {}'
            ''.format(group.field.tag))

    def raise_duplicate_field(self, tag, group):
        raise ValueError(
            'Duplicate field {} for group {}'
            ''.format(tag, group.field.tag)
        )

    def raise_missing_delimiter(self, group):
        raise ValueError(
            'Field {} is the first field in repeating '
            'group {}, it is required'
            ''.format(group.delimiter.name, group.field.tag.name)
        )

    def raise_entries_exceeded(self, group):
        raise ValueError(
            'Too many entries {} for repeating group {} with value {}'
            ''.format(group.entry_count + 1, group.field.tag, group.no_entries)
        )

    def raise_too_few_entries(self, group):
        raise ValueError(
            'Too few entries {} for repeating group {} with value {}'
            ''.format(group.entry_count, group.field.tag.name, group.no_entries)
        )

    def validate_field_value(self, field, val):
        field_spec = self.field_spec[field]
        if field_spec.values:
            if val not in field_spec.values:
                raise ValueError(
                    '{} is not a supported value for field {}'
                    ''.format(val, field.name)
                )
        else:
            if not isinstance(val, field_spec.type):
                raise TypeError(
                    'Expected {} to be of type {}, but instead got {}'
                    ''.format(field.name, field_spec.type, type(val))
                )

    def validate_field(self, tag):
        if tag not in self.field_spec:
            raise ValueError(
                'Field {} ({}) is not supported by this dictionary'
                ''.format(tag.name, tag))

    def validate_msg_type(self, msg):
        msg_type = msg.get(self.tags.MsgType)
        msg_type = fc.FixMsgType(msg_type)
        if not self.messages.get(msg_type):
            raise ValueError(
                'Message type {} is not supported by the dictionary',
                ''.format(msg_type)
            )
        return msg_type

    def validate_msg_field(self, msg_type, tag):
        msg_def = self.messages.get(msg_type)
        field_def = msg_def.fields.get(tag, self.header.get(tag))
        if not field_def:
            self.validate_field(tag)
            raise ValueError(
                'Field {} ({}) is not supported by message type {}'
                ''.format(tag.name, tag, msg_type))
        return field_def

    def validate_msg(self, msg):
        msg_type = self.validate_msg_type(msg)
        groups = []
        for tag, val in msg:
            tag = self.tags(tag)
            field_def = self.validate_msg_field(msg_type, tag)

            if field_def.groupfields:
                groups.append(self.GroupTracker(
                    field=field_def, no_entries=int(val)))
                continue

            if groups:
                current_group = groups[-1]
                if field_def.group != current_group.field.tag:
                    if current_group.entry_count == 0:
                        self.raise_missing_delimiter(current_group)
                    if current_group.entry_count < current_group.no_entries:
                        self.raise_too_few_entries(current_group)
                    groups = groups[:-1]
                    continue

                if not current_group.current_entry:
                    if tag != current_group.delimiter:
                        self.raise_missing_delimiter(current_group)
                    current_group.new_entry()
                    current_group.current_entry.append(field_def)
                    continue

                if field_def in current_group.current_entry:
                    if tag != current_group.delimiter:
                        self.raise_duplicate_field(tag, current_group)
                    current_group.new_entry()
                    if current_group.entry_count > current_group.no_entries:
                        self.raise_entries_exceeded(current_group)
                else:
                    last_field = current_group.current_entry[-1]
                    if field_def.group_index < last_field.group_index:
                        self.raise_out_of_order(current_group)

                current_group.current_entry.append(field_def)

    @classmethod
    def from_xml(cls, path):
        xml_parser = FixXMLParser()
        return xml_parser.parse(path)
