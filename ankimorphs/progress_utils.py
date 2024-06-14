from functools import partial

from aqt import mw

from ankimorphs.exceptions import CancelledOperationException


def update_progress_potentially_cancel(
    label: str, counter: int, max_value: int
) -> None:
    assert mw is not None

    if counter % 1000 == 0:
        if mw.progress.want_cancel():  # user clicked 'x'
            raise CancelledOperationException

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label=label,
                value=counter,
                max=max_value,
            )
        )
