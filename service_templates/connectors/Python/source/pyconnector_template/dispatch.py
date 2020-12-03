#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import threading
import ctypes


class BaseDispatcher(threading.Thread):
    """
    This is a bit hacky extension that allows terminating a running thread.

    Termination is done primarly by raising SystemExit. However, you should
    be aware that some commands won't receive the Exception directly,
    especially if those commands are executed as C code. This is e.g. the
    case for time.sleep, which will delay until the full requested time is
    over before the Exception is handled. In order to circumvent this issue
    we additionally provide the termination_event (threadig.Event) as
    suggested by:
    https://blog.miguelgrinberg.com/post/how-to-kill-a-python-thread
    As a consuequence, the target function must termination_event as a
    keyword_argument.

    This may not work on all system, and especially not on other Python
    runtime implementations. This implemenation might only work on Python
    3.7+, see comment in terminate() for details.
    """

    def __init__(self, *args, **kwargs):
        """
        Similar to the __init__ of Thread.

        Difference is that we inject termination_event into the target
        function an that daemon is always set to True. The later is as
        we need to be sure that the Dispatcher will exit with the main
        program.

        See also:
        https://docs.python.org/3/library/threading.html#threading.Thread
        """
        kwargs["daemon"] = True

        self.termination_event = threading.Event()
        if not "kwargs" in kwargs:
            kwargs["kwargs"] = {}  # These are the kwargs of the target func.
        kwargs["kwargs"]["termination_event"] = self.termination_event

        super().__init__(*args, **kwargs)

    def terminate(self):
        """
        Find the id of this thread and use the Python C-Lib to inject a
        SystemExit exception.
        """
        # Find the id in the list of all threads.
        for _id, thread in threading._active.items():
            if thread is self:
                thread_id = _id
                break

        # Be aware of the change in Python 3.7 to PyThreadState_SetAsyncExc:
        # https://docs.python.org/3/c-api/init.html?highlight=pythreadstate_setasyncexc#c.PyThreadState_SetAsyncExc
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(thread_id),
            ctypes.py_object(SystemExit)
        )

        # Fire the event after the exception has been raised, so we jump
        # to exception handling immediatly.
        self.termination_event.set()

        # If not thread was affected by the call above.
        if res == 0:
            print(
                "Terminating thread failed, could not find thread with "
                "matching id."
            )


class DispatchInInterval(BaseDispatcher):

    def __init__(self, dispatch_interval):
        """
        self.dispatch_interval

        Parameters
        ----------
        dispatch_interval : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """