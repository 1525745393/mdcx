#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import time

import urllib3
import zhconv
from lxml import etree

from models.base.web import curl_html
from models.config.config import config
from models.crawlers.guochan import get_number_list
from models.crawlers.guochan import get_actor_list, get_lable_list,get_extra_info

urllib3.disable_warnings()  # yapf: disable

# import traceback

def get_actor_photo(actor):
    actor = actor.split(',')
    data = {}
    for i in actor:
        actor_photo = {i: ''}
        data.update(actor_photo)
    return data


def get_detail_info(html, real_url, number, file_path):
    href = re.split(r'[/.]', real_url)[-2]
    title_h1 = html.xpath('//h3[@class="title" and not(contains(normalize-space(.), "目录")) and not(contains(normalize-space(.), "为你推荐"))]/text()')
    title = title_h1[0].replace(number + ' ', '').strip() if title_h1 else number
    actor = get_extra_info(title, file_path, info_type="actor")
    tag = get_extra_info(title, file_path, info_type="tag")
    cover_url = html.xpath(f'//a[@data-original and contains(@href,"{href}")]/@data-original')
    cover_url = cover_url[0] if cover_url else ''

    return number, title, actor, cover_url, tag


def get_real_url(html, number_list, hscangku_url):
    item_list = html.xpath('//a[@class="stui-vodlist__thumb lazyload"]')
    for each in item_list:
        #href="/vodplay/41998-1-1.html"
        detail_url = hscangku_url + each.get('href')
        title = each.xpath('@title')[0]
        if title and detail_url:
            for n in number_list:
                temp_n = re.sub(r'[\W_]', '', n).upper()
                temp_title = re.sub(r'[\W_]', '', title).upper()
                if temp_n in temp_title:
                    return True, n, title, detail_url
    return False, '', '', ''

def get_redirected_url(url):

    result, response = curl_html(url)
    if not result:
        return None
    
    if redirected_url := re.search(r'"(https?://.*?)"', response).group(1):
        http = urllib3.PoolManager()
        response = http.request('GET', f'{redirected_url}{url}&p=', redirect=False)
        final_url = response.get_redirect_location()
        return final_url if final_url else None
    else:
        return None

