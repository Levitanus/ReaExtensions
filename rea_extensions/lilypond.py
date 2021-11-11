import io
import re
import typing as ty

from fractions import Fraction
from pprint import pprint

import librosa  # type: ignore
import reapy as rpr

from reapy import reascript_api as RPR

EventsDictType = ty.Dict['Position', ty.List['Note']]


class LyExpr:

    @property
    def for_ly(self) -> str:
        return self.__repr__()


class Event(LyExpr):
    ...


class Fractured:

    @property
    def fraction(self) -> Fraction:
        raise NotImplementedError()

    @classmethod
    def normalized(
        cls, fraction: Fraction, head: ty.Tuple[Fraction, ...] = tuple()
    ) -> ty.Tuple[Fraction, ...]:

        def power_of_two(target: int) -> int:
            if target > 1:
                for i in range(1, int(target)):
                    if (2**i >= target):
                        return ty.cast(int, 2**(i - 1))
            elif target in (1, 0):
                return target
            raise ValueError(f"can't resolve numerator: {target}")

        num = fraction.numerator
        den = fraction.denominator

        if den == 1 or num < 5:
            return fraction,
        if num == power_of_two(num):
            return fraction,
        num_nr = power_of_two(num)
        whole = Fraction(num_nr / den)
        remainder = Fraction((num - num_nr) / den)
        if remainder.numerator > 3:
            return cls.normalized(remainder, head=tuple((*head, whole)))
        return remainder, whole, *head

    # @classmethod
    # def normalized_duration(cls,
    #                         fraction: Fraction) -> ty.Tuple['Length', ...]:
    #     return (Length(fr) for fr in cls.normalized(fraction))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fractured):
            return False
        return other.fraction == self.fraction

    def __gt__(self, other: ty.Union[Fraction, 'Fractured']) -> bool:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction > other

    def __lt__(self, other: ty.Union[Fraction, 'Fractured']) -> bool:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction < other

    def __add__(self, other: ty.Union[Fraction, 'Fractured']) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction + other

    def __sub__(self, other: ty.Union[Fraction, 'Fractured']) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction - other

    def __mul__(self, other: ty.Union[Fraction, 'Fractured']) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction * other

    def __div__(self, other: ty.Union[Fraction, 'Fractured']) -> Fraction:
        if isinstance(other, Fractured):
            other = other.fraction
        return self.fraction / other

    def __hash__(self) -> int:
        return hash(self.fraction)


