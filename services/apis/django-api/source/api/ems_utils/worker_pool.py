from multiprocessing import Pool


class WorkerPoolHandler():
    """
    A handler for a shared Pool of workers to offload CPU intensive computations
    on multiple processes.
    """

    def __new__(cls, *args, **kwargs):
        """
        Ensure singleton, i.e. only one instance is created.
        """
        if not hasattr(cls, "_instance"):
            # This magically calls __init__ with the correct arguements too.
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        self.pool = Pool()
