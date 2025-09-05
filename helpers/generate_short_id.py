import shortuuid


def generate_short_id():
    return shortuuid.ShortUUID().random(length=10)
