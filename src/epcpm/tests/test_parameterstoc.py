import functools
import os
import textwrap

import click.testing
import pycparser.c_ast
import pycparser.c_generator
import pytest

import epyqlib.attrsmodel

import epcpm.parametermodel
import epcpm.parameterstoc


def disabled_test_exploration():
    path = os.path.join(os.path.dirname(__file__), 'example_parameters.json')

    runner = click.testing.CliRunner()
    runner.isolated_filesystem()
    result = runner.invoke(
        epcpm.parameterstoc.cli,
        [
            '--parameters', path,
        ],
    )

    print(result.output)

    assert result.exit_code == 0


@pytest.mark.skip
def test_exploration():
    path = os.path.join(os.path.dirname(__file__), 'example_parameters.json')

    with open(path) as f:
        epcpm.parameterstoc._cli(parameters=f)


def test_pycparser_exploration_parse():
    sample = '''
    typedef int int16_t;
    typedef int uint16_t;

    enum EnumName
    {
        one=1,
        two=2
    };
    typedef enum EnumName EnumTypedefName;

    struct StructName
    {
        int16_t a;
        uint16_t b;
    };
    typedef struct StructName StructTypedefName;
    
    int16_t array[5];
    '''

    parser = pycparser.CParser()
    ast = parser.parse(sample)

    generator = pycparser.c_generator.CGenerator()

    generator.visit(ast)

    return ast


def test_pycparser_exploration_wrapped():
    top_level = []

    top_level.extend(epcpm.parameterstoc.enum(
        name='EnumName',
        enumerators=(
            ('a', 1),
            ('b', 2),
        ),
    ))

    top_level.extend(epcpm.parameterstoc.struct(
        name='StructName',
        member_decls=(
            epcpm.parameterstoc.Decl(
                type=epcpm.parameterstoc.Type(
                    name=name,
                    type=type,
                )
            )
            for type, name in (
                ('int16_t', 'a'),
                ('uint16_t', 'b'),
            )
        )
    ))

    ast = pycparser.c_ast.FileAST(top_level)

    generator = pycparser.c_generator.CGenerator()

    s = generator.visit(ast)
    assert s == textwrap.dedent('''\
    enum EnumName_e {a = 1, b = 2};
    typedef enum EnumName_e EnumName_et;
    struct StructName_s
    {
      int16_t a;
      uint16_t b;
    };
    typedef struct StructName_s StructName_t;
    ''')


def test_single_layer_group_to_c():
    group = epcpm.parametermodel.Group(
        name='Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        group.append_child(child)

    top_level = epcpm.parameterstoc.build_ast(group)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct GroupName_s
        {
          int16_t parameterA;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef struct GroupName_s GroupName_t;
        ''')


def test_nested_group_to_c():
    inner_inner_group = epcpm.parametermodel.Group(
        name='Inner Inner Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter F',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter G',
        ),
    ]

    for child in children:
        inner_inner_group.append_child(child)

    inner_group = epcpm.parametermodel.Group(
        name='Inner Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter D',
        ),
        inner_inner_group,
        epcpm.parametermodel.Parameter(
            name='Parameter E',
        ),
    ]

    for child in children:
        inner_group.append_child(child)

    outer_group = epcpm.parametermodel.Group(
        name='Outer Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        inner_group,
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        outer_group.append_child(child)

    ast = pycparser.c_ast.FileAST(epcpm.parameterstoc.build_ast(outer_group))
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct InnerInnerGroupName_s
        {
          int16_t parameterF;
          int16_t parameterG;
        };
        typedef struct InnerInnerGroupName_s InnerInnerGroupName_t;
        struct InnerGroupName_s
        {
          int16_t parameterD;
          InnerInnerGroupName_t innerInnerGroupName;
          int16_t parameterE;
        };
        typedef struct InnerGroupName_s InnerGroupName_t;
        struct OuterGroupName_s
        {
          int16_t parameterA;
          InnerGroupName_t innerGroupName;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef struct OuterGroupName_s OuterGroupName_t;
        ''')


def test_array_group_to_c():
    array = epcpm.parametermodel.ArrayGroup(
        name='Array Group Name',
    )

    array.length = 5

    parameter = epcpm.parametermodel.Parameter(name='Array Parameter')
    array.append_child(parameter)

    top_level = epcpm.parameterstoc.build_ast(array)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct ArrayGroupName_s
        {
          int16_t arrayParameter;
        };
        typedef struct ArrayGroupName_s ArrayGroupName_t;
        ''')

    group = epcpm.parametermodel.Group(
        name='Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        array,
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        group.append_child(child)

    top_level = epcpm.parameterstoc.build_ast(group)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct ArrayGroupName_s
        {
          int16_t arrayParameter;
        };
        typedef struct ArrayGroupName_s ArrayGroupName_t;
        typedef ArrayGroupName_t array_name[5] ArrayGroupName_at;
        struct GroupName_s
        {
          int16_t parameterA;
          ArrayGroupName_at arrayGroupName;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef struct GroupName_s GroupName_t;
        ''')


