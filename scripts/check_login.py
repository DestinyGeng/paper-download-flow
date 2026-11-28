#!/usr/bin/env python3
"""检测订阅库登录态：用本地 CDP 代理逐个打开，判断是否已登录。输出 JSON。"""
import json
import sys
import time
import urllib.parse
import urllib.request

PROXY = 'http://127.0.0.1:3457'

SITES = [
    ('cnki', 'CNKI 知网', 'https://kns.cnki.net/kns8s/defaultresult/index?kw=%E6%BA%A2%E5%87%BA&korder=SU'),
    ('sd', 'ScienceDirect', 'https://www.sciencedirect.com/'),
    ('wos', 'Web of Science', 'https://webofscience.clarivate.cn/wos/woscc/smart-search'),
    ('ebsco', 'EBSCO', 'https://researchhtbprolebscohtbprolcom-s.libvpn.zuel.edu.cn/c/j4g2wp/search'),
]


def http(path, timeout=60):
    return urllib.request.urlopen(PROXY + path, timeout=timeout).read().decode()


def ev(tid, js):
    req = urllib.request.Request(PROXY + '/eval?target=' + tid, data=js.encode(),
                                 headers={'Content-Type': 'text/plain'})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30)).get('value')
    except Exception:
        return ''


def nav(tid, url):
    try:
        http('/navigate?target=%s&url=%s' % (tid, urllib.parse.quote(url, safe='')))
    except Exception:
        pass


def judge(key, title, url, text):
    t = (title or '')
    u = (url or '')
    x = (text or '')
    if 'ids.zuel.edu.cn' in u or '统一身份认证' in t:
        return False, '需要统一身份认证登录'
    if key == 'cnki':
        if '安全验证' in t:
            return False, '触发安全验证'
        return ('中国知网' in t or '检索' in t), '未触发验证' if '中国知网' in t or '检索' in t else '页面异常'
    if key == 'sd':
        ok = ('Zhongnan University' in x) or ('中南财经政法大学' in x)
        return ok, '机构已识别' if ok else '未识别机构'
    if key == 'wos':
        ok = ('SID=' in u) or ('Web of Science' in t)
        return ok, '已进入检索页' if ok else '未登录或超时'
    if key == 'ebsco':
        ok = ('EBSCO' in t) and 'ids.zuel.edu.cn' not in u
        return ok, '已进入 EBSCO' if ok else '未登录'
    return False, '未知'


def main():
    try:
        tid = json.loads(http('/targets'))[0]['targetId']
    except Exception as exc:
        print(json.dumps({'error': 'CDP 代理不可用: %s' % exc}, ensure_ascii=False))
        return
    out = {}
    for key, name, url in SITES:
        nav(tid, url)
        time.sleep(7)
        title = ev(tid, 'document.title') or ''
        cur = ev(tid, 'location.href') or ''
        text = ev(tid, 'document.body.innerText.slice(0,400)') or ''
        ok, why = judge(key, title, cur, text)
        out[key] = {'name': name, 'ok': bool(ok), 'why': why,
                    'title': title[:60], 'url': cur[:80]}
        print('##PROGRESS## ' + json.dumps(
            {'stage': 'login', 'done': len(out), 'total': len(SITES), 'msg': name},
            ensure_ascii=False), flush=True)
    print('##RESULT## ' + json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
