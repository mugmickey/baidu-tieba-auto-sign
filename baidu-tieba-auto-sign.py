# -*- coding: utf-8 -*-

import urllib2
import cookielib
import re
import hashlib
import json
import threading
import platform
import os
from sys import stdout
# from bs4 import BeautifulSoup
from pprint import pprint
from urllib import quote
from urllib import urlencode


def _setup_cookie(my_cookie):
    cookie = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    urllib2.install_opener(opener)
    opener.addheaders = [('User-agent',
                          'Mozilla/5.0 (SymbianOS/9.3; Series60/3.2 NokiaE72-1/021.021;Profile/MIDP-2.1 Configuration/CLDC-1.1 ) AppleWebKit/525 (KHTML, like Gecko) Version/3.0 BrowserNG/7.1.16352'),
                         ('Cookie', my_cookie),
                         ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')]

def _fetch_fav_pub_list():
    print u'获取喜欢的贴吧...' if system_env else '获取喜欢的贴吧...',
    page_count = 1
    list_fav_pubs = []

    while True:
        fav_pubs_list_page = 'http://tieba.baidu.com/f/like/mylike?&pn=%d' % page_count  # retrieve pubs by page
        req = urllib2.Request(fav_pubs_list_page)
        resp = urllib2.urlopen(req).read()
        pub_page = resp.decode('gbk').encode('utf8')
        # pub_page = resp.decode('gbk')
        # pub_page = resp
        title_list_re = "<a href=\"\/f\?kw=.*?\" title=\"(.*?)\">.+?<\/a><\/td><td><a class=\"cur_exp\" target=\"_blank\".*?"
        title_list_on_page = re.findall(title_list_re, pub_page)
        '''fav_pubs_of_this_page = []
        soup = BeautifulSoup(pub_page, 'html.parser')
        tableRows = soup.find('div', {'class': 'forum_table'}).find('table').findAll('tr')
        for tr in tableRows:
            cols = tr.findAll('td')
            # pprint(cols)
            if len(cols) >= 4:
                # link = cols[0].find('a').get('href')
                tmp_title = cols[0].find('a').get('title')
                # link_array = link.split('=')
                # fav_pub = link_array[1]
                fav_pub = tmp_title.encode('utf-8')
                # print type(fav_pub)
                # print fav_pub.decode('utf-8')
                fav_pubs_of_this_page.append(fav_pub)'''
        if not title_list_on_page:
            break
        else:
            list_fav_pubs += title_list_on_page
        page_count += 1

    '''for item in list_fav_pubs:
        print repr(item)
        print type(item)'''
    print ("\r"),
    return list_fav_pubs


def _fetch_pub_info(pub_name):
    pub_wap_url = "http://tieba.baidu.com/mo/m?kw=" + quote(pub_name)
    wap_resp = urllib2.urlopen(pub_wap_url).read()

    if not wap_resp:
        return
    re_already_sign = '<td style="text-align:right;"><span[ ]>(.*?)<\/span><\/td><\/tr>'
    already_sign = re.findall(re_already_sign, wap_resp)
    if already_sign:
        already_sign = already_sign[0]
        # print type(already_sign), already_sign.decode('utf-8')
    # print type(already_sign), already_sign.decode('utf-8')

    re_fid = '<input type="hidden" name="fid" value="(.+?)"\/>'
    _fid = re.findall(re_fid, wap_resp)
    fid = _fid and _fid[0] or None
    # print type(fid), fid

    re_tbs = '<input type="hidden" name="tbs" value="(.+?)"\/>'
    _tbs = re.findall(re_tbs, wap_resp)
    tbs = _tbs and _tbs[0] or None
    # print type(tbs), tbs

    return already_sign, fid, tbs


def _compose_dict(post_data):
    sign_key = "tiebaclient!!!"
    s = ""
    keys = post_data.keys()
    keys.sort()
    for i in keys:
        s += i + '=' + post_data[i]
    sign_stamp = hashlib.md5(s + sign_key).hexdigest().upper()
    post_data.update({'sign': str(sign_stamp)})
    return post_data


def _make_sign_request(pub_name, fid, tbs, bduss):
    sign_url = 'http://c.tieba.baidu.com/c/c/forum/sign'
    sign_request_dict = {"BDUSS": bduss,
                    "_client_id": "03-00-DA-59-05-00-72-96-06-00-01-00-04-00-4C-43-01-00-34-F4-02-00-BC-25-09-00-4E-36",
                    "_client_type": "4",
                    "_client_version": "1.2.1.17",
                    "_phone_imei": "540b43b59d21b7a4824e1fd31b08e9a6",
                    "fid": fid,
                    "kw": pub_name,
                    "net_type": "3",
                    'tbs': tbs}
    sign_request_dict = _compose_dict(sign_request_dict)
    sign_request_dict_encoded = urlencode(sign_request_dict)

    sign_request = urllib2.Request(sign_url, sign_request_dict_encoded)
    sign_request.add_header(
        "Content-Type", "application/x-www-form-urlencoded")
    return sign_request


def _handle_response(sign_resp, pub_name):
    sign_resp = json.load(sign_resp)
    error_code = sign_resp['error_code']
    sign_bonus_point = 0
    try:
        # Don't know why but sometimes this will trigger key error.
        if 'user_info' in sign_resp:
            if 'sign_bonus_point' in sign_resp['user_info']:
                sign_bonus_point = int(sign_resp['user_info']['sign_bonus_point'])
    except KeyError:
        pass
    if error_code == '0':
        print pub_name.decode('utf-8') + u"签到成功,经验+%d" % sign_bonus_point if system_env else pub_name + "签到成功,经验+%d" % sign_bonus_point
    else:
        if 'error_msg' in sign_resp:
            error_msg = sign_resp['error_msg']
            print pub_name.decode('utf-8') + ":" if system_env else pub_name + ":",
            print "(Error:" + unicode(error_code) + ") " + unicode(error_msg)


def _sign_a_pub(pub_name, bduss):
    already_sign, fid, tbs = _fetch_pub_info(pub_name)
    if not already_sign:
        print pub_name.decode('utf-8') + u': 正在尝试签到' if system_env else pub_name + ': 正在尝试签到'
    else:
        if already_sign == "已签到":
            print pub_name.decode('utf-8') + u": 已签到" if system_env else pub_name + ": 已签到"
            return

    if not fid or not tbs:
        print u"签到失败，原因未知" if system_env else "签到失败，原因未知"
        return

    sign_request = _make_sign_request(pub_name, fid, tbs, bduss)
    sign_resp = urllib2.urlopen(sign_request, timeout=5)
    _handle_response(sign_resp, pub_name)


def sign(my_cookie, _bduss):
    _setup_cookie(my_cookie)
    _fav_pub_list = _fetch_fav_pub_list()
    if len(_fav_pub_list) == 0:
        print u"获取喜欢的贴吧失败，请检查Cookie和BDUSS是否正确" if system_env else "获取喜欢的贴吧失败，请检查Cookie和BDUSS是否正确"
        return

    thread_list = []
    for pub in _fav_pub_list:
        t = threading.Thread(target=_sign_a_pub, args=(pub, _bduss))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join(3)


def main():
    handle = open("config.ini")
    my_cookie = handle.readline()
    if not my_cookie:
        exit(0)
    my_cookie_list = my_cookie.split('; ')
    for item in my_cookie_list:
        if "BDUSS=" in item:
            mbduss_str = item
    if not mbduss_str:
        exit(0)
    mbduss_list = mbduss_str.split('BDUSS=')
    mbduss = mbduss_list[1]
    sign(my_cookie, mbduss)


if __name__ == "__main__":
    system_env = True if platform.system() == 'Windows' else False
    main()
    os.system("date /T >> tieba_log.log") if system_env else os.system("date >> tieba_log.log")
