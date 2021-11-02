def filter_headers(headers, fields):
    return list(filter(lambda x: x[0].lower() not in fields, headers))
