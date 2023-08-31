
import re

def pad_zero(match):
    text = match.group(0)
    num = match.group('num')
    padded = "%03d" % int(num)
    return match.group(0).replace(num, padded)

prefix = "_s"

p = re.compile(r'%s(?P<num>[0-9]+)' % prefix)

tests = [
    "test_s1",
    "_s1",
    "myimage_s19.tif",
    "myimage2_s19.tif",
]

for t in tests:

    print('\n', t)
    # print('match', p.match(t))
    print("replace", p.sub(pad_zero, t))
