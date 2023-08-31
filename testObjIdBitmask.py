import requests
import click
import pdb

@click.group()
def bitmaskTest():
    pass

def getByteStr(bt):
    bstr = ''
    for i in range(0, 8):
        bstr = bstr + ('1' if (bt & 2 ** i) != 0 else '0')
    return bstr

@bitmaskTest.command()
@click.argument('sessionid')
@click.argument('tableid')
@click.option('-q', '--query', default='*')
def getBitmask(sessionid, tableid, query):
    url = 'http://localhost:4080/webgateway/table/{}/obj_id_bitmask/?query={}'.format(tableid, query)
    cookies = {'sessionid': sessionid}
    res = requests.get(url, cookies=cookies)
    print(res.status_code)
    # print(res.text)
    bitmask = res.content
    bitStr = ''
    for i in range(0, len(bitmask)):
        bitStr = bitStr + getByteStr(int(bitmask[i]))
    # print(bitStr)
    return


if __name__ == '__main__':
    bitmaskTest()