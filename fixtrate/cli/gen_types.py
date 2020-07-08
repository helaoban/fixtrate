from collections import OrderedDict
from inflection import underscore  # type: ignore
import os
import re
import typing as t
import typing_extensions as te
from jinja2 import Environment

from lxml import etree  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(os.path.dirname(HERE), "templates")

if t.TYPE_CHECKING:
    FIXFields = t.Dict[
        t.Tuple[str, str, str],
        t.List[t.Tuple[str, str]]
    ]
    FIXMessages = t.Dict[
        t.Tuple[str, str, str],
        t.List[t.Tuple[str, str]]
    ]

TYPE_MAP = {
    "BOOLEAN": "bool",
    "INT": "int",
    "LENGTH": "int",
    "DAYOFMONTH": "int",
    "NUMINGROUP": "int",
    "SEQNUM": "int",
    "FLOAT": "float",
    "AMT": "Decimal",
    "QTY": "Decimal",
    "PRICE": "Decimal",
    "PRICEOFFSET": "Decimal",
    "DATA": "str",
    "CHAR": "str",
    "STRING": "str",
    "CURRENCY": "str",
    "EXCHANGE": "str",
    "MONTHYEAR": "str",
    "MULTIPLEVALUESTRING": "str",
    "LOCALMKTDATE": "dt.date",
    "UTCDATE": "dt.date",
    "UTCTIMEONLY": "dt.time",
    "UTCTIMESTAMP": "dt.datetime",
}

unit = [
    "",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine"
]
teen = [
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
ten = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]


def camel_to_snake(val: str):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', val).lower()


def to_word(num: str) -> str:
    as_int = int(num)
    if as_int < 10:
        as_word = unit[as_int]
    elif as_int < 20:
        as_word = teen[int(num[0]) - 1]
    else:
        as_word = ten[int(num[0])]
        second = int(num[1])
        if second > 0:
            as_word = as_word + f"_{unit[second]}"
    return as_word


class FIXField(te.TypedDict):
    number: str
    name: str
    type: str
    values: t.List[t.Tuple[str, str]]


FIXFieldRefs = t.Dict[str, bool]


class FIXMessage(te.TypedDict):
    name: str
    category: str
    type: str
    fields: FIXFieldRefs


class FIXSpec(te.TypedDict):
    fields: t.Dict[str, FIXField]
    messages: t.List[FIXMessage]
    header: t.List[t.Tuple[str, bool]]
    trailer: t.List[t.Tuple[str, bool]]
    type_map: t.Dict[str, str]


PATTERN = re.compile(r"^\d+")


def get_required(refs: FIXFieldRefs) -> t.List[str]:
    return [n for n, r in refs.items() if r]


def get_optional(refs: FIXFieldRefs) -> t.List[str]:
    return [n for n, r in refs.items() if not r]


def convert_to_bool(val: str) -> bool:
    if val == "Y":
        return True
    if val == "N":
        return False
    raise ValueError("Value must be on of 'Y' or 'N'")


