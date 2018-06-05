## 中国铁路 12306 工具箱

用 Python 3 来检索[中国铁路客户服务中心](http://www.12306.cn)提供的各项数据。

### 车站信息查询
#### 依赖说明
* 各联网访问 API 的组件均依赖 [requests](http://docs.python-requests.org)。
* 如果你的 Python 版本低于 Python 3.5，则需安装标准库中新增的 [typing](https://pypi.python.org/pypi/typing)。
* 可选装 [IPython](https://ipython.org) 来增强交互式终端的易用性。
* `provinces.py` 依赖 [mwclient](https://mwclient.readthedocs.io) 来读取维基百科上的条目。

#### 组件介绍
* `hyfw.py` 交互式查询车站的电报码、TMIS 代码、所属省级行政区等。
    - 请输入站名的拼音首字母，匹配方式为前方一致。
        - 示例输入：`GLDS`
        - 示例输出：`{ZMHZ: 嘎拉德斯汰, TMIS: 13188, DBM: GLC, PYM: GLDST, SSJC: 蒙, LJDM: 00004}`
    - 数据来自[货运运费查询](http://hyfw.95306.cn/hyinfo/page/home-hyzx-yfss)页面。

* `kyfw.py` 解析客运车站的电报码、拼音码、拼音等。
    - 数据来自[车票预订](https://kyfw.12306.cn/otn/leftTicket/init)页面中的 [station_name.js](https://kyfw.12306.cn/otn/resources/js/framework/station_name.js)。

* `tmis.py` 交互式查询车站的 TMIS 代码。
    - 请输入汉字站名，匹配方式为前方一致。
        - 示例输入：`津沪`
        - 示例输出：`津沪所	10348`
    - 数据来自[货运营业站服务信息查询](http://hyfw.12306.cn/hyinfo/action/FwcszsAction_index?type=1)页面，该接口的亮点在于可以查到线路所及不办货车站的代码。感谢维基人 [N509FZ](https://zh.wikipedia.org/zh-cn/User:N509FZ/线路所) 指出此接口。

* `dump.py` 从以上三个接口分别读取数据，合并重复数据，并保存于本地的 `station_name.js`。
    - 发生合并冲突时，会弹出 Python Shell，以便用户准确解决。
    - 输出结果已通过[铁路信息查询](https://moerail.ml)网站呈现。
    - 输出结果的格式与 12306 网站提供的 `station_name.js` 相同，即以 `@` `|` 作为分隔符。

* `provinces.py` 读取中文维基百科[各车站条目中的信息框](https://zh.wikipedia.org/zh-cn/Template:Infobox_China_railway_station)，查询车站所属的省级行政区，以填补 `station_name.js` 中的对应字段。

* `stations.py` 启动一个 Shell，用于交互式查询上述 `station_name.js`（以及其他类似格式的文件）。
    - 启动后首先会进入 Python 解释器，退出该解释器后则会进入 SQLite 解释器。
    - 由于 SQL 中不能用编号代指字段，因此表中各字段依次用 A 至 Z 的字母命名。
    - 示例：中国铁路名字最短的车站是？
        - 输入：
            ```python
            sorted(s, key=lambda i: len(i[1]))[0]
            ```
            ```sql
            SELECT * FROM s
            ORDER BY LENGTH(b) ASC
            LIMIT 1;
            ```
        - 输出：
            ```python
            ('son', '宋', 'SOB', '57368', '黑')
            ```
    - 思考题：请模仿[港铁的站名拼词](https://zh.wikipedia.org/zh-cn/港鐵文化#站名拼詞)。
        ```
        　利国
        　布强格
        　　万年
        马三家
        　李旺

        宋城路
        　东通化
        　　百子湾
        　创业村
        　　兴隆店
        ```

### 车辆车次查询
#### 依赖说明
* 环境要求与[上一节](#车站信息查询)相同。
* 可选装 [Pillow](https://pillow.readthedocs.io) 来自动显示验证码图片。
* 如果安装有 Pillow 并启用了 Git 子模块 `captcha`，将自动识别验证码文字。

#### 组件介绍
* `tracking.py` 查询货运车辆的类别型号、编入列车车次、当前位置、装载货物类型、发站到站等。
    - 请输入货运车辆的编号，通常为七位纯数字。

* `tickets.py` 启动 Python 解释器，查询两座车站之间的客运列车车次及确切的余票数量。需要登录 12306 账户。

* `trains.py` 启动一个 Shell，用于交互式查询 `train_list.js` 中记录的车次。
    - 示例：Z1 到 Z100 的一百个车次中，哪些车次目前闲置？
        - 输入：
            ```python
            {'Z%d' % i for i in range(1, 101)}.difference(i[1] for i in t)
            ```
            ```sql
            WITH range AS (SELECT 1 i UNION SELECT i + 1 FROM range WHERE i < 100)
            SELECT 'Z' || i FROM range
            EXCEPT SELECT b FROM t;
            ```
        - 输出：
            ```python
            {'Z73', 'Z74', 'Z83', 'Z84'}
            ```
    - 示例：哪十座车站的始发车次最多？
        - 输入：
            ```python
            from collections import Counter
            distinct_trains = {i[0]: i[2] for i in t}
            Counter(distinct_trains.values()).most_common(10)
            ```
            ```sql
            SELECT c, COUNT(*) AS n
            FROM (SELECT DISTINCT a, c FROM t)
            GROUP BY c
            ORDER BY n DESC
            LIMIT 10;
            ```
        - 输出：
            ```python
            ('广州南', 384)
            ('上海虹桥', 335)
            ('北京西', 242)
            ('北京南', 242)
            ('上海', 193)
            ('深圳北', 187)
            ('西安北', 180)
            ('北京', 175)
            ('成都东', 161)
            ('武汉', 132)
            ```
    - 数据来自[车次查询](https://kyfw.12306.cn/otn/queryTrainInfo/init)页面中的 [train_list.js](https://kyfw.12306.cn/otn/resources/js/query/train_list.js)。

* `otp.py` 交互式查询某车次的正晚点信息。
    - 请输入车次与车站。
      - 示例输入：`6419 张辛 顺义 庙城 怀柔 统军庄 密云北`
      - 示例输出：略
    - 数据来自[正晚点查询](http://www.12306.cn/mormhweb/kyfw/lczwdcx)页面。

### 交路查询
#### 依赖说明
* 交路数据来自于[新浪微博用户「CRH380AL动车组」](https://weibo.com/u/2646253421)编写的动车组交路查询软件。
    - 在此对原作者坚持不懈的数据整理工作表示感谢。
    - 运行以下各组件前，请先下载并启动上述软件。
    - 由于上述软件系 Visual Basic 6.0 编写，因此交路查询相关的功能只能在 Windows 上运行。

* 截图功能依赖 [Pillow](http://python-pillow.org)。
    - 建议使用默认 DPI 与 Windows 经典主题，以保证图片正确裁切；参见 `mask.png`。
    - 建议关闭 ClearType 使用点阵字体，以保证单色位图的清晰度。

* 文字的提取依赖早期版本 Windows 的特定内存结构，参见 `internals.c`。
    - 注意，Python 3.5 及以上版本不再支持早期版本的 Windows。
    - 因此，建议使用 Windows XP 虚拟机安装 [Python 3.4](https://www.python.org/ftp/python/3.4.4/python-3.4.4.msi) 来运行下列组件。

* 批量查询功能依赖 12306 提供的车次数据 [train_list.js](https://kyfw.12306.cn/otn/resources/js/query/train_list.js)。
    - 因此，原软件中的少量车次因在 12306 上不存在而被遗漏，如 DJ7488 等。

#### 组件介绍
* `shot.py` 对单个车次进行查询，包括对动车组型号的提取及对整个窗口的截图。

* `cache.py` 对 12306 上列出的所有车次进行批量查询。
    - 输出的截图已通过[铁路信息查询](https://moerail.ml)网站呈现。

* `group.py` 对批量查询的文本输出按照车型进行分组，并转存为 JSON 格式。
    - 输出结果已用于[动车组交路查询](https://greasyfork.org/scripts/33266)浏览器扩展及[动车组查询 Android 客户端](https://github.com/Arnie97/webview-inject)。

* `web.py` 基于 Flask 框架编写，响应浏览器的 HTTP 请求，动态返回截图。
    - 由于该方案难以应对并发查询，且依赖 Windows 服务器，目前已被抛弃，仅作为开发历史予以保留。
