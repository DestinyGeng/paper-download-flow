#!/usr/bin/env python3
"""JS 表达式构造：所有插进浏览器的字符串都走 json.dumps，避免转义地狱。

教训：直接拼 f-string 会踩 \u4e00 被 Python 转义、引号错配、eval 400 这几类坑。
"""
import json


def js(value):
    """把 Python 值安全地序列化成 JS 字面量。"""
    return json.dumps(value, ensure_ascii=False)


def read_body(max_chars=4000):
    return 'document.body.innerText.slice(0,%d)' % int(max_chars)


def read_html(max_chars=4000):
    return 'document.documentElement.outerHTML.slice(0,%d)' % int(max_chars)


def find_by_text(text, tag='a,button'):
    """返回第一个内文恰好等于 text 的元素表达式。"""
    return ('Array.from(document.querySelectorAll(%s))'
            '.find(function(e){return (e.innerText||"").trim()===%s})'
            % (js(tag), js(text)))


def mark(selector, attr='data-pick', value='1'):
    """给唯一元素打标记，返回 ok / no。"""
    return ('(function(){var e=document.querySelector(%s);'
            'if(!e)return "no";e.setAttribute(%s,%s);return "ok"})()'
            % (js(selector), js(attr), js(value)))


def mark_visible_by_id(element_id, attr='data-pick', value='1'):
    """给指定 id 且可见的元素打标记（CNKI 的 pdfDown 有隐藏重复项）。"""
    return ('(function(){var e=Array.from(document.querySelectorAll(%s))'
            '.filter(function(x){return x.id===%s&&x.getBoundingClientRect().width>0})[0];'
            'if(!e)return "no";e.setAttribute(%s,%s);e.scrollIntoView({block:"center"});return "ok"})()'
            % (js('a,button'), js(element_id), js(attr), js(value)))


def attr_of(selector, name):
    return '(function(){var e=document.querySelector(%s);return e?e.getAttribute(%s):null})()' % (
        js(selector), js(name))


def title():
    return 'document.title'