def test_datalogger_a():
    root = epcpm.parametermodel.Root()

    model = epyqlib.attrsmodel.Model(
        root=root,
        columns=epcpm.parametermodel.columns,
    )

    data_logger = epcpm.parametermodel.Group(name='Data Logger')
    root.append_child(data_logger)

    chunks = epcpm.parametermodel.ArrayGroup(name='Chunks', length=16)
    data_logger.append_child(chunks)

    address = epcpm.parametermodel.Parameter(
        name='Address',
        default=0,
    )
    chunks.append_child(address)
    bytes_ = epcpm.parametermodel.Parameter(
        name='Bytes',
        default=0,
    )
    chunks.append_child(bytes_)

    post_trigger_duration = epcpm.parametermodel.Parameter(
        name='Post Trigger Duration',
        default=500,
    )
    data_logger.append_child(post_trigger_duration)

    group = epcpm.parametermodel.Group(name='Group')
    data_logger.append_child(group)

    param = epcpm.parametermodel.Parameter(name='Param')
    group.append_child(param)

    ast = pycparser.c_ast.FileAST(epcpm.parameterstoc.build_ast(data_logger))
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    struct Chunks_s
    {
      int16_t address;
      int16_t bytes;
    };
    typedef struct Chunks_s Chunks_t;
    typedef Chunks_t array_name[16] Chunks_at;
    struct Group_s
    {
      int16_t param;
    };
    typedef struct Group_s Group_t;
    struct DataLogger_s
    {
      Chunks_at chunks;
      int16_t postTriggerDuration;
      Group_t group;
    };
    typedef struct DataLogger_s DataLogger_t;
    ''')

data_logger_structures = '''\
typedef struct
{
    void*	address;
    size_t	bytes;
} DataLogger_Chunk;

#define DATALOGGER_CHUNK_DEFAULTS(...) \
{ \
    .address = 0, \
    .bytes = 0, \
    __VA_ARGS__ \
}

typedef DataLogger_Chunk DataLogger_Chunks[dataLoggerChunkCount];

typedef struct
{
    DataLogger_Chunks chunks;
    uint16_t postTriggerDuration_ms;
} DataLogger_Params;

#define DATALOGGER_PARAMS_DEFAULTS(...) \
{ \
    .chunks = {[0 ... dataLoggerChunkCount-1] = DATALOGGER_CHUNK_DEFAULTS()}, \
    .postTriggerDuration_ms = 500, \
    __VA_ARGS__ \
}
'''


def test_basic_parameter_array():
    array = epcpm.parametermodel.Array(name='Array Name')
    parameter = epcpm.parametermodel.Parameter(name='Parameter Name')

    array.append_child(parameter)

    n = 5

    array.length = n

    builder = epcpm.parameterstoc.builders.wrap(array)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    enum ArrayName_e {ArrayName_ParameterName = 0, ArrayName_NewArrayParameterElement = 1, ArrayName_NewArrayParameterElement = 2, ArrayName_NewArrayParameterElement = 3, ArrayName_NewArrayParameterElement = 4, ArrayName_Count = 5};
    typedef enum ArrayName_e ArrayName_et;
    typedef int16_t ArrayName_t[5];
    ''')


def test_grouped_parameter_array():
    group = epcpm.parametermodel.Group(name='Group Name')
    array = epcpm.parametermodel.Array(name='Array Name')
    parameter = epcpm.parametermodel.Parameter(name='Parameter Name')

    group.append_child(array)
    array.append_child(parameter)

    n = 5

    array.length = n

    builder = epcpm.parameterstoc.builders.wrap(group)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    enum ArrayName_e {ArrayName_ParameterName = 0, ArrayName_NewArrayParameterElement = 1, ArrayName_NewArrayParameterElement = 2, ArrayName_NewArrayParameterElement = 3, ArrayName_NewArrayParameterElement = 4, ArrayName_Count = 5};
    typedef enum ArrayName_e ArrayName_et;
    typedef int16_t ArrayName_t[5];
    struct GroupName_s
    {
      ArrayName_t arrayName;
    };
    typedef struct GroupName_s GroupName_t;
    ''')


def test_line_monitor_params():
    line_monitoring = epcpm.parametermodel.Group(
        name='Line Monitoring',
    )

    frequency_limits = epcpm.parametermodel.Array(
        name='Frequency Limits',
    )
    line_monitoring.append_child(frequency_limits)

    frequency_limit = epcpm.parametermodel.Group(
        name='First',
        type_name='Frequency Limit',
    )
    frequency_limits.append_child(frequency_limit)

    frequency = epcpm.parametermodel.Parameter(
        name='Frequency',
    )
    frequency_limit.append_child(frequency)

    clearing_time = epcpm.parametermodel.Parameter(
        name='Clearing Time',
    )
    frequency_limit.append_child(clearing_time)

    frequency_limits.length = 4
    frequency_limits.children[1].name = 'Second'
    frequency_limits.children[2].name = 'Third'
    frequency_limits.children[3].name = 'Fourth'

    builder = epcpm.parameterstoc.builders.wrap(line_monitoring)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)
    print(f' - - -\n{s}\n - - -')

    assert s == textwrap.dedent('''\
    struct FrequencyLimit_s
    {
      int16_t frequency;
      int16_t clearingTime;
    };
    typedef struct FrequencyLimit_s FrequencyLimit_t;
    enum FrequencyLimits_e {FrequencyLimits_First = 0, FrequencyLimits_Second = 1, FrequencyLimits_Third = 2, FrequencyLimits_Fourth = 3, FrequencyLimits_Count = 4};
    typedef enum FrequencyLimits_e FrequencyLimits_et;
    typedef FrequencyLimit_t FrequencyLimits_t[4];
    struct LineMonitoring_s
    {
      FrequencyLimits_t frequencyLimits;
    };
    typedef struct LineMonitoring_s LineMonitoring_t;
    ''')