class Length(Fractured, LyExpr):

    def __init__(
        self, length: ty.Union[float, Fraction], tie: bool = False
    ) -> None:
        """
        Parameters
        ----------
        length : Union[float, Fraction]
            if float — in quarter_notes
        take : rpr.Take
            Description
        """
        if isinstance(length, Fraction):
            length = (length.numerator / length.denominator) * 4
        self.length = length
        self.tie = tie

    def __repr__(self) -> str:
        return f'Length({self.length}={self.fraction})'

    @property
    def fraction(self) -> Fraction:
        fr = Fraction(self.length / 4).limit_denominator(128)
        # print(fr, fr.denominator, '//', fr.numerator)
        if fr.denominator >= 1:
            return fr
        return Fraction(1 / (fr.denominator // fr.numerator))

    @classmethod
    def _ly_duration(self, fraction: Fraction) -> str:
        num = fraction.numerator
        den = fraction.denominator

        if den == 1:
            return f'{num}'
        elif num == 1:
            return f'{den}'
        elif num == 3:
            return f'{den//2}.'
        elif num < 5:
            return str(fraction)
        raise ValueError(f'can not render duration {fraction}')

    @property
    def for_ly(self) -> str:
        norm = self.normalized(self.fraction)
        # print(self.fraction, norm, sep=' || ')
        out = "~".join([self._ly_duration(fr) for fr in norm])
        if self.tie:
            out += '~'
        return out


class Position(Fractured):

    def __init__(self, ppq: float, take: rpr.Take) -> None:
        self.ppq_position = ppq
        self.position = round(take.ppq_to_beat(ppq), 4)
        self.bar, self._bar_position = self._get_bar_position(take)

    def _get_bar_position(self, take: rpr.Take) -> ty.Tuple[int, Fraction]:
        # measure_start = RPR.MIDI_GetPPQPos_StartOfMeasure(
        #     take,
        # )
        (
            measure,
            _,
            _,
            qnMeasureStart,
            qnMeasureend,
        ) = RPR.TimeMap_QNToMeasures(  # type: ignore
            rpr.Project(), round(take.ppq_to_beat(self.ppq_position)), 1.0, 0.0
        )
        return measure, round(self.position - qnMeasureStart, 4)

    @property
    def fraction(self) -> Fraction:
        fr = Fraction(self.position / 4).limit_denominator(128)
        # print(fr, fr.denominator, '//', fr.numerator)
        if fr.denominator >= 1:
            return fr
        return Fraction(f'1/{fr.denominator//fr.numerator}')

    @property
    def bar_position(self) -> Fraction:
        fr = Fraction(self._bar_position / 4).limit_denominator(128)
        # print(fr, fr.denominator, '//', fr.numerator)
        if fr.denominator >= 1:
            return fr
        return Fraction(f'1/{fr.denominator//fr.numerator}')

    def __repr__(self) -> str:
        return f'<Position bar:{self.bar}, beat:{self.bar_position}>'


class Pitch(LyExpr):

    def __init__(self, midi_pitch: int) -> None:
        self.midi_pitch = midi_pitch
        self.key = 'C:min'

    def __repr__(self) -> str:
        return f'<Pitch({self.midi_pitch}) for_ly: "{self.for_ly}">'

    @property
    def for_ly(self) -> str:
        string = '{}'.format(
            librosa.convert.midi_to_note(self.midi_pitch, unicode=False)
        ).lower()
        if m := re.match(r'(\w)([#b]?)(\d)', string):
            note, acc, str_octave = m.groups()
        if acc == '#':
            acc = 'is'
        elif acc == 'b':
            acc = 's' if note in ('a', 'e') else 'es'
        octave = int(str_octave) - 3
        if octave == 0:
            oct_str = ''
        elif octave > 0:
            oct_str = "'" * octave
        else:
            oct_str = "," * -octave
        return f'{note}{acc}{oct_str}'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pitch):
            return False
        if self.midi_pitch == other.midi_pitch:
            return True
        return False


class Notation:

    def __init__(self, msg: str, position: Position) -> None:
        note_pattern = re.compile(r'NOTE\s(\d+)\s(\d+)\s')
        self.channel, midi_pitch = re.search(  # type:ignore
            note_pattern,
            msg
        ).groups()
        # print(f'channel: "{self.channel}", pitch: "{midi_pitch}"')
        self.pitch = Pitch(int(midi_pitch))
        self.notation_raw = re.sub(note_pattern, '', msg)
        self.position = position
        self.parced, self.unparced = self._parce()

    def __repr__(self) -> str:
        return 'Notation<ch: {}, pitch: {}, raw: {}> at ppq: {}'.format(
            self.channel, self.pitch, self.notation_raw, self.position
        )

    def _parce(self) -> ty.Tuple[ty.Dict[str, object], ty.List[str]]:
        tokens = re.findall(r'(\S+\s\S+)', self.notation_raw)
        known = {
            "voice": int,
            "staff": int,
            "accidental": str,
        }
        parced = {}
        unparced = []
        for token in tokens:
            key, val = token.split(' ')
            if key in known:
                parced[key] = known[key](val)
            else:
                unparced.append(token)
        return parced, unparced

    def apply_to_note(self, note: 'Note') -> None:
        note.notation = self.unparced
        for key, val in self.parced.items():
            setattr(note, key, val)


class Note(Event):

    def __init__(
        self,
        pitch: Pitch,
        position: Position,
        length: Length,
    ) -> None:
        self.pitch = pitch
        self.position = position
        self.length = length
        self.staff: ty.Optional[int] = None
        self.voice: ty.Optional[int] = None
        self.accidental = ''
        self._notation: ty.Optional[ty.List[str]] = None

    @property
    def notation(self) -> ty.Optional[ty.List[str]]:
        return self._notation

    @notation.setter
    def notation(self, notation: ty.List[str]) -> None:
        self._notation = notation

    def __repr__(self) -> str:
        items = [
            f'pitch={self.pitch}',
            f'position={self.position}',
            f'length={self.length}',
            f'staff={self.staff}',
            f'voice={self.voice}',
            f'accidental="{self.accidental}"',
        ]
        return f"Note({', '.join(items)})"

    @property
    def for_ly(self) -> str:
        return self.pitch.for_ly + self.length.for_ly


class Rest(Event):

    def __init__(self, length: Length, big: bool = False) -> None:
        self.length = length
        self.big = big

    @property
    def for_ly(self) -> str:
        s = self.r
        s += re.sub('~', f' {self.r}', self.length.for_ly)
        return s

    @property
    def r(self) -> str:
        s = 'r' if not self.big else 'R'
        return s

    def __repr__(self) -> str:
        return f"<Rest {self.r} {self.length}>"


@rpr.inside_reaper()
def parce_notes(notes: rpr.NoteList, take: rpr.Take) -> ty.List[Note]:
    ly_notes = []
    for note in notes:
        note_info = note.infos
        midi_pitch = note_info['pitch']
        pitch = Pitch(midi_pitch)
        pos_ppq = note_info['ppq_position']
        end = note_info['ppq_end']
        length = Length(take.ppq_to_beat(end) - take.ppq_to_beat(pos_ppq))
        pos = Position(pos_ppq, take)
        # ly_note = ly.music.items.Note()
        # ly_note.pitch = ly.music.items.Pitch(pitch.for_ly)
        # ly_note.duration = length.fraction.denominator
        # print(
        #     f'pitch: {pitch} ,as midi: {midi_pitch}',
        #     f'pos: {pos}, in beats: {take.ppq_to_beat(pos)}',
        #     f'end: {end}, in beats: {take.ppq_to_beat(end)}',
        #     f'length: {end - pos} in beats: {length}',
        #     # f'length for ly: {length.for_ly}',
        #     sep='\n---',
        # )
        # ly_note = ly.music.items.Note()
        # ly_note.pitch = note.pitch
        # print(ly_note)
        ly_notes.append(Note(pitch, pos, length))
    return ly_notes


# parced_notes = parce_notes(notes)


@rpr.inside_reaper()
def examine_notation(eventlist: ty.List[rpr.MIDIEventDict],
                     take: rpr.Take) -> ty.List[Notation]:
    notations = []
    for event in filter(
        lambda event: event['buf'][0:2] == [0xff, 0x0f], eventlist
    ):
        pos = Position(event['ppq'], take)
        msg = event['buf'][2:]
        # print(
        #     f'pos: {pos}, in beats: {take.ppq_to_beat(pos)}',
        #     f"msg: {bytes(msg)}",
        #     sep='\n---',
        # )
        notations.append(Notation(str(bytes(msg), encoding='utf-8'), pos))
    return notations


# notations = examine_notation(take.get_midi())
# pprint(notations)


def make_events(
    notes: ty.List[Note], notations: ty.List[Notation]
) -> EventsDictType:
    ppqs: EventsDictType = {}
    for note in notes:
        if note.position not in ppqs:
            ppqs[note.position] = []
        notation = tuple(
            filter(
                lambda x: (x.position == note.position) and
                (x.pitch == note.pitch), notations
            )
        )
        # print(notation)
        if notation:
            notation[0].apply_to_note(note)
        ppqs[note.position].append(note)
    return ppqs


# pprint(make_events(parced_notes, notations))
StaffType = ty.Tuple[EventsDictType, EventsDictType]


def slpit_by_staff(
    parced_events: EventsDictType,
    split_note: int = 60,
    divided: bool = False
) -> ty.Union[StaffType, EventsDictType]:
    staffs: StaffType = ({}, {})
    divided = divided
    for time, events in parced_events.items():
        for event in events:
            if event.staff:
                idx = event.staff - 1
                divided = True
            elif event.pitch.midi_pitch >= split_note:
                idx = 0
            else:
                idx = 1
            if time not in staffs[idx]:
                staffs[idx][time] = []
            staffs[idx][time].append(event)
    if not divided:
        return parced_events
    return staffs


class Chord(Event):

    def __init__(self, length: Length, *notes: Note) -> None:
        self.length = length
        self.notes = list(notes)

    def append(self, note: Note) -> 'Chord':
        self.notes.append(note)
        return self

    def extend(self, notes: ty.Iterable[Note]) -> 'Chord':
        self.notes.extend(notes)
        return self

    def __repr__(self) -> str:
        return f'<Chord {tuple(n.pitch for n in self.notes)}, {self.length}>'

    @property
    def for_ly(self) -> str:
        return '<{}>{}'.format(
            ' '.join(n.pitch.for_ly for n in self.notes), self.length.for_ly
        )


class Music(LyExpr):

    def __init__(self, *events: Event) -> None:
        self._music: ty.List[Event] = list(events)

    def append(self, event: Event) -> 'Music':
        self._music.append(event)
        return self

    def extend(self, events: ty.List[Event]) -> 'Music':
        self._music.extend(events)
        return self

    @ty.overload
    def __getitem__(self, key: slice) -> ty.List[Event]:
        ...

    @ty.overload
    def __getitem__(self, key: int) -> Event:
        ...

    def __getitem__(
        self, key: ty.Union[int, slice]
    ) -> ty.Union[Event, ty.List[Event]]:
        return self._music[key]

    def __len__(self) -> int:
        return len(self._music)

    def __repr__(self) -> str:
        return f'<Music {self._music[:]}>'

    @property
    def for_ly(self) -> str:
        return " ".join([m.for_ly for m in self._music])


class MusicList(Music):

    @property
    def for_ly(self) -> str:
        return f"{{{' '.join([m.for_ly for m in self._music])}}}"


class ClefChange(Event):

    def __init__(self, clef: str = 'treble') -> None:
        self.clef = clef

    def __repr__(self) -> str:
        return f'<Clef {self.clef}>'

    @property
    def for_ly(self) -> str:
        return f'\\clef {self.clef}'


class Staff(MusicList):

    def __init__(
        self, *events: Event, clef: ClefChange = ClefChange()
    ) -> None:
        super().__init__(*events)
        self.staff_expr = 'Staff'
        self.clef = clef

    @property
    def for_ly(self) -> str:
        list_ = ' '.join([m.for_ly for m in self._music])
        return f"\\new {self.staff_expr} {{{self.clef.for_ly} {list_}}}"


StaffGroup_template = """\
\\new {staff_expr} <<
{contents}
>>
"""


class StaffGroup(Staff):

    def __init__(self, *staves: Staff) -> None:
        staves[-1].clef = ClefChange('bass')
        super().__init__(*staves)
        self.staff_expr = 'PianoStaff'

    @property
    def for_ly(self) -> str:
        return StaffGroup_template.format(
            staff_expr=self.staff_expr,
            contents=f"\n".join((m.for_ly for m in self._music))
        )


class Voice(MusicList):

    def __init__(self, *events: Event) -> None:
        super().__init__(*events)

    def build_music(self, events: EventsDictType) -> Music:
        music = self._music
        first_pos = None
        last_pos = tuple(events.keys())[0]
        last_length = Length(0)
        for pos, notes in events.items():
            if first_pos is None:
                first_pos = pos
                last_pos = pos
                if pos.bar > 0:
                    music.extend(
                        [Rest(length=Length(4), big=True)] * (pos.bar - 1)
                    )
                    if pos.bar_position > 0:
                        music.append(Rest(Length(pos.bar_position)))

            if pos > last_pos + last_length:
                print(f'{pos} ({pos.fraction}) >  ({last_pos + last_length})')
                music.append(Rest(Length(pos - (last_pos + last_length))))
            if len(notes) > 1:
                # if VoiceSplit.check()
                length = notes[0].length
                event: ty.Union[Note, Chord] = Chord(length, *notes)
                print('made chord:', event)
            else:
                event = notes[0]
                length = event.length
            if pos - last_pos < last_length:
                print(f'{pos} - {last_pos} ({pos-last_pos}) < {last_length}')
                prev = music[-1]
                new_duration = Length(prev.length - (pos - last_pos))
                prev.length = Length(pos - last_pos, tie=True)
                if isinstance(prev, Chord):
                    prev = prev.notes
                elif not isinstance(prev, tuple):
                    prev = prev,
                if isinstance(event, Chord):
                    print(event, prev)
                    event.extend(prev)
                else:
                    event = Chord(length, *prev, event)
            music.append(event)

            last_length = length
            last_pos = pos

        return music


class VoiceSplit(Voice):

    def __init__(self) -> None:
        self.voices = [[], []]
        self._list = []

    def append(self, event: ty.Union[Note, Chord]) -> 'VoiceSplit':
        self._list.append(event)
        voice = note.voice if note.voice else 1
        self.voices[voice].append(event)

    @property
    def for_ly(self) -> str:
        voices = []
        for voice in self.voices:
            voice.append(self.build_voice_music(voice).for_ly)
        s = '\n//\n'.join(voices)
        s = '<<\n{s}\n>>'
        return s

    @classmethod
    def check(cls, note: Note) -> bool:
        if note.voice:
            return True
        return False

    def get_out_position(
        self, staff: EventsDictType, start_pos: Position, take: rpr.Take
    ) -> Position:
        for pos, notes in staff:
            if pos < start_pos:
                continue


@rpr.inside_reaper()
def item_to_ly(item: rpr.Item) -> str:

    out = io.StringIO()
    # printer = exp.Output_printer()
    # printer.set_file(out)
    # printer.dump_version("2.20.0")

    take = item.active_take
    midi = take.get_midi()
    notes = take.notes
    notations = examine_notation(midi, take)
    parced_notes = parce_notes(notes, take)
    parced_events = make_events(parced_notes, notations)
    # pprint(parced_events)
    staffs = slpit_by_staff(parced_events)
    # pprint(staffs)
    if isinstance(staffs, dict):
        staffs_music = build_staff_music(staffs, take),

    else:
        staffs_music = StaffGroup(
            *(build_staff_music(staff, take) for staff in staffs)
        )
    out = MusicList(staffs_music).for_ly

    # ready_chords = parce_chords(parced_events)
    # pprint(ready_chords)

    return out
