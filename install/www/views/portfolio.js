jQuery(function($) {
    $('#recent-box [data-rel="tooltip"]').tooltip({placement: tooltip_placement});
    function tooltip_placement(context, source) {
        var $source = $(source);
        var $parent = $source.closest('.tab-content')
        var off1 = $parent.offset();
        var w1 = $parent.width();

        var off2 = $source.offset();
        var w2 = $source.width();

        if( parseInt(off2.left) < parseInt(off1.left) + parseInt(w1 / 2) ) return 'right';
        return 'left';
    }


    $('.dialogs,.comments').slimScroll({
        height: '300px'
    });
    
    
    //Android's default browser somehow is confused when tapping on label which will lead to dragging the task
    //so disable dragging when clicking on label
    var agent = navigator.userAgent.toLowerCase();
    if("ontouchstart" in document && /applewebkit/.test(agent) && /android/.test(agent))
      $('#tasks').on('touchstart', function(e){
        var li = $(e.target).closest('#tasks li');
        if(li.length == 0)return;
        var label = li.find('label.inline').get(0);
        if(label == e.target || $.contains(label, e.target)) e.stopImmediatePropagation() ;
    });

    $('#tasks').sortable({
        opacity:0.8,
        revert:true,
        forceHelperSize:true,
        placeholder: 'draggable-placeholder',
        forcePlaceholderSize:true,
        tolerance:'pointer',
        stop: function( event, ui ) {//just for Chrome!!!! so that dropdowns on items don't appear below other items after being moved
            $(ui.item).css('z-index', 'auto');
        }
        }
    );
    $('#tasks').disableSelection();
    $('#tasks input:checkbox').removeAttr('checked').on('click', function(){
        if(this.checked) $(this).closest('li').addClass('selected');
        else $(this).closest('li').removeClass('selected');
    });
})



jQuery(function($) {
    url = "/api/currencies?access=" + csrf_token;
    $.getJSON( url, function( data ) {
        html = "";
         $.each( data, function( key, val ) {
            currency_code = data[key]["code"].toUpperCase();
html += "<tr>"
html += "<td style='text-transform:capitalize;'>" + htmlEncode(key) + "</td>";
html += "<td>";
html += "<b class='green'>" + htmlEncode(data[key]["balance"]);
if(currency_code != ""){
    html += " " + htmlEncode(currency_code);
}
html += "</b></td>";
html += "<td class='hidden-480'>";
            pending = parseFloat(data[key]["pending"]);
            color = "green";
            if(pending > 0.0){
                color = "red";
            }
            pending = pending.toString();
html += "<b class='" + htmlEncode(color) + "'>" + htmlEncode(data[key]["pending"]);
if(currency_code != ""){
    html += " " + htmlEncode(currency_code);
}
html += "</b></td>";
html += "<td>";
            if(data[key]["address"] == ""){
                name = key;
                if(name.length > 1){
                    name = name.charAt(0).toUpperCase() + name.slice(1);
                }
                data[key]["address"] = name + " wallet could not be loaded.";
            }
html += htmlEncode(data[key]["address"]);
html += "</td>";
html += "<td>";
            color = "red";
            icon = "icon-remove";
            if(data[key]["connected"]){
                color = "green";
                icon = "icon-ok";
            }
html += "<b class='" + htmlEncode(color) + "'>" + "port " + htmlEncode(data[key]["rpc"]["port"]);
html += "&nbsp;<i class='" + htmlEncode(icon) + "'></i></b>";
html += "</td>";
html += "<td class='center'>";
html += "<label>";
html += "<input type='radio' class='ace' name='form-field-radio'>";
html += "<span class='lbl'></span>";
html += "</label>";
html += "</td>";
html += "</tr>";
        });
        if(Object.keys(data).length){
            $("#assets_tbody").html(html);
        }
    });
});


jQuery(function($) {
    //html = '<div style="margin-right: 10px; float: left;">Trading on:</div>';
    //html += '<div style="float: left; margin-right: 30px;"><b class="blue">';
    //if(testnet){
    //    $(".trading_network").text("Testnet");
    //}
    //html += '</b></div>';
    html = '<div style="margin-right: 10px; float: left;">';
    html += 'Connections:</div><div style="float: left; margin-right: 30px;">';
    html += '<b class="blue">' + htmlEncode(connection_no) + '</b></div>';
    html += '<div style="margin-right: 10px; float: left;">';
    html += 'NAT type:</div><div style="float: left; margin-right: 30px;">';
    html += '<b class="blue">';
    html += htmlEncode(nat_type);
    html += '</a></b></div>';
    html += '<div style="margin-right: 10px; float: left;">';
    if(node_type == "passive"){
        html += "Listening:";
         html += '</div><div style="float: left; margin-right: 30px;"><b class="green">port ' + htmlEncode(passive_port) + ' <i class="icon-ok"></i></b></div>';
    } else {
        html += "Node type:";
        html += '</div><div style="float: left; margin-right: 30px;">';
        html += '<b class="blue">';
        if(node_type == "simultaneous"){
            html += "sim_open";
        }
        else{
            html += htmlEncode(node_type);
        }
        html += '</b></div>';
    }
    html += '<div style="margin-right: 10px; float: left;">';
    html += 'Forwarding:</div><div style="float: left; margin-right: 30px;">';
    if(forwarding_type == "manual"){
        html += '<b class="red">manual <i class="icon-remove"></i></b>';
    } else {
        html += '<b class="green">' + htmlEncode(forwarding_type) + ' <i class="icon-ok"></i></b>';
    }
    html += '</div>';

    $(".portfolio_main_stats").html(html);
});

