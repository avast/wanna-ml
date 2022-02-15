from halo import Halo

DEFAULT_SPINNER = "dots"  # Choose one of https://github.com/manrajgrover/py-spinners


class Spinner(Halo):
    """
    This class builds on top of https://github.com/manrajgrover/halo spinner.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spinner = DEFAULT_SPINNER

    def __enter__(self):
        """
        Starts the spinner on a separate thread. For use in context managers.
        """
        return self.start()

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Stops the spinner. For use in context managers.
        Succeed (print check mark) if the operation in context manager succeeds.
        Fail (print red cross) if the operation in context manager throws exception.
        """
        if exception_value:
            self.fail()
        else:
            self.succeed()
