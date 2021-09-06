def filter_tuples(tuple_list, n, value):
    return list(filter(lambda x: x[n] != value, tuple_list))
