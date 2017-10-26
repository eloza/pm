import PyQt5.QtCore
import attr
import epyqlib.attrsmodel
import epyqlib.treenode
import epyqlib.utils.general
import epyqlib.utils.qt
import graham
import marshmallow

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@graham.schemify(tag='parameter')
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Parameter(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Parameter',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    type_name = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    # TODO: CAMPid 1342975467516679768543165421
    default = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    minimum = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    maximum = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    nv = attr.ib(
        default=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    read_only = attr.ib(
        default=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    factory = attr.ib(
        default=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, tuple(self.addable_types().values()))

    @PyQt5.QtCore.pyqtProperty('PyQt_PyObject')
    def pyqtify_minimum(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'minimum')

    @pyqtify_minimum.setter
    def pyqtify_minimum(self, value):
        epyqlib.utils.qt.pyqtify_set(self, 'minimum', value)
        if None not in (value, self.maximum):
            if value > self.maximum:
                self.maximum = value

    @PyQt5.QtCore.pyqtProperty('PyQt_PyObject')
    def pyqtify_maximum(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'maximum')

    @pyqtify_maximum.setter
    def pyqtify_maximum(self, value):
        epyqlib.utils.qt.pyqtify_set(self, 'maximum', value)
        if None not in (value, self.minimum):
            if value < self.minimum:
                self.minimum = value

    can_delete = epyqlib.attrsmodel.childless_can_delete


@graham.schemify(tag='group')
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Group(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Group',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    type_name = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                # TODO: would be nice to self reference without a name
                marshmallow.fields.Nested('Group'),
                marshmallow.fields.Nested('Array'),
                marshmallow.fields.Nested(graham.schema(Parameter)),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, tuple(self.addable_types().values()))

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True


@graham.schemify(tag='array_parameter_element')
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original='original',
    field_names=('nv',),
)
@attr.s(hash=False)
class ArrayParameterElement(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Array Parameter Element',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    # TODO: CAMPid 1342975467516679768543165421
    default = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    minimum = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    maximum = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    nv = attr.ib(
        default=False,
        init=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
    )
    uuid = epyqlib.attrsmodel.attr_uuid()
    original = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=epyqlib.attrsmodel.Reference(),
        ),
    )

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


@graham.schemify(tag='array_group_element')
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class ArrayGroupElement(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Array Group Element',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()
    original = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=epyqlib.attrsmodel.Reference(),
        ),
    )

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


class InvalidArrayLength(Exception):
    pass


@graham.schemify(tag='array')
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Array(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Array',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    length = attr.ib(
        default=1,
        convert=int,
    )
    named_enumerators = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Parameter)),
                marshmallow.fields.Nested(graham.schema(ArrayParameterElement)),
                marshmallow.fields.Nested(graham.schema(Group)),
                marshmallow.fields.Nested(graham.schema(ArrayGroupElement)),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    element_types = {
        Parameter: ArrayParameterElement,
        Group: ArrayGroupElement,
    }

    def __attrs_post_init__(self):
        super().__init__()

        self.length = max(1, len(self.children))

        for child in self.children[1:]:
            if self.children[0].uuid != child.original:
                raise epyqlib.attrsmodel.ConsistencyError(
                    'UUID mismatch: {} != {}'.format(
                        self.children[0].uuid,
                        child.original,
                    )
                )

            child.original = self.children[0]

    @property
    def pyqtify_length(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'length')

    @pyqtify_length.setter
    def pyqtify_length(self, value):
        if value < 1:
            raise InvalidArrayLength('Length must be at least 1')

        if self.children is not None:
            if value < len(self.children):
                for row in range(len(self.children) - 1, value - 1, - 1):
                    self.remove_child(row=row)
            elif 1 <= len(self.children) < value:
                for _ in range(value - len(self.children)):
                    original = self.children[0]
                    type_ = self.element_types[type(original)]
                    self.append_child(type_(original=original))

        epyqlib.utils.qt.pyqtify_set(self, 'length', value)

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(
            [*cls.element_types.keys(), *cls.element_types.values()],
        )

    def addable_types(self):
        child_types = {type(child) for child in self.children}

        value_types = self.element_types.keys()

        if len(child_types.intersection(set(value_types))) == 0:
            types = value_types
        else:
            # types = (ArrayElement,)
            types = ()

        return epyqlib.attrsmodel.create_addable_types(types)

    def can_drop_on(self, node):
        return isinstance(node, tuple(self.addable_types().values()))

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        if node not in self.children:
            raise epyqlib.attrsmodel.ConsistencyError(
                'Specified node not found in children'
            )

        if len(self.children) > 1:
            return False

        return True


@graham.schemify(tag='parameter.enumeration')
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class EnumerationParameter(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Enumeration',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        )
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


Root = epyqlib.attrsmodel.Root(
    default_name='Parameters',
    valid_types=(Parameter, Group)
)

types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        Parameter,
        EnumerationParameter,
        Group,
        Array,
        ArrayGroupElement,
        ArrayParameterElement,
    ),
)

columns = epyqlib.attrsmodel.columns(
    (
        (Parameter, 'name'),
        (Group, 'name'),
        (Array, 'name'),
        (ArrayParameterElement, 'name'),
        (ArrayGroupElement, 'name'),
        (EnumerationParameter, 'name'),
    ),
    ((Group, 'type_name'), (Parameter, 'type_name')),
    ((Array, 'length'),),
    ((Array, 'named_enumerators'),),
    ((Parameter, 'default'), (ArrayParameterElement, 'default')),
    ((Parameter, 'minimum'), (ArrayParameterElement, 'minimum')),
    ((Parameter, 'maximum'), (ArrayParameterElement, 'maximum')),
    ((Parameter, 'nv'), (ArrayParameterElement, 'nv')),
    ((Parameter, 'read_only'),),
    ((Parameter, 'factory'),)
)
