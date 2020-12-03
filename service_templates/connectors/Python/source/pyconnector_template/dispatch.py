#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import ctypes
import inspect
import threading


class DispatchOnce(threading.Thread):
    """
    Execute a target function once in a thread with the abbility to cancel.

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

    def __init__(
            self,
            target_func=None,
            target_args=None,
            target_kwargs=None,
            cleanup_func=None,
            cleanup_args=None,
            cleanup_kwargs=None,
        ):
        """
        Parameters
        ----------
        target_func : callable, optional
            The target that is called in the Thread. Defaults to None.
        target_args : tuple/list, optional
            Arguments provided to target_func. Defaults to ().
        target_kwargs : dict, optional
            Keywordarguments provided to target_func. Defaults to {}.
        cleanup_func : TYPE, optional
            A callable that is executed after the target has finished.
            Regardeless if it exited normally or with exception.
            Defaults to None.
        cleanup_args : tuple/list, optional
            Arguments provided to cleanup_func. Defaults to ().
        cleanup_kwargs : dict, optional
            Keywordarguments provided to cleanup_func. Defaults to {}.
        """
        # These are always daemonin, as we expect them to exit with the
        # main program. No zombies today.
        super().__init__(daemon=True)

        if target_args is None:
            target_args = ()
        if target_kwargs is None:
            target_kwargs = {}
        if cleanup_args is None:
            cleanup_args = ()
        if cleanup_kwargs is None:
            cleanup_kwargs = {}

        self.target_func = target_func
        self.target_args = target_args
        self.target_kwargs = target_kwargs
        self.cleanup_func = cleanup_func
        self.cleanup_args = cleanup_args
        self.cleanup_kwargs = cleanup_kwargs

        # Create the termination event and inject it into kwargs of the
        # target function, if the function expects it.
        self.termination_event = threading.Event()
        if callable(self.target_func):
            target_params = inspect.signature(self.target_func).parameters
            if "termination_event" in target_params:
                self.target_kwargs["termination_event"] = self.termination_event

    def run(self):
        """
        Execute the target function once in thread. Call cleanup afterwards.

        This executes target_func until either the function has finished
        by itself, or until the terminate method has been called. Either
        way we call cleanup_func and exit afterwards.
        """
        try:
            if self.target_func:
                self.target_func(*self.target_args, **self.target_kwargs)
        except SystemExit:
            pass
        finally:
            if self.cleanup_func:
                self.cleanup_func(*self.cleanup_args, **self.cleanup_kwargs)
            # This is taken from the Python default implementation at:
            # https://github.com/python/cpython/blob/master/Lib/threading.py
            #
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self.target_func, self.target_func, self.target_kwargs
            del self.cleanup_func, self.cleanup_func, self.cleanup_kwargs

    def terminate(self):
        """
        Find the id of this thread and use the Python C-Lib to inject a
        SystemExit exception.
        """
        # Find the id in the list of all threads.
        thread_id = None
        for _id, thread in threading._active.items():
            if thread is self:
                thread_id = _id
                break

        # Be aware of the change in Python 3.7 to PyThreadState_SetAsyncExc:
        # https://docs.python.org/3/c-api/init.html?highlight=pythreadstate_setasyncexc#c.PyThreadState_SetAsyncExc
        if thread_id:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(thread_id),
                ctypes.py_object(SystemExit)
            )
            # If true no thread was affected by the call above.
            if res == 0:
                print(
                    "Terminating thread failed, could not find thread with "
                    "matching id."
                )

        # Fire the event after the exception has been raised, so we jump
        # to exception handling immediatly.
        self.termination_event.set()


