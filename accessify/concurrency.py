def consume_queue(a_queue, item_handler):
    while True:
        item_handler(a_queue.get())
