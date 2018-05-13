// ==UserScript==
// @name        动车组交路查询
// @description 在 12306 订票页面上显示动车组型号与交路
// @author      Arnie97
// @version     2018.05.13
// @license     MIT
// @namespace   https://github.com/Arnie97
// @homepageURL https://github.com/Arnie97/emu-tools
// @match       https://kyfw.12306.cn/otn/leftTicket/init
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/init
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/initPublicPrice
// @match       https://kyfw.12306.cn/otn/czxx/init
// @icon        https://moerail.ml/favicon.ico
// @connect     moerail.ml
// @grant       none
// ==/UserScript==

// Attempt to infer the model of the trains from these rules
var patterns = {
    'CRH1A-A型': /D7(1|2[01]|3)/,
    'CRH2A型': /C5[0356]/,
    'CRH5A型': /C(13|50)/,
    'CRH5G/2G型': /C85/,
    'CRH6A型': /C7[679]|S1/,
    'CRH6F型': /C(69|78)|D75[6-8]/,
    'NDJ3型': /S[25]/
};

// Search the database
function getTrainModel(code) {
    if ('GDCS'.indexOf(code[0]) == -1) {
        return;
    }
    for (var key in models) {
        var codes = models[key];
        for (var i = codes.length; i >= 0; i--) {
            if (code == codes[i]) {
                return [key, true];
            }
        }
    }
    for (var key in patterns) {
        if (code.match(patterns[key])) {
            return [key];
        }
    }
}

// Attempt to infer the model of intercity trains from the coach class
function getIntercityTrainModel(code, obj) {
    var table_row = obj.parentNode.parentNode;
    var coach_class = table_row.children[1];
    if (code.match(/C2[0-6]/)) {  // Tianjin
        if (coach_class.id.match(/^SWZ_/)) {  // Business Coach
            return ['CR400AF/BF型'];
        } else if (coach_class.id.match(/^TZ_/)) {  // Premier Coach
            return ['CRH3C型'];
        }
    } else if (code.match(/C29/)) {  // Zhengzhou
        if (coach_class.firstChild.textContent === '--') {
            return ['CRH6A型'];
        } else if (coach_class.id.match(/^SWZ_/)) {
            return ['CRH380A统型'];
        }
    }
}

// Patch items on the web page
// Return 1 for unknown trains, 2 for found ones and 3 for inferred ones
function showTrainModel(i, obj) {
    var code = $(obj).find('a.number').text();
    var model = getTrainModel(code) || getIntercityTrainModel(code, obj);
    if (!model) {
        return 1;
    } else if (model[1]) {
        var url = 'https://moerail.ml/img/' + code + '.png';
        var img = $('<img>');
        var node = $('<a>').addClass('route').text(model[0]).append(img);
        node.click(function(event) {
            img.attr('src') || img.attr('src', url);
            img.toggle();
        });
    } else {
        var node = $('<span>').addClass('route').text(model[0]);
    }
    $(obj).find('.ls>span, td:nth-child(3)').contents().replaceWith(node);
    return model[1]? 2: 3;
}

// Iterate through the items
function checkPage() {
    if (!$('#trainum, #_sear_tips>p').html()) {
        return;
    }
    var result = $('.ticket-info, #_query_table_datas>tr').map(showTrainModel);
    var count = [result.length, 0, 0, 0];
    result.each(function(i, x) {
        count[x]++;
    });

    var msg = 'EMU Tools: {0} checked, {2} found, {3} inferred';
    console.log(msg.replace(/{(\d+)}/g, function(match, number) {
        return count[number];
    }));
}

// Append <style> blocks to the document <head>
function addStyle(css) {
    return $('<style>').attr('type', 'text/css').text(css).appendTo('head');
}

// Register the event listener
function main(json_object) {
    addStyle(stylesheet);
    models = json_object;
    checkPage();
    var observer = new MutationObserver(checkPage);
    observer.observe($('.t-list>table')[0], {childList: true});
}

// Confirm the host name for Android client compatibility
if (location.host == 'kyfw.12306.cn') {
    $.getJSON('https://moerail.ml/models.json', main);
}

var stylesheet = ('\
    .ls {                           \
        width: 120px !important;    \
    }                               \
    .ticket-info {                  \
        width: 400px !important;    \
    }                               \
    .route>img {                    \
        display: none;              \
        position: absolute;         \
        z-index: 120;               \
        width: 640px;               \
        padding: 4px;               \
        background: #fff;           \
        border: 2px solid #ddd;     \
        border-radius: 4px;         \
    }                               \
');
