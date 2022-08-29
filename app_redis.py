# -*- coding:utf-8 -*-
from spider import *
from utils import douban
from flask import Flask, abort, request, jsonify
from flask_cors import CORS
from flask_caching import Cache
import concurrent.futures
import json

redis_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': '127.0.0.1',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 3
}

app = Flask(__name__)
cors = CORS(app)
cache = Cache(app=app, config=redis_config)
# cache.clear()

site_list = [
    # "bdys01",
    "bttwoo",
    "cokemv",
    "czspp",
    "ddys",
    "dy555",
    "gitcafe",
    "lezhu",
    "libvio",
    "onelist",
    "smdyy",
    "sp360",
    "voflix",
    "yiso",
    "zhaoziyuan"
]

with open('./json/douban.json', "r", encoding="utf-8") as f:
    douban_filter = json.load(f)


@app.route('/vod')
def vod():
    try:
        wd = request.args.get('wd')
        ac = request.args.get('ac')
        quick = request.args.get('quick')
        play = request.args.get('play')
        flag = request.args.get('flag')
        filter = request.args.get('filter')
        t = request.args.get('t')
        pg = request.args.get('pg')
        ext = request.args.get('ext')
        ids = request.args.get('ids')
        q = request.args.get('q')

        sites = request.args.get('sites')
        ali_token = request.args.get('ali_token')
        try:
            timeout = int(request.args.get('timeout'))
        except Exception as e:
            timeout = 5

        if not ali_token:
            ali_token = ""

        # 站点筛选
        search_sites = []
        if not sites or sites == "all":
            search_sites = site_list
        else:
            try:
                for site in sites.split(","):
                    if site in site_list:
                        search_sites.append(site)
            except Exception as e:
                print(e)
                search_sites = site_list
        sites_key = "".join(sorted(search_sites))

        # 分类数据
        if filter == "true" and t:
            res = cache.get(f"{t}_{ext}_{pg}")
            if res:
                return res
            else:
                res = douban.cate_filter(t, ext, pg)
                if res:
                    cache.set(f"{t}_{ext}_{pg}", res, timeout=60*60*3)
            return res

        # 搜索
        if wd:
            key_name = f"search__{wd}__{sites_key}"
            if ali_token:
                key_name += "__ali"
            res = cache.get(key_name)
            if res:
                return jsonify({
                    "list": res
                })
            else:
                res = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(search_sites)) as executor:
                    to_do = []
                    for site in search_sites:
                        future = executor.submit(eval(f"{site}.searchContent"), wd, ali_token)
                        to_do.append(future)
                    try:
                        for future in concurrent.futures.as_completed(to_do, timeout=timeout):  # 并发执行
                            # print(future.result())
                            res.extend(future.result())
                        if res:
                            cache.set(key_name, res, timeout=60*30)
                    except Exception as e:
                        print(e)
                    finally:
                        return jsonify({
                            "list": res
                        })

        # 详情
        if ac and ids:
            vodList = cache.get(f"detail__{ids}")
            if not vodList:
                vodList = eval(f"{ids.split('$')[0]}.detailContent")(ids, ali_token)
                if vodList:
                    cache.set(f"detail__{ids}", vodList, 60*20)
            return jsonify({
                "list": vodList
            })

        # 播放
        if play and flag:
            playerContent = eval(f"{play.split('___')[0]}.playerContent")(play, flag, ali_token)
            return playerContent

        real_time_hotest = cache.get("real_time_hotest")
        if not real_time_hotest:
            real_time_hotest = douban.subject_real_time_hotest()
            if real_time_hotest:
                cache.set("real_time_hotest", real_time_hotest, 60*60)
        douban_filter["list"] = real_time_hotest
        return jsonify(douban_filter)

        # return jsonify({
        #     "list": search_sites
        # })
    except Exception as e:
        print(e)
        return jsonify({
            "list": []
        })


@app.route('/')
def hello_world():  # put application's code here
    abort(403)


if __name__ == '__main__':
    app.run()
