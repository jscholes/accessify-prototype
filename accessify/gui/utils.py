def find_last_child(widget):
    children = widget.GetChildren()
    if not children:
        return widget
    else:      
        last = children[len(children) - 1]
        return find_last_child(last)

