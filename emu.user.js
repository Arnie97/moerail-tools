// ==UserScript==
// @name        动车组交路查询
// @description 在 12306 订票页面上显示动车组型号与交路
// @author      Arnie97
// @version     2023.07.26
// @license     MIT
// @namespace   https://github.com/Arnie97
// @homepageURL https://github.com/Arnie97/emu-tools/blob/master/emu.user.js
// @match       https://kyfw.12306.cn/otn/leftTicket/init*
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/init
// @match       https://kyfw.12306.cn/otn/leftTicketPrice/initPublicPrice
// @match       https://kyfw.12306.cn/otn/czxx/init
// @icon        https://rail.re/favicon.ico
// @connect     rail.re
// @grant       none
// ==/UserScript==

// Patch items on the web page
function showTrainModel(parentNode, info) {
    var urlPath = 'https://rail.re/img/';
    var img = $('<img>');
    var node = $('<a>')
        .addClass('route')
        .text(formatTrainModel(info).emu_no)
        .attr('title', info.date)
        .append(img);

    colors.some(function(pair) {
        if (pair[1].test(info.emu_no)) {
            node.css('color', pair[0]);
            return true;
        }
    });

    // Preload images on mouse hover
    node.mouseenter(function(event) {
        node.unbind('mouseenter');
        img.attr('src', urlPath + info.train_no + '.png').error(function() {
            $(this).unbind('error').attr('src', urlPath + '404.png');
        });
    });
    node.click(function(event) {
        node.mouseenter();
        img.toggle();
    });
    $(parentNode).find('.ls>span, td:nth-child(3)').contents().replaceWith(node);
}

// Add hyphens properly
function formatTrainModel(info) {
    [
        /^(\w+)(\d{4})$/,
        /^(\w+A)(A-\d{4})$/,
        /^(\w+F)(\w+-\d{4})$/,
    ].forEach(function(regExp) {
        var match = info.emu_no.match(regExp);
        if (match) {
            info.emu_no = match[1] + "-" + match[2];
        }
    });
    return info;
}

// Iterate through the items
function checkPage() {
    var trainNodes = $('.ticket-info, #_query_table_datas>tr');
    if (!trainNodes.length) {
        return;
    }

    var trainNumbers = Array.from(trainNodes.map(function(index, node) {
        return $(node).find('a.number').text();
    }));

    var url = 'https://api.rail.re/train/,' + trainNumbers.join(',');
    $.getJSON(url, function(results) {
        console.log('EMU Tools:', results.length, 'results found');

        // Convert array to map
        var trains = {};
        results.forEach(function(info) {
            trains[info.train_no] = info;
        });

        trainNodes.each(function(index, node) {
            var info = trains[trainNumbers[index]];
            if (info) {
                showTrainModel(node, info);
            }
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

var colors = [
    ['#D52', /MTR/],
    ['#080', /^CR200J/],
    ['#222', /^CRH(1|380D)/],
    ['#222', /^CRH2(G|.-?246[0-5])/],
    ['#E58', /^CRH6F-?A/],
    ['#F62', /^CRH6/],
    ['#999', /^CRH380A/],
    ['#F10', /Z|AF-?C|^CRH3A-?A/],
    ['#B01', /AF/],
    ['#B85', /BF|^CRH3A/],
];

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