def main(number, appoint_url='', log_info='', req_web='', language='zh_cn', file_path='', appoint_number=''):
    start_time = time.time()
    website_name = 'hscangku'
    req_web += '-> %s' % website_name
    title = ''
    cover_url = ''
    web_info = '\n       '
    log_info += ' \n    🌐 hscangku'
    debug_info = ''
    real_url = appoint_url
    hscangku_url = getattr(config, 'hscangku_website', 'http://hsck.net')

    try:
        if not real_url:
            # 处理番号
            number_list, filename_list = get_number_list(number, appoint_number, file_path)
            n_list = number_list[:1] + filename_list
            #处理重定向
            hscangku_url = get_redirected_url(hscangku_url)
            if not hscangku_url:
                debug_info = '没有正确的 hscangku_url，无法刮削'
                log_info += web_info + debug_info
                raise Exception(debug_info)
            for each in n_list:
                real_url = f'{hscangku_url}/vodsearch/-------------.html?wd={each}&submit='
                # real_url = 'http://hsck860.cc/vodsearch/-------------.html?wd=%E6%9F%9A%E5%AD%90%E7%8C%AB&submit='
                debug_info = f'请求地址: {real_url} '
                log_info += web_info + debug_info
                result, response = curl_html(real_url)

                if not result:
                    debug_info = '网络请求错误: %s' % response
                    log_info += web_info + debug_info
                    raise Exception(debug_info)
                search_page = etree.fromstring(response, etree.HTMLParser())
                result, number, title, real_url = get_real_url(search_page, n_list, hscangku_url)
                # real_url = 'http://hsck860.cc/vodsearch/-------------.html?wd=%E6%9F%9A%E5%AD%90%E7%8C%AB&submit='
                if result:
                    break
            else:
                debug_info = '没有匹配的搜索结果'
                log_info += web_info + debug_info
                raise Exception(debug_info)
            
        debug_info = f'番号地址: {real_url} '
        log_info += web_info + debug_info
        result, response = curl_html(real_url)

        if not result:
            debug_info = '没有找到数据 %s ' % response
            log_info += web_info + debug_info
            raise Exception(debug_info)

        detail_page = etree.fromstring(response, etree.HTMLParser())
        number, title, actor, cover_url, tag = get_detail_info(detail_page, real_url, number, file_path)
        actor_photo = get_actor_photo(actor)

        try:
            dic = {
                'number': number,
                'title': title,
                'originaltitle': title,
                'actor': actor,
                'outline': '',
                'originalplot': '',
                'tag': tag,
                'release': '',
                'year': '',
                'runtime': '',
                'score': '',
                'series': '',
                'country': 'CN',
                'director': '',
                'studio': '',
                'publisher': '',
                'source': 'hscangku',
                'website': real_url,
                'actor_photo': actor_photo,
                'cover': cover_url,
                'poster': '',
                'extrafanart': '',
                'trailer': '',
                'image_download': False,
                'image_cut': 'no',
                'log_info': log_info,
                'error_info': '',
                'req_web': req_web + '(%ss) ' % (round((time.time() - start_time), )),
                'mosaic': '国产',
                'wanted': '',
            }
            debug_info = '数据获取成功！'
            log_info += web_info + debug_info
            dic['log_info'] = log_info
        except Exception as e:
            debug_info = '数据生成出错: %s' % str(e)
            log_info += web_info + debug_info
            raise Exception(debug_info)

    except Exception as e:
        # print(traceback.format_exc())
        debug_info = str(e)
        dic = {
            'title': '',
            'cover': '',
            'website': '',
            'log_info': log_info,
            'error_info': debug_info,
            'req_web': req_web + '(%ss) ' % (round((time.time() - start_time), )),
        }
    dic = {website_name: {'zh_cn': dic, 'zh_tw': dic, 'jp': dic}}
    js = json.dumps(
        dic,
        ensure_ascii=False,
        sort_keys=False,
        indent=4,
        separators=(',', ': '),
    )
    return js


