import typing as ty
import reapy as rpr

# editor = rpr.MIDIEditor()

take = rpr.Project().selected_items[0].active_take
midi = take.get_midi()
filtered = ty.cast(
    ty.Tuple[rpr.MIDIEventDict],
    tuple(
        filter(
            lambda event: event['selected'] and event['buf'][0] == 144, midi
        )
    )
)


def get_bounds(midi: ty.Iterable[rpr.MIDIEventDict]) -> ty.Tuple[float, float]:
    start, end = float('inf'), 0
    for event in midi:
        if not event['selected']:
            continue
        if start > event['ppq']:
            start = event['ppq']
        if end < event['ppq']:
            end = event['ppq']
    return start, end


start_ppq, end_ppq = get_bounds(midi)


def markers_to_ppq(take: rpr.Take, *ppqs: int) -> None:
    for ppq in ppqs:
        time = take.ppq_to_time(ppq)
        rpr.Project().add_marker(time)


# markers_to_ppq(take, start_ppq, end_ppq)


def spread_times(midi: ty.Tuple[rpr.MIDIEventDict], start: float,
                 end: float) -> ty.List[int]:
    step = (end - start) / (len(midi))
    times = []
    for i in range(len(midi) + 1):
        times.append(int(start + i * step))
    return times


times = spread_times(filtered, start_ppq, end_ppq)
# markers_to_ppq(take,*times)


def modify_list(midi: ty.List[rpr.MIDIEventDict],
                times: ty.List[int]) -> ty.List[rpr.MIDIEventDict]:
    modified: ty.List[rpr.MIDIEventDict] = []
    times_on_i, times_off_i = 0, 1
    for event_ in midi:
        event = event_.copy()
        if event['selected']:
            msg = event['buf'][0]
            if msg >= 0x90 and msg < 0xa0:
                event['ppq'] = times[times_on_i]
                times_on_i += 1
            elif msg >= 0x80 and msg < 0x90:
                event['ppq'] = times[times_off_i]
                times_off_i += 1
        modified.append(event)
    return sorted(modified, key=lambda d: d['ppq'])


modified = modify_list(midi, times)
take.set_midi(modified)
