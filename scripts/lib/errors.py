#!/usr/bin/env python3
"""统一错误码：替代 'ERR ' + str(e)[:80] 这种没法统计的写法。"""

OK = 'ok'
NO_OA = 'no_oa_url'            # 没有开放获取地址
NOT_PDF = 'not_pdf'            # 返回的不是 PDF
TOO_SMALL = 'too_small'        # 文件过小
FETCH_FAILED = 'fetch_failed'  # 网络层失败
HTTP_4XX = 'http_4xx'
HTTP_5XX = 'http_5xx'
TIMEOUT = 'timeout'
CRA_BLOCKED = 'cra_blocked'          # Cloudflare/Elsevier 风控
LOGIN_REQUIRED = 'login_required'
PAYWALLED = 'paywalled'
NO_BUTTON = 'no_pdf_button'
NO_FILE = 'no_file_after_click'
DUPLICATE = 'dup_sha'
MISSING = 'missing_file'

ALL = [OK, NO_OA, NOT_PDF, TOO_SMALL, FETCH_FAILED, HTTP_4XX, HTTP_5XX,
       TIMEOUT, CRA_BLOCKED, LOGIN_REQUIRED, PAYWALLED, NO_BUTTON,
       NO_FILE, DUPLICATE, MISSING]


def from_exception(exc):
    """把异常归到错误码。"""
    s = str(exc).lower()
    if 'timed out' in s or 'timeout' in s:
        return TIMEOUT
    if '403' in s:
        return HTTP_4XX
    if '404' in s:
        return HTTP_4XX
    if '429' in s:
        return HTTP_4XX
    if '5' in s[:3] and 'http error' in s:
        return HTTP_5XX
    if 'ssl' in s or 'certificate' in s:
        return FETCH_FAILED
    return FETCH_FAILED