if __name__ == '__main__':
    # yapf: disable
    # print(main('GDCM-018'))
    # print(main('国产一姐裸替演员沈樵Qualla作品.七旬老农的女鬼诱惑.国语原创爱片新高度', file_path='国产一姐裸替演员沈樵Qualla作品.七旬老农的女鬼诱惑.国语原创爱片新高度'))
    # print(main('RS001', file_path='RS-001.红斯灯影像.REDSTEN.淫白大胜利.上.男女水中竞赛.败方被强制插入高潮连连'))
    # print(main('MD-0269', file_path='MD-0269.梁佳芯.唐芯.换妻性爱淫元宵.正月十五操骚鲍.麻豆传媒映画原创中文原版收藏'))
    # print(main('sh-006', file_path='SH-006.谢冰岚.神屌侠侣.是谁操了我的小龙女.涩会传媒'))
    # print(main('PMC-085', file_path='PMC/PMC-085.雪霏.出差借宿小姨子乱伦姐夫.特别照顾的肉体答谢.蜜桃影像传媒.ts'))
    # print(main('TM-0165', file_path='TM0165.王小妮.妈妈的性奴之路.性感少妇被儿子和同学调教成性奴.天美传媒'))
    # print(main('mini06.全裸家政.只為弟弟的學費打工.被玩弄的淫亂家政小妹.mini傳媒'))
    # print(main('mini06', file_path='mini06.全裸家政.只為弟弟的學費打工.被玩弄的淫亂家政小妹.mini傳媒'))
    # print(main('mini06.全裸家政.只为弟弟的学费打工.被玩弄的淫乱家政小妹.mini传媒', file_path='mini06.全裸家政.只为弟弟的学费打工.被玩弄的淫乱家政小妹.mini传媒'))
    # print(main('XSJ138', file_path='XSJ138.养子的秘密教学EP6.薇安姐内射教学.性视界出品'))
    # print(main('DW-006.AV帝王作品.Roxie出演.地方妈妈的性解放.双穴双屌', file_path='DW-006.AV帝王作品.Roxie出演.地方妈妈的性解放.双穴双屌'))
    # print(main('MDJ001-EP3.陈美惠.淫兽寄宿家庭.我和日本父子淫乱的一天.2021麻豆最强跨国合作', file_path='MDJ001-EP3.陈美惠.淫兽寄宿家庭.我和日本父子淫乱的一天.2021麻豆最强跨国合作'))
    # print(main('MKY-TN-003.周宁.乱伦黑料流出.最喜欢爸爸的鸡巴了.麻豆传媒MKY系列', file_path='MKY-TN-003.周宁.乱伦黑料流出.最喜欢爸爸的鸡巴了.麻豆传媒MKY系列'))
    # print(main('XSJ138.养子的秘密教学EP6.薇安姐内射教学.性视界出品', file_path='XSJ138.养子的秘密教学EP6.薇安姐内射教学.性视界出品'))
    # print(main('大像传媒之淫蕩刺青女學徒', file_path='大像传媒之淫蕩刺青女學徒'))
    # print(main('冠希传媒GX-017强上弟弟的巨乳姐姐', file_path='冠希传媒GX-017强上弟弟的巨乳姐姐'))
    # print(main('[SWAG]XHX-0014宅男的公仔幻化成人', file_path='[SWAG]XHX-0014宅男的公仔幻化成人'))
    # print(main('IDG5401'))
    print(main('大像传媒之長腿癡女代表情慾作-米歐', file_path='大像传媒之長腿癡女代表情慾作-米歐'))
    # print(main('MDX-0016'))
    # print(main('MDSJ-0004'))
    # print(main('RS-020'))
    # print(main('PME-018.雪霏.禽兽小叔迷奸大嫂.性感身材任我玩弄.蜜桃影像传媒', file_path='PME-018.雪霏.禽兽小叔迷奸大嫂.性感身材任我玩弄.蜜桃影像传媒'))
    # print(main('老公在外出差家里的娇妻被入室小偷强迫性交 - 美酱'))
    # print(main('', file_path='夏日回忆 贰 HongKongDoll玩偶姐姐.短篇集.夏日回忆 贰.Summer Memories.Part 2.mp4'))
    # print(main('', file_path='HongKongDoll玩偶姐姐.短篇集.夏日回忆 贰.Summer Memories.Part 2.mp4'))
    # print(main('', file_path="【HongKongDoll玩偶姐姐.短篇集.情人节特辑.Valentine's Day Special-cd2"))
    # print(main('', file_path='PMC-062 唐茜.綠帽丈夫連同新弟怒操出軌老婆.強拍淫蕩老婆被操 唐茜.ts'))
    # print(main('', file_path='MKY-HS-004.周寗.催情民宿.偷下春药3P干爆夫妇.麻豆传媒映画'))
    # print(main('淫欲游戏王.EP6', appoint_number='淫欲游戏王.EP5', file_path='淫欲游戏王.EP6.情欲射龙门.性爱篇.郭童童.李娜.双英战龙根3P混战.麻豆传媒映画.ts')) # EP不带.才能搜到
    # print(main('', file_path='PMS-003.职场冰与火.EP3设局.宁静.苏文文.设局我要女人都臣服在我胯下.蜜桃影像传媒'))
    # print(main('', file_path='PMS-001 性爱公寓EP04 仨人.蜜桃影像传媒.ts'))
    # print(main('', file_path='PMS-001.性爱公寓EP03.ts'))
    # print(main('', file_path='MDX-0236-02.沈娜娜.青梅竹马淫乱3P.麻豆传媒映画x逼哩逼哩blibli.ts'))
    # print(main('', file_path='淫欲游戏王.EP6.情欲射龙门.性爱篇.郭童童.李娜.双英战龙根3P混战.麻豆传媒映画.ts'))
    # main('', file_path='淫欲游戏王.EP6.情欲射龙门.性爱篇.郭童童.李娜.双英战龙根3P混战.麻豆传媒映画.ts')
    # print(main('', file_path='麻豆傳媒映畫原版 兔子先生 我的女友是女優 女友是AV女優是怎樣的體驗-美雪樱'))   # 简体搜不到
    # print(main('', file_path='麻豆傳媒映畫原版 兔子先生 拉麵店搭訕超可愛少女下-柚木结爱.TS'))
    # '麻豆傳媒映畫原版 兔子先生 拉麵店搭訕超可愛少女下-柚木結愛', '麻豆傳媒映畫原版 兔子先生 拉麵店搭訕超可愛少女下-', ' 兔子先生 拉麵店搭訕超可愛少女下-柚木結愛']
    # print(main('', file_path='麻豆傳媒映畫原版 兔子先生 我的女友是女優 女友是AV女優是怎樣的體驗-美雪樱.TS'))
    # print(main('', file_path='PMS-001 性爱公寓EP02 女王 蜜桃影像传媒 -莉娜乔安.TS'))
    # print(main('91CM-081', file_path='91CM-081.田恬.李琼.继母与女儿.三.爸爸不在家先上妹妹再玩弄母亲.果冻传媒.mp4'))
    # print(main('91CM-081', file_path='MDJ-0001.EP3.陈美惠.淫兽寄宿家庭.我和日本父子淫乱的一天.麻豆传媒映画.mp4'))
    # print(main('91CM-081', file_path='MDJ0001 EP2  AV 淫兽鬼父 陈美惠  .TS'))
    # print(main('91CM-081', file_path='MXJ-0005.EP1.弥生美月.小恶魔高校生.与老师共度的放浪补课.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='MKY-HS-004.周寗.催情民宿.偷下春药3P干爆夫妇.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='PH-US-002.色控.音乐老师全裸诱惑.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='MDX-0236-02.沈娜娜.青梅竹马淫乱3P.麻豆传媒映画x逼哩逼哩blibli.TS'))
    # print(main('91CM-081', file_path='MD-0140-2.蜜苏.家有性事EP2.爱在身边.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='MDUS系列[中文字幕].LAX0025.性感尤物渴望激情猛操.RUCK ME LIKE A SEX DOLL.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='REAL野性派001-朋友的女友讓我最上火.TS'))
    # print(main('91CM-081', file_path='MDS-009.张芸熙.巨乳旗袍诱惑.搔首弄姿色气满点.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='MDS005 被雇主强上的熟女家政妇 大声呻吟被操到高潮 杜冰若.mp4.TS'))
    # print(main('91CM-081', file_path='TT-005.孟若羽.F罩杯性感巨乳DJ.麻豆出品x宫美娱乐.TS'))
    # print(main('91CM-081', file_path='台湾第一女优吴梦梦.OL误上痴汉地铁.惨遭多人轮番奸玩.麻豆传媒映画代理出品.TS'))
    # print(main('91CM-081', file_path='PsychoPorn色控.找来大奶姐姐帮我乳交.麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='鲍鱼游戏SquirtGame.吸舔碰糖.失败者屈辱凌辱.TS'))
    # print(main('91CM-081', file_path='导演系列 外卖员的色情体验 麻豆传媒映画.TS'))
    # print(main('91CM-081', file_path='MDS007 骚逼女友在作妖-硬上男友当玩具 叶一涵.TS'))
    # print(main('MDM-002')) # 去掉标题最后的发行商
    # print(main('MDS-007')) # 数字要四位才能搜索到，即 MDS-0007 MDJ001 EP1 我的女优物语陈美惠.TS
    # print(main('MDS-007', file_path='MDJ001 EP1 我的女优物语陈美惠.TS')) # 数字要四位才能搜索到，即 MDJ-0001.EP1
    # print(main('91CM-090')) # 带横线才能搜到
    # print(main('台湾SWAG chloebabe 剩蛋特辑 干爆小鹿'))   # 带空格才能搜到
    # print(main('淫欲游戏王EP2'))  # 不带空格才能搜到
    # print(main('台湾SWAG-chloebabe-剩蛋特輯-幹爆小鹿'))
    # print(main('MD-0020'))
    # print(main('mds009'))
    # print(main('mds02209'))
    # print(main('女王的SM调教'))
    # print(main('91CM202'))
    # print(main('91CM-202'))
