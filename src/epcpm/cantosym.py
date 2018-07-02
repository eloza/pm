import collections
import io
import textwrap

import attr
import canmatrix.canmatrix
import canmatrix.formats

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.canmodel

builders = epyqlib.utils.general.TypeMap()


def dehumanize_name(name):
    name = name.replace('-', '_')
    return epyqlib.utils.general.spaced_to_upper_camel(name)


@builders(epcpm.canmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        matrix = canmatrix.canmatrix.CanMatrix()
        # TODO: this shouldn't need to be copied from:
        #           canmatrix.sym.load()
        matrix.addFrameDefines("GenMsgCycleTime", 'INT 0 65535')
        matrix.addFrameDefines("Receivable", 'BOOL False True')
        matrix.addFrameDefines("Sendable", 'BOOL False True')
        matrix.addSignalDefines("GenSigStartValue", 'FLOAT -3.4E+038 3.4E+038')
        matrix.addSignalDefines("HexadecimalOutput", 'BOOL False True')
        matrix.addSignalDefines("DisplayDecimalPlaces", 'INT 0 65535')
        matrix.addSignalDefines("LongName", 'STR')

        enumerations = self.collect_enumerations()

        for enumeration in enumerations:
            enumerators = collections.OrderedDict(
                (e.value, dehumanize_name(e.name))
                for e in enumeration.children
            )

            matrix.addValueTable(
                name=dehumanize_name(enumeration.name),
                valueTable=enumerators,
            )

        for child in self.wrapped.children:
            frame = builders.wrap(
                wrapped=child,
                access_levels=self.access_levels,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            matrix.frames.addFrame(frame)

        codec = 'utf-8'

        f = io.BytesIO()
        canmatrix.formats.dump(matrix, f, 'sym', symExportEncoding=codec)
        f.seek(0)

        return f.read().decode(codec)

    def collect_enumerations(self):
        collected = []

        if self.parameter_model is None:
            return collected

        def collect(node, collected):
            is_enumeration = isinstance(
                node,
                (
                    epyqlib.pm.parametermodel.Enumeration,
                    epyqlib.pm.parametermodel.AccessLevels,
                )
            )
            if is_enumeration:
                collected.append(node)

        self.parameter_model.root.traverse(
            call_this=collect,
            payload=collected,
            internal_nodes=True,
        )

        return collected


@builders(epcpm.canmodel.Message)
@attr.s
class Message:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        frame = canmatrix.canmatrix.Frame(
            name=dehumanize_name(self.wrapped.name),
            Id=self.wrapped.identifier,
            extended=self.wrapped.extended,
            dlc=self.wrapped.length,
            comment=self.wrapped.comment,
        )

        if self.wrapped.cycle_time is not None:
            frame.attributes['GenMsgCycleTime'] = str(self.wrapped.cycle_time)

        frame.attributes['Receivable'] = str(self.wrapped.receivable)
        frame.attributes['Sendable'] = str(self.wrapped.sendable)

        for child in self.wrapped.children:
            signal = builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            frame.signals.append(signal)

        return frame


@builders(epcpm.canmodel.Signal)
@attr.s
class Signal:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self, multiplex_id=None, skip_access_level=False):
        extras = {}
        can_find_parameter = (
            self.wrapped.parameter_uuid is not None
            and self.parameter_uuid_finder is not None
        )
        parameter = None
        if can_find_parameter:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            if parameter.minimum is not None:
                extras['min'] = parameter.minimum

            if parameter.maximum is not None:
                extras['max'] = parameter.maximum

            if parameter.comment is not None:
                comment = parameter.comment.strip()
                if len(comment) > 0:
                    extras['comment'] = comment

            handle_access_level = (
                    not skip_access_level
                    and parameter.access_level_uuid is not None
            )
            if handle_access_level:
                access_level = self.parameter_uuid_finder(
                    parameter.access_level_uuid
                )
                if access_level != access_level.tree_parent.default():
                    extras['comment'] = '{} <{}>'.format(
                        extras.get('comment', ''),
                        access_level.name.casefold(),
                    ).strip()

            if parameter.nv_format is not None:
                segments = ['nv']

                nv_flags = ''
                if parameter.nv_cast:
                    nv_flags += 'c'

                segments.append(nv_flags)

                if parameter.nv_factor is not None:
                    segments.append('f{}'.format(parameter.nv_factor))

                segments.append(parameter.nv_format)

                extras['comment'] = '{}  <{}>'.format(
                    extras.get('comment', ''),
                    ':'.join(segments),
                ).strip()

            if parameter.units is not None:
                extras['unit'] = parameter.units

            if parameter.enumeration_uuid is not None:
                enumeration = self.parameter_uuid_finder(
                    parameter.enumeration_uuid,
                )

                extras['enumeration'] = dehumanize_name(enumeration.name)
                extras['values'] = {v: k for k, v in enumeration.items()}

        signal = canmatrix.canmatrix.Signal(
            name=dehumanize_name(self.wrapped.name),
            multiplex=multiplex_id,
            signalSize=self.wrapped.bits,
            is_signed=self.wrapped.signed,
            factor=self.wrapped.factor,
            startBit=self.wrapped.start_bit,
            calc_min_for_none=False,
            calc_max_for_none=False,
            **extras,
        )

        if parameter is not None:
            attributes = signal.attributes

            attributes['LongName'] = parameter.name
            attributes['HexadecimalOutput'] = parameter.display_hexadecimal

            if parameter.default is not None:
                # TODO: it seems this shouldn't be needed...  0754397432978432
                attributes['GenSigStartValue'] = (
                    parameter.default / self.wrapped.factor
                )

            if parameter.decimal_places is not None:
                attributes['DisplayDecimalPlaces'] = parameter.decimal_places

        return signal


@builders(epcpm.canmodel.MultiplexedMessage)
@attr.s
class MultiplexedMessage:
    wrapped = attr.ib()
    access_levels = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        common_signals = []
        not_signals = []
        for child in self.wrapped.children[1:]:
            if isinstance(child, epcpm.canmodel.Signal):
                common_signals.append(child)
            else:
                not_signals.append(child)

        frame = canmatrix.canmatrix.Frame(
            name=dehumanize_name(self.wrapped.name),
            Id=self.wrapped.identifier,
            extended=self.wrapped.extended,
            dlc=not_signals[0].length,
            comment=self.wrapped.comment,
            attributes={
                'Receivable': str(self.wrapped.receivable),
                'Sendable': str(self.wrapped.sendable),
            }
        )

        cycle_time = not_signals[0].cycle_time
        if cycle_time is not None:
            frame.attributes['GenMsgCycleTime'] = str(cycle_time)

        if len(self.wrapped.children) == 0:
            return frame

        mux_signal = builders.wrap(
            wrapped=self.wrapped.children[0],
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen(
            multiplex_id='Multiplexor',
        )
        frame.signals.append(mux_signal)

        for multiplexer in not_signals:
            if multiplexer.comment is not None:
                mux_signal.comments[multiplexer.identifier] = (
                    multiplexer.comment
                )

            for signal in common_signals:
                matrix_signal = builders.wrap(
                    wrapped=signal,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                )
                frame.signals.append(matrix_signal)

            frame.mux_names[multiplexer.identifier] = (
                dehumanize_name(multiplexer.name)
            )

            def param_special(signal):
                folded = signal.name.casefold()

                return folded.startswith('read param - ') or folded == 'meta'

            signal_access_levels = set()

            for signal in multiplexer.children:
                if param_special(signal):
                    continue

                parameter = self.parameter_uuid_finder(signal.parameter_uuid)
                uuid = parameter.access_level_uuid

                if uuid is None:
                    access_level = self.access_levels.default()
                else:
                    access_level = self.parameter_uuid_finder(uuid)

                signal_access_levels.add(access_level)

            all_access_levels_match = len(signal_access_levels) == 1

            if all_access_levels_match:
                access_level = signal_access_levels.pop()
                if access_level != access_level.tree_parent.default():
                    mux_signal.comments[multiplexer.identifier] = (
                        '{} <{}>'.format(
                            mux_signal.comments.get(multiplexer.identifier, ''),
                            access_level.name.casefold(),
                        ).strip()
                    )

            for signal in multiplexer.children:
                signal = builders.wrap(
                    wrapped=signal,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                ).gen(
                    multiplex_id=multiplexer.identifier,
                    skip_access_level=all_access_levels_match,
                )

                frame.signals.append(signal)

        return frame