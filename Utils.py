import datetime


def To_hex_str(num):
    chaDic = {10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f'}
    hexStr = ""
    if num < 0:
        num = num + 2 ** 32
    while num >= 16:
        digit = num % 16
        hexStr = chaDic.get(digit, str(digit)) + hexStr
        num //= 16
    hexStr = chaDic.get(num, str(num)) + hexStr
    return hexStr


def get_time_stamp():
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")


def print_log(*logstrs):
    print(get_time_stamp(), end=" ")

    for logstr in logstrs:
        print(logstr, end=" ")

    print("")
