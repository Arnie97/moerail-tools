// ==UserScript==
// @name        动车组交路查询
// @description 在 12306 订票页面上显示动车组型号与交路
// @author      Arnie97
// @namespace   https://github.com/Arnie97
// @homepageURL https://github.com/Arnie97/emu-tools
// @match       https://kyfw.12306.cn/otn/leftTicket/init
// @grant       GM_xmlhttpRequest
// @grant       GM_addStyle
// @version     2018.02.10
// ==/UserScript==

var patterns = {
    'CRH1A-A型': /D7(1|2[01]|3)/,
    'CRH2A型': /C29/,
    'CRH5A型': /C(13|50)/,
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
                return key;
            }
        }
    }
    for (var model in patterns) {
        if (code.match(patterns[model])) {
            return model;
        }
    }
}

// Beijing-Tianjin Intercity Railway
function getIntercityTrainModel(code, obj) {
    if (!code.match(/C2[0-6]/)) {
        return;
    }
    var table_row = obj.parentNode.parentNode;
    var coach_class = table_row.childNodes[1].id;
    if (coach_class.match(/^SWZ_/)) {  // Business Coach
        return 'CR400AF/BF型';
    } else if (coach_class.match(/^TZ_/)) {  // Premier Coach
        return 'CRH3C型';
    }
}

// Patch items on the web page
function showTrainModel(i, obj) {
    var code = $(obj).find('a.number').text();
    var model = getTrainModel(code) || getIntercityTrainModel(code, obj);
    if (!model) {
        return false;
    }
    var url = 'https://moerail.ml/img/' + code + '.png';
    var img = $('<img>').attr('src', url).width(600).hide();
    var link = $('<a>').attr('onclick', '$(this).children().toggle()');
    link.text(model).append(img);
    $(obj).find('.ls>span').replaceWith(link);
    return true;
}

// Iterate through the items
function checkPage() {
    if (!$('#trainum').html()) {
        return;
    }
    var result = $('.ticket-info').map(showTrainModel);
    var count = result.length, sum = 0;
    result.each(function(i, x) {
        sum += x? 1: 0;
    });
    console.log('EMU Tools:', count, 'checked,', sum, 'found');
}

// Register the event listener
function main(dom) {
    models = JSON.parse(dom.responseText);
    checkPage();
    var observer = new MutationObserver(checkPage);
    observer.observe($('#t-list>table')[0], {childList: true});
}

GM_xmlhttpRequest({
    method: 'GET',
    url: 'https://moerail.ml/models.json',
    onload: main
});
GM_addStyle('\
    .ls          {width: 120px !important;} \
    .ticket-info {width: 400px !important;} \
');
