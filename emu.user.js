// ==UserScript==
// @name        动车组交路查询
// @description 在 12306 订票页面上显示动车组型号与交路
// @author      Arnie97
// @namespace   https://github.com/Arnie97
// @homepageURL https://github.com/Arnie97/emu-tools
// @match       https://kyfw.12306.cn/otn/leftTicket/init
// @grant       GM_xmlhttpRequest
// @grant       GM_addStyle
// @version     2017.09.18
// ==/UserScript==

// Forked from https://stackoverflow.com/a/4673436/5072722
function format(str) {
    var args = Array.prototype.slice.call(arguments, 1);
    return str.replace(/{(\d+)}/g, function(match, number) {
        return args[number] !== undefined? args[number]: match;
    });
}

// Search the database
function getTrainModel(code) {
    if ('GDC'.indexOf(code[0]) == -1) {
        return;
    }
    for (var key in models) {
        var codes = models[key];
        for (var i = codes.length; i; i--) {
            if (code == codes[i]) {
                return key;
            }
        }
    }
}

// Patch items on the web page
function showTrainModel(i, obj) {
    var code = $(obj).find('a.number').text();
    var model = getTrainModel(code);
    if (!model) {
        return false;
    }
    var template = '<a onclick="$(this).children().toggle()">{0}<img src="https://moerail.ml/img/{1}.png" style="width: 600px; display: none;"></a>';
    $(obj).find('.ls>span').replaceWith(format(template, model, code));
    return true;
}

// Register the event listener
function main(dom) {
    models = JSON.parse(dom.responseText);
    var observer = new MutationObserver(function() {
        if ($('#trainum').html()) {
            $('.ticket-info').map(showTrainModel);
        }
    });
    observer.observe($('#t-list>table')[0], {childList: true});
}

GM_xmlhttpRequest({
    method: 'GET',
    url: 'https://moerail.ml/models.json',
    onload: main
});
GM_addStyle('\
    .ls          {width: auto  !important;} \
    .ticket-info {width: 400px !important;} \
');
