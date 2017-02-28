import threading


def consume_queue(a_queue, item_handler):
    """
    On a background thread, fetch items from a queue and dispatch them to the specified item_handler callable.
    """
    def consume():
        while True:
            item_handler(a_queue.get())

    worker = threading.Thread(target=consume, daemon=True)
    worker.start()


def submit_future(executor, func, *func_args, done_callback=None, error_callback=None, include_return_value=True, **func_kwargs):
    """
    Helper to submit a future to an executor, attach it to a done callback and handle errors in a separate callback if desired.

    If done_callback is provided, it will be called with a single argument - the return value of the submitted function unless include_return_value is False in which case it will be called with no arguments.

    If the submitted function raises an exception and error_callback is provided, it will be called with the exception as a single argument.  If no error callback is provided, the exception will be reraised in the context in which the concurrent.futures module executes done callbacks.

    If the function raises an exception and no done or error callbacks have been provided, or the done or error callbacks raise an exception, the behaviour is undefined.  See the documentation for the concurrent.futures module for more details.
    """
    def done(future):
        try:
            res = future.result()
        except Exception as e:
            if error_callback is not None:
                error_callback(e)
                return
            else:
                raise
        if done_callback is not None:
            if include_return_value:
                done_callback(res)
            else:
                done_callback()

    future = executor.submit(func, *func_args, **func_kwargs)
    future.add_done_callback(done)
