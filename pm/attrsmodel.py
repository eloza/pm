import decimal
import json
import logging
import uuid

import attr
from PyQt5 import QtCore

import epyqlib.abstractcolumns
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.utils.general

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger()


def attr_uuid():
    return attr.ib(
        default=None,
        convert=lambda x: x if x is None else uuid.UUID(x),
        metadata={'ignore': True}
    )


def to_decimal_or_none(s):
    if s is None:
        return None

    try:
        result = decimal.Decimal(s)
    except decimal.InvalidOperation as e:
        raise ValueError('Invalid number: {}'.format(repr(s))) from e

    return result


def two_state_checkbox(v):
    return v in (QtCore.Qt.Checked, True)


def ignored_attribute_filter(attribute):
    return not attribute.metadata.get('ignore', False)


class Decoder(json.JSONDecoder):
    types = ()

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook,
                         parse_float=decimal.Decimal,
                         parse_int=decimal.Decimal,
                         *args,
                         **kwargs)

    def object_hook(self, obj):
        obj_type = obj.get('_type', None)

        if isinstance(obj, list):
            return obj

        for t in self.types:
            if obj_type == t._type.default:
                obj.pop('_type')
                return t.from_json(obj)

        raise Exception('Unexpected object found: {}'.format(obj))


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, list):
            return obj

        elif type(obj) == epyqlib.treenode.TreeNode:
            if obj.tree_parent is None:
                return [self.default(c) for c in obj.children]

        if isinstance(obj, decimal.Decimal):
            i = int(obj)
            if i == obj:
                d = i
            else:
                d = float(obj)
        elif isinstance(obj, uuid.UUID):
            d = str(obj)
        else:
            d = obj.to_json()

        return d


def check_child_uuids(root):
    def visit(node, uuids):
        if node is root:
            return

        if node.uuid is None:
            while node.uuid is None:
                u = uuid.uuid4()
                if u not in uuids:
                    node.uuid = u
        elif node.uuid in uuids:
            raise Exception('Duplicate uuid found: {}'.format(node.uuid))

        uuids.add(node.uuid)

    root.traverse(call_this=visit, payload=set(), internal_nodes=True)


class Model(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, header_type, parent=None):
        super().__init__(root=root, attrs=True, parent=parent)

        self.headers = [a.name.replace('_', ' ').title()
                        for a in header_type.public_fields]

        self.mime_map = {}

        check_child_uuids(self.root)

    @classmethod
    def from_json_string(cls, s, header_type, types, decoder=Decoder):
        root = epyqlib.treenode.TreeNode()

        # Ugly but maintains the name 'types' both for the parameter
        # and in D.
        t = types
        del types

        class D(Decoder):
            types = t

        children = json.loads(s, cls=D)
        for child in children:
            root.append_child(child)

        return cls(root=root, header_type=header_type)

    def to_json_string(self):
        return json.dumps(self.root, cls=Encoder, indent=4)

    def flags(self, index):
        flags = super().flags(index)

        node = self.node_from_index(index)

        checkable = False

        if node.public_fields[index.column()].convert is two_state_checkbox:
            checkable = True

        if checkable:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif node.public_fields[index.column()].metadata.get('editable', True):
            flags |= QtCore.Qt.ItemIsEditable

        flags |= QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

        return flags

    def data_display(self, index):
        node = self.node_from_index(index)

        if node.public_fields[index.column()].convert is two_state_checkbox:
            return ''

        result = super().data_display(index)

        return str(result)

    def data_edit(self, index):
        result = super().data_edit(index)

        return str(result)

    def data_check_state(self, index):
        node = self.node_from_index(index)

        if node.public_fields[index.column()].convert is two_state_checkbox:
            if node[index.column()]:
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked

        return None

    def setData(self, index, data, role=None):
        node = self.node_from_index(index)

        if role == QtCore.Qt.EditRole:
            convert = node.public_fields[index.column()].convert
            if convert is not None:
                try:
                    converted = convert(data)
                except ValueError:
                    return False
            else:
                converted = data

            node[index.column()] = converted

            self.dataChanged.emit(index, index)
            return True
        elif role == QtCore.Qt.CheckStateRole:
            node[index.column()] = node.public_fields[index.column()].convert(data)

            return True

        return False

    def add_child(self, parent, child):
        row = len(parent.children)
        self.begin_insert_rows(parent, row, row)
        parent.append_child(child)
        self.end_insert_rows()

    def delete(self, node):
        row = node.tree_parent.row_of_child(node)
        self.begin_remove_rows(node.tree_parent, row, row)
        node.tree_parent.remove_child(child=node)
        self.end_remove_rows()

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        import random

        data = bytearray()

        for index in indexes:
            while True:
                key = random.randrange(2**(4*8))

                if key not in self.mime_map:
                    logger.debug('create: {}'.format(key))
                    self.mime_map[key] = index
                    data.extend(key.to_bytes(4, 'big'))
                    break

        m = QtCore.QMimeData()
        m.setData('mine', data)

        return m

    def dropMimeData(self, data, action, row, column, parent):
        logger.debug('\nentering dropMimeData()')
        logger.debug((data, action, row, column, parent))
        new_parent = self.node_from_index(parent)
        if row == -1 and column == -1:
            if parent.isValid():
                row = 0
            else:
                row = len(self.root.children)

        decoded = self.decode_data(bytes(data.data('mine')))
        node = decoded[0]
        if action == QtCore.Qt.MoveAction:
            logger.debug('node name: {}'.format(node.name))
            logger.debug(data, action, row, column, parent)
            logger.debug('dropped on: {}'.format(new_parent.name))

            from_row = node.tree_parent.row_of_child(node)

            success = self.beginMoveRows(
                self.index_from_node(node.tree_parent),
                from_row,
                from_row,
                self.index_from_node(new_parent),
                row
            )

            if not success:
                return False

            node.tree_parent.remove_child(child=node)
            new_parent.insert_child(row, node)

            self.endMoveRows()

            return True

        return False

    def canDropMimeData(self, mime, action, row, column, parent):
        parent = self.node_from_index(parent)
        logger.debug('canDropMimeData: {}: {}'.format(parent.name, row))
        return parent.can_drop_on()

    def decode_data(self, data):
        keys = tuple(int.from_bytes(key, 'big') for key
                     in epyqlib.utils.general.grouper(data, 4))

        nodes = tuple(self.node_from_index(self.mime_map[key])
                      for key in keys)

        return nodes