def get_fix_spec(path: str) -> "FIXSpec":
    tree = etree.parse(path)

    header_tree = tree.xpath("/fix/header/*")
    msg_tree = tree.xpath("/fix/messages/*")
    field_tree = tree.xpath("/fix/fields/*")
    trailer_tree = tree.xpath("/fix/trailer/*")

    for elem in header_tree:
        name = elem.get("name")
        required = elem.get("required")
        is_required = required == "Y"

    msgs: t.List[FIXMessage] = []

    for elem in msg_tree:

        name = elem.get("name")
        type = elem.get("msgtype")
        cat = elem.get("msgcat")

        def _get_fields(
            elem,
            fields: t.Optional[FIXFieldRefs] = None,
        ) -> FIXFieldRefs:
            if fields is None:
                fields = OrderedDict()
            for c in elem.getchildren():
                if c.tag != "field":
                    continue

                name: str = c.get("name")
                required: bool = c.get("required") == "Y"
                is_group = c.tag == "group"

                fields[name] = required

                if is_group:
                    _get_fields(c, fields)

            return fields

        msg_fields = _get_fields(elem)

        msg: FIXMessage = {
            "name": name,
            "type": type,
            "category": cat,
            "fields": msg_fields,
        }

        msgs.append(msg)

    fix_fields: t.Dict[str, FIXField] = OrderedDict()

    for elem in field_tree:
        number = elem.get("number")
        name = elem.get("name")
        type = elem.get("type")

        values = []

        for child in elem.getchildren():
            val = child.get("enum")
            label = child.get("description")

            match = PATTERN.search(label)
            if match is not None:
                num = match.group()
                as_word = to_word(num)
                label, _ = PATTERN.subn(as_word.upper(), label)

            values.append((label, val))

        fix_field: FIXField = {
            "name": name,
            "number": number,
            "type": type,
            "values": values,
        }

        fix_fields[name] = fix_field

    header = []

    for elem in header_tree:
        field_name = elem.get("name")
        is_required = elem.get("required") == "Y"
        header.append((field_name, is_required))

    trailer = []

    for elem in trailer_tree:
        field_name = elem.get("name")
        is_required = elem.get("required") == "Y"
        trailer.append((field_name, is_required))

    type_map = {
        f["name"]: TYPE_MAP[f["type"]]
        for f in fix_fields.values()
    }

    spec: FIXSpec = {
        "fields": fix_fields,
        "messages": msgs,
        "header": header,
        "trailer": trailer,
        "type_map": type_map,
    }

    return spec


jenv = Environment(
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_cls_files(spec: FIXSpec, dir: str) -> None:
    with open(os.path.join(TEMPLATE_DIR, "msg_cls.txt"), "r") as f:
        content = f.read()
    template = jenv.from_string(content)
    for msg in spec["messages"]:
        fn = camel_to_snake(msg["name"]) + ".py"
        fn = os.path.join(dir, fn)
        template.stream(
            msg=msg,
            fields=spec["fields"],
            type_map=spec["type_map"],
            get_required=get_required,
            get_optional=get_optional,
            camel_to_snake=underscore,
        ).dump(fn)


def render_type_file(spec: FIXSpec, dir: str) -> None:
    with open(os.path.join(TEMPLATE_DIR, "types.txt"), "r") as f:
        content = f.read()
    template = jenv.from_string(content)
    fn = os.path.join(dir, "types.py")
    template.stream(
        spec=spec,
    ).dump(fn)


def render_data_file(spec: FIXSpec, dir: str) -> None:
    with open(os.path.join(TEMPLATE_DIR, "data.txt"), "r") as f:
        content = f.read()
    template = jenv.from_string(content)
    fn = os.path.join(dir, "data.py")
    template.stream(
        spec=spec,
        convert_to_bool=convert_to_bool,
    ).dump(fn)


def render_init_file(spec: FIXSpec, dir: str) -> None:
    with open(os.path.join(TEMPLATE_DIR, "init.txt"), "r") as f:
        content = f.read()
    template = jenv.from_string(content)
    fn = os.path.join(dir, "__init__.py")
    template.stream(
        spec=spec,
        camel_to_snake=camel_to_snake,
    ).dump(fn)


def make_output_dir(path: str) -> None:
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    try:
        open(os.path.join(path, "__init__.py"), "x")
    except FileExistsError:
        pass


def generate(spec_path: str, dir: t.Optional[str] = None):
    if dir is None:
        dir = os.getcwd()
    spec = get_fix_spec(spec_path)
    fn = os.path.basename(os.path.normpath(spec_path))
    # TODO this is naive
    spec_name = fn.split(".")[0]
    dest = os.path.join(dir, spec_name)
    make_output_dir(dest)
    render_type_file(spec, dest)
    render_data_file(spec, dest)
    render_cls_files(spec, dest)
    render_init_file(spec, dest)
