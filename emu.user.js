// ==UserScript==
// @name        动车组交路查询
// @description 在 12306 订票页面上显示动车组型号与交路
// @author      Arnie97
// @version     2019.09.26
// @license     MIT
// @namespace   https://github.com/Arnie97
// @homepageURL https://github.com/Arnie97/emu-tools
// @match       https://www.12306.cn/kfzmpt/*
// @match       https://kyfw.12306.cn/otn/leftTicket/init*
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/init
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/initPublicPrice
// @match       https://kyfw.12306.cn/otn/czxx/init
// @icon        https://moerail.ml/favicon.ico
// @connect     moerail.ml
// @grant       none
// ==/UserScript==

// Patch items on the web page
function showTrainModel(trains, trainNo, vehicleNo) {
    var urlPath = 'https://moerail.ml/img/';
    var img = $('<img>');
    var node = $('<a>').addClass('route').text(vehicleNo).append(img);
    node.mouseenter(function(event) {
        node.unbind('mouseenter');
        img.attr('src', urlPath + trainNo + '.png').error(function() {
            $(this).unbind('error').attr('src', urlPath + '404.png');
        });
    });
    node.click(function(event) {
        node.mouseenter();
        img.toggle();
    });
    $(trains[trainNo]).find('.ls>span, td:nth-child(3)').contents().replaceWith(node);
}

// Iterate through the items
function checkPage() {
    var trainNodes = $('.ticket-info, #_query_table_datas>tr');
    if (!trainNodes.length) {
        return;
    }

    var trains = {};
    trainNodes.each(function(i, node) {
        var trainNo = $(node).find('a.number').text();
        trains[trainNo] = node;
    });

    $.getJSON('https://api.moerail.ml/train/' + Object.keys(trains).join(','), function(results) {
        console.log('EMU Tools:', results.length, 'results found');
        results.forEach(function(item) {
            showTrainModel(trains, item.train_no, item.emu_no);
        });
    });
}

// Append <style> blocks to the document <head>
function addStyle(css) {
    return $('<style>').attr('type', 'text/css').text(css).appendTo('head');
}

// Register the event listener
function main() {
    addStyle(stylesheet);
    checkPage();
    var observer = new MutationObserver(checkPage);
    observer.observe($('.t-list>table')[0], {childList: true});
    observer.observe($('.t-list tbody')[0], {childList: true});
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

$(main);
