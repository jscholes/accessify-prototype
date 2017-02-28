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
