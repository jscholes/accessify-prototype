def format_seconds(seconds):
    m, s = divmod(seconds, 60)
    if m >= 60:
        h, m = divmod(m, 60)
    else:
        h = 0
    if h > 0:
        return '{0:02d}:{1:02d}:{2:02d}'.format(h, m, s)
    else:
        return '{0:02d}:{1:02d}'.format(m, s)

