import re
import typing as ty
from fractions import Fraction
from pprint import pprint
import reapy as rpr

import librosa

import ly.music
import ly.music.items

take = rpr.Project().selected_items[0].active_take
midi = tuple(
    filter(
        lambda midi: midi['buf'][0] >= 0x80 and midi['buf'][0] <= 0xa0,
        take.get_midi()
    )
)
# pprint(tuple(enumerate(midi)))
# pprint(take.get_midi())

notes = take.notes

# pprint(tuple(enumerate(notes)))


class Length:

    def __init__(self, length: float) -> None:
        """        
        Parameters
        ----------
        length : float
            in quarter_notes
        """
        self._length = length

    def __repr__(self) -> str:
        return f'Length({self._length})'

    @property
    def fraction(self) -> Fraction:
        fr = Fraction(self._length / 4).limit_denominator()
        # print(fr, fr.denominator, '//', fr.numerator)
        if fr.denominator >= 1:
            return fr
        return Fraction(f'1/{fr.denominator//fr.numerator}')

    @property
    def for_ly(self) -> str:
        return f'{self._length/4} = {self.fraction}'


pitch_table = ['']


class Pitch:

    def __init__(self, midi_pitch: int) -> None:
        self._midi_pitch = midi_pitch

    def __repr__(self) -> str:
        return f'<Pitch({self._midi_pitch}) for_ly: "{self.for_ly}">'

    @property
    def for_ly(self) -> str:
        string = '{}'.format(
            librosa.convert.midi_to_note(
                self._midi_pitch, unicode=False, key='C:min'
            )
        ).lower()
        if m := re.match(r'(\w)([#b]?)(\d)', string):
            note, acc, octave = m.groups()
        if acc == '#':
            acc = 'is'
        elif acc == 'b':
            acc = 's' if note in ('a', 'e') else 'es'
        octave = int(octave) - 3
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
        if self._midi_pitch == other._midi_pitch:
            return True
        return False


class Notation:

    def __init__(self, msg: bytes, ppq_position: int) -> None:
        note_pattern = re.compile(r'NOTE (\d+) (\d+)')
        self.channel, midi_pitch = re.search(note_pattern, msg).groups()
        # print(f'channel: "{self.channel}", pitch: "{midi_pitch}"')
        self.pitch = Pitch(int(midi_pitch))
        self.notation_raw = re.sub(note_pattern, '', msg).strip()
        self.position = ppq_position

    def __repr__(self) -> str:
        return 'Notation<ch: {}, pitch: {}, raw: {}> at ppq: {}'.format(
            self.channel, self.pitch, self.notation_raw, self.position
        )

    def apply_to_note(self, note: 'Note') -> None:
        note.notation = self


class Note:

    def __init__(
        self,
        pitch: Pitch,
        ppq_position: int,
        length: Length,
    ) -> None:
        self.pitch = pitch
        self.position = ppq_position
        self.length = length
        self._notation = None

    @property
    def notation(self):
        return self._notation

    @notation.setter
    def notation(self, notation: Notation) -> None:
        self._notation = notation

    def __repr__(self) -> str:
        return "Note(pitch={}, ppq_position={}, length={}, notation={})".format(
            self.pitch, self.position, self.length.for_ly,
            None if not self.notation else self.notation.notation_raw
        )


@rpr.inside_reaper()
def parce_notes(notes: rpr.NoteList) -> ty.List[Note]:
    ly_notes = []
    for note in notes:
        note_info = note.infos
        midi_pitch = note_info['pitch']
        pitch = Pitch(midi_pitch)
        pos = note_info['ppq_position']
        end = note_info['ppq_end']
        length = Length(take.ppq_to_beat(end) - take.ppq_to_beat(pos))
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


parced_notes = parce_notes(notes)


@rpr.inside_reaper()
def examine_notation(
    eventlist: ty.List[rpr.MIDIEventDict]
) -> ty.List[Notation]:
    notations = []
    for event in filter(
        lambda event: event['buf'][0:2] == [0xff, 0x0f], eventlist
    ):
        pos = event['ppq']
        msg = event['buf'][2:]
        # print(
        #     f'pos: {pos}, in beats: {take.ppq_to_beat(pos)}',
        #     f"msg: {bytes(msg)}",
        #     sep='\n---',
        # )
        notations.append(Notation(str(bytes(msg)), pos))
    return notations


notations = examine_notation(take.get_midi())
# pprint(notations)


def make_events(notes: ty.List[Note], notations: ty.List[Notation]) -> None:
    ppqs = {}
    for note in notes:
        if note.position not in ppqs:
            ppqs[note.position] = []
        notation = tuple(
            filter(
                lambda x: x.position == note.position and x.pitch == note.pitch,
                notations
            )
        )
        # print(notation)
        if notation:
            notation[0].apply_to_note(note)
        ppqs[note.position].append(note)
    return ppqs


pprint(make_events(parced_notes, notations))
