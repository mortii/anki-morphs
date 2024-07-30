from functools import partial

from aqt import mw

from ankimorphs.exceptions import CancelledOperationException


def background_update_progress_potentially_cancel(
    label: str, counter: int, max_value: int, increment: int = 1000
) -> None:
    assert mw is not None

    if counter % increment == 0:
        # time.sleep(0.3)
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


def background_update_progress(label: str) -> None:
    assert mw is not None

    mw.taskman.run_on_main(
        partial(
            mw.progress.update,
            label=label,
        )
    )
