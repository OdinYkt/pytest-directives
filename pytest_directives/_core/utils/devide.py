from typing import TypeVar, Iterable, Iterator

A = TypeVar("A")


def divide(count_parts: int, iterable: Iterable[A]) -> list[Iterator[A]]:
    """
    Divide iterable to parts with same size

    :param count_parts: count of parts
    :param iterable: iterable to divide

    :return: list with count_parts iterators
    """
    if count_parts < 1:
        raise ValueError("'count_parts' must be at least 1")

    try:
        iterable[:0]
    except TypeError:
        seq = tuple(iterable)
    else:
        seq = iterable

    q, r = divmod(len(seq), count_parts)

    ret = []
    stop = 0
    for i in range(1, count_parts + 1):
        start = stop
        stop += q + 1 if i <= r else q
        ret.append(iter(seq[start:stop]))

    return ret
