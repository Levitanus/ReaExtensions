import reapy as rpr
import typing as ty


def offline_fx_on_track(track: rpr.Track, on_pos: float, off_pos: float):
    for fx in track.fxs:
        param = fx.params['Bypass']
        env = param.envelope or param.add_envelope()
        print(env)
        # env = rpr.Envelope()
        env.insert_point(
            rpr.EnvelopePoint(
                index=0, shape=1, tension=0, selected=False, time=0.0, value=1
            ),
            sort=False
        )
        env.insert_point(
            rpr.EnvelopePoint(
                index=0,
                shape=1,
                tension=0,
                selected=False,
                time=on_pos,
                value=0
            ),
            sort=False
        )
        env.insert_point(
            rpr.EnvelopePoint(
                index=0,
                shape=1,
                tension=0,
                selected=False,
                time=off_pos,
                value=1
            ),
            sort=True
        )


def get_bounds(pr: rpr.Project) -> ty.Tuple[float, float]:
    left, right = (0.0, 0.0)
    for item in pr.selected_items:
        if left > item.position or left == .0:
            left = item.position
        end = item.position + item.length
        if right < end:
            right = end
    return left, right


with rpr.inside_reaper():
    pr = rpr.Project()

    left, right = get_bounds(pr)
    print(left, right)

    tracks = pr.selected_tracks
    for track in tracks:
        print(track.name)
        offline_fx_on_track(track, left, right)
    rpr.update_arrange()
