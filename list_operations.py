"""
Contains some typical operations to construct new lists based on existing ones (and an operation).

These are often used when constructing trees of various types; but because the trees might have multiple such lists,
we've factored out the common operations.
"""


def l_become():
    """Trivial, included for reasons of symmetry"""
    return []


def l_insert(l, index, new_element):
    result = l[:]
    result.insert(index, new_element)
    return result


def l_delete(l, index):
    result = l[:]
    del result[index]
    return result


def l_replace(l, index, new_element):
    result = l[:]
    result[index] = new_element
    return result