contracts = []
function list_contracts(){
    url = "/api/contracts?access=" + csrf_token;
    $.getJSON( url, function( data ) {
        html = '<table class="table table-bordered ';
        html += 'table-striped"><thead class="thin-border-';
        html += 'bottom"><tr><th><i class="icon-caret';
        html += '-right blue"></i>&nbsp;action</th><th>';
        html += '<i class="icon-caret-right blue"></i>&nbsp;';
        html += 'amount<th><i class="icon-caret-right';
        html += ' blue"></i>&nbsp;pair</th><th class="';
        html += 'hidden-480"><i class="icon-caret-right';
        html += ' blue"></i>&nbsp;ppc</th>';
        html += '<th><i class="icon-caret-right';
        html += ' blue"></i>&nbsp;status</th><th style="';
        html += 'color: #428BCA; width: 50px; text-align:';
        html += ' center; font-size: 18px;"><i class="icon-ok';
        html += ' blue">&nbsp;</i></th></tr></thead><tbody'
        html += ' id="assets_tbody">';
        if(!data.length){
            html += "<tr><td colspan='7'><center>You have no open contracts.</center></td></tr>'";
            $("#member-tab").html(html);
            return;
        }

        contracts = data;
        contract_index = 0;
        $.each( data, function( key, val ) {
            //action
            //amount
            //pair
            //ppc
            //fees
            //status
            //% complete
            contract = data[key];
            percent_complete = (math.bignumber(contract["recv"]) / math.bignumber(contract["download_amount"])) * 100;
            percent_complete = Math.floor(percent_complete);
            html += '<tr onclick="show_contract_details(' + htmlEncode(contract_index) + ');"><td>' + htmlEncode(contract["action"]);
            html += "</td><td>" + htmlEncode(contract["amount"]);
            html += "</td><td>" + htmlEncode(contract["base_currency"]) + "&nbsp;/&nbsp;";
            html += htmlEncode(contract["quote_currency"]);
            html += "</td><td>" + htmlEncode(contract["ppc"]);
            html += "</td><td>" + htmlEncode(contract["status"]);
            html += "</td><td>" + htmlEncode(percent_complete);
            html += "</td></tr>";

            contract_index += 1;
        });
        html += '</tbody></table>';
        $("#member-tab").html(html);
    });
}

function copy_contract_field(index, field){
    contract = contracts[index];
    value = contract[field];
    window.prompt("Copy " + field + " to clipboard: Ctrl+C, then press Enter.", value);
}

function show_contract_details(index){
    contract = contracts[index];
    $("body").css("overflow-y", "hidden");
    var box = bootbox.dialog({
        message: '&nbsp;',
        title: "Contract details",
        buttons: {
            ok: {
              label: "Close",
              className: "btn-white",
              callback: function() {
                bootbox.hideAll();
              }
            }
        }
    });
    $(".modal-dialog").css("width", "700px");
    $(".modal-body").css("padding-bottom", "5px");
    $(".bootbox-close-button").on("remove", function () {
        $("body").css("overflow-y", "scroll");
    });
    $( ".bootbox-body" ).html("Loading ...");
    $('body').css('cursor', 'progress');

    //HTML here.
    html = 'Green address:&nbsp;&nbsp;' + htmlEncode(contract["green_address"]) + '<br>';
    html += 'Deposit TXID:&nbsp;&nbsp;' + htmlEncode(contract["deposit_txid"]) + '<br>';
    html += 'Deposit TX hex:&nbsp;&nbsp;<a href="#" onclick="copy_contract_field(' + htmlEncode(index) + ', \'' + htmlEncode("deposit_tx_hex") + '\');">click to copy hex</a><br>';
    html += 'Setup TXID:&nbsp;&nbsp;' + htmlEncode(contract["setup_txid"]) + '<br>';
    html += 'Setup TX hex:&nbsp;&nbsp;<a href="#" onclick="copy_contract_field(' + htmlEncode(index) + ', \'' + htmlEncode("setup_tx_hex") + '\');">click to copy hex</a><br>';
    html += 'Download TXID:&nbsp;&nbsp;' + htmlEncode(contract["download_txid"]) + '<br>';
    html += 'Download TX hex:&nbsp;&nbsp;<a href="#" onclick="copy_contract_field(' + htmlEncode(index) + ', \'' + htmlEncode("download_tx_hex") + '\');">click to copy hex</a><br>';
    $( ".bootbox-body" ).html(html);

    //data = "x";
    //$(".modal-footer").html(data);
    $('body').css('cursor', 'default');
}


