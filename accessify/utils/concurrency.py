import logging
import threading


logger = logging.getLogger(__name__)


def consume_queue(a_queue, item_handler):
    """
    Fetch items from a queue on a background thread and dispatch them to the specified item_handler callable.
    """
    logger.debug('Consuming queue {0} - dispatching items to {1}'.format(a_queue, item_handler))
    def consume():
        while True:
            try:
                item_handler(a_queue.get())
                a_queue.task_done()
            except Exception:
                logger.exception('Item handler {0} threw an error:'.format(item_handler), exc_info=True)
                continue

    worker = threading.Thread(target=consume, daemon=True)
    worker.start()

