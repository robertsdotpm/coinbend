our_unl_pointer = "";
simple_lock = 0;

function footer_format(name, value){
    html  = "<b>" + htmlEncode(name) + "</b>&nbsp;&nbsp;";
    html += htmlEncode(value);
    $("#trade_footer").html(html);
}

function node_id_link(){
    html = '<b>Node ID:</b>&nbsp;&nbsp;<a onclick="copy_node_id();" href="#" style="color: #888 !important;">click here to generate a copy of your Node ID.</a>';
    $("#trade_footer").html(html);
}

function hide_bottom_whitespace(scroll)
{
    $(".page-content-row").css("overflow", "visible");
    $(".page-content-row").css("height", "auto");
    var height = $(".page-content-row").height();
    height -= 65;
    $(".page-content-row").css("height", height + "px");
    $(".page-content-row").css("overflow", "hidden");

    if(scroll)
    {
        setTimeout("window.scrollTo(0,document.body.scrollHeight);", 100);
    }
}

function toggle_show_open_trades()
{
    //show
    if(active_tab == "open_trades")
    {
        $("#task-tab-link")[0].click();
    }
    else
    {
        $("#amount_input").val("");
        $("#ppc_input").val("");
        $("#total_input").val("");
        $("#trade_fee_input").val("");
        $("#trade_status_input").val("");
        set_initial_ppc_value();
    }
    hide_bottom_whitespace();
}

function get_exchange_rate(base_currency, quote_currency){
    pair = base_currency.toUpperCase() + "/" + quote_currency.toUpperCase();
    url = "/api/rates/external/" + base_currency + "_"
    url += quote_currency + "?access=" + csrf_token;
    rate = "0";
    $.ajax({
        dataType: "json",
        url: url,
        success: function( data ) {
            rate = data[pair];
        },
        async: false
    });

    return rate;
}

function copy_node_id(){
    $('body').css('cursor', 'progress');
    footer_format("Status:", "now building your personal Node ID - please wait");

    url = "/api/node_id/direct?access=" + csrf_token;
    setTimeout(function(){
        $.ajax({
            dataType: "json",
            url: url,
            success: function( data ) {
                if(typeof data["error"] === 'undefined') {
                    node_id_link();
                    our_unl_pointer = data["unl_pointer"];
                    window.prompt("Copy Node ID to clipboard: Ctrl+C, then press Enter.", data["unl_pointer"]);
                } else {
                    alert(data["error"]);
                }
            },
            async: false
        });

        $('body').css('cursor', 'default');
    }, 700);
}

function convert_currencies(from_currency, to_currency, amount){
    amount = math.bignumber(amount);
    rate = math.bignumber(get_exchange_rate(from_currency, to_currency));
    if(rate == math.bignumber(0)){
        return math.bignumber(0);
    } else {
        return amount * rate;
    }
}

function set_initial_ppc_value(){
    $('body').css('cursor', 'progress');
    $('.input-group-addon select').css('cursor', 'progress');
    base_currency = $("#amount_addon").find("select").val();
    quote_currency = $("#ppc_addon").find("select").val();
    callback = function() {
        rate = get_exchange_rate(base_currency, quote_currency);
        rate = math.bignumber(rate);
        rate = pretty_float(rate, 16);
        $("#ppc_input").val(rate);
        adjust_total();
        $('body').css('cursor', 'default');
        $('.input-group-addon select').css('cursor', 'default');
    };
    setTimeout(callback, 100);
}

function format_currency(option_text, currency_code){
    if(option_text.length > 1){
        option_text = option_text.charAt(0).toUpperCase() + option_text.slice(1);
    }
    if(currency_code != ""){
        option_text = currency_code.toUpperCase();
    }

    return option_text;
}

currencies = {};
$( document ).ready(function() {
    url = "/api/currencies?access=" + csrf_token;
    $.getJSON( url, function( data ) {
        currencies = data;
        html = '<center><select class="form-control">';
         $.each( data, function( key, val ) {
            currency_code = data[key]["code"];
            option_text = format_currency(key, currency_code);
            html += '<option value="' + htmlEncode(option_text);
            html += '">' + htmlEncode(option_text) + '</option>';
        });
        html += '</select></center>';
        $("#amount_addon").html(html);
        $("#ppc_addon").html(html);
        $("#total_addon").html(html);

        $("#ppc_addon").find("select").change(function() {
            adjust_total_currency();
        });

        $("#total_addon").find("select").change(function() {
            adjust_ppc_currency();
        });

        $("#amount_addon").find("select").change(function() {
            set_initial_ppc_value();
        });

        $(".type_input").change(function() {
            adjust_desc();
        });

        set_initial_ppc_value();
    });
});


function dateFromString(str) {
    var m = str.match(/(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)\.(\d+)/);
    return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6] * 100);
}

active_tab = "new_trade";
function list_open_trades(){
    url = "/api/trades?access=" + csrf_token;
    $.getJSON( url, function( data ) {
        html = '<form id="delete_trade">';
        html += '<table class="table table-bordered table-striped';
        html += '"><thead class="thin-border-bottom">';
        html += '<tr><th style="width: 140px;"><i class=';
        html += '"icon-caret-right blue">&nbsp;</i>date</th>';
        html += '<th><i class="icon-caret-right blue">&nbsp</i>';
        html += 'type</th><th><i class="icon-caret-right blue">&nbsp</i>';
        html += 'amount</th><th class="hidden-480"><i class=';
        html += '"icon-caret-right blue">&nbsp</i>';
        html += 'ppc</th><th class="hidden-480"><i class=';
        html += '"icon-caret-right blue">&nbsp</i>';
        html += 'total</th>';
        html += '<th class="hidden-480"><i class=';
        html += '"icon-caret-right blue">&nbsp</i>';
        html += 'fee</th>';
        html += '<th class="hidden-480"><i class=';
        html += '"icon-caret-right blue">&nbsp</i>';
        html += 'deposit</th>';
        html += '<th class="hidden-480 center" style="';
        html += 'color: #428BCA; '; //font-size: 19px;
        html += 'width: 40px;"><i class=';
        html += '"icon-ok blue">&nbsp</i>';
        html += '</th><th class="center"';
        html += 'style="border: none !important; color:';
        html += '#428BCA; font-size: 19px; text-align: center; width: 53px">';
        html += '<i class="icon-remove"></i>';
        html += '</th></tr></thead><tbody>';
        if(!data.length){
            html += "<tr><td colspan='9'><center>You have no open trades.</center></td></tr>'";
            $(".open_trades").html(html);
            setTimeout("hide_bottom_whitespace(true);", 100);
            return;
        }
         $.each( data, function( key, val ) {
            // date 	type 	amount 	ppc 	total 	complete 	 radio
            trade = data[key];
            base_currency = trade["codes"][0].toUpperCase();
            if(base_currency == ""){
                base_currency = trade["pair"][0].toUpperCase();
            }
            quote_currency = trade["codes"][1].toUpperCase();
            if(quote_currency == ""){
                quote_currency = trade["pair"][1].toUpperCase();
            }
            created_at = new Date(trade["created_at"] * 1000);
            created_at = DateFormat.format.date(created_at.getTime(), "dd/MM/yyyy - HH:mm");
            html += "<tr><td>" + htmlEncode(created_at) + "</td>";
            html += "<td>" + htmlEncode(capitaliseFirstLetter(trade["action"])) + "</td>";
            html += "<td>" + htmlEncode(trade["amount"]) + " " + htmlEncode(base_currency) + "</td>";
            html += "<td>" + htmlEncode(trade["ppc"]) + " " + htmlEncode(quote_currency) + "</td>";
            html += "<td>" + htmlEncode(trade["total"]) + " " + htmlEncode(quote_currency) + "</td>";
            if(trade["action"] == "buy"){
                fee_currency = quote_currency;
            } else {
                fee_currency = base_currency;
            }
            html += "<td>" + htmlEncode(trade["fees"]) + " " + htmlEncode(fee_currency) + "</td>";
            html += "<td>" + htmlEncode(trade["deposit_status"]) + "</td>";
            if(trade["action"] == "buy"){
                percent_complete = (math.bignumber(trade["recv"]) / math.bignumber(trade["amount"])) * 100;
            } else {
                percent_complete = (math.bignumber(trade["recv"]) / math.bignumber(trade["total"])) * 100;
            }
            percent_complete = htmlEncode(trade["complete"]); 
            html += "<td style='text-align: center;'>" + htmlEncode(percent_complete) + "%</td>";
            html += '<td class="center"><label><input class="ace" name=';
            html += '"trade_id_radio" type="radio" value="'
            html += htmlEncode(trade["id"]) + '"><span'; 
            html += ' class="lbl"></span></label></td></tr>';
        });
        html += '</tbody></table></form>';
        $(".open_trades").html(html);
        setTimeout("hide_bottom_whitespace(true);", 100);
    });
}

function connection_countdown(n){
    //Timeout expired - we failed.
    if(n == 0){
        status = "unable to make a connection with the node";
        footer_format("Status:", status);
        return;
    }

    //Asynchronous error occured.
    if(simple_lock){
        return;
    }

    //Update status.
    status  = "attempting to make connection with node ... ";
    status += n.toString();
    footer_format("Status", status);

    //Keep counting.
    setTimeout(function(){
        connection_countdown(n - 1);
    }, 1000);
}

function post_trade(action, amount, pair, ppc, csrf_token, dest_ip){
    //Check dest_ip.
    if(dest_ip == "-1"){
        $.notify("Unable to connect to node.", "error");
        return;
    }

    data = {
        "action": action,
        "amount": amount,
        "ppc": ppc,
        "access": csrf_token,
        "dest_ip": dest_ip
    }

    success = function(data){
        if(typeof data["error"] === "undefined"){
            bootbox.hideAll();
            $.notify("Trade submitted.", "success");
        } else {
            $.notify("Trade was rejected.", "error");
            alert(data["error"]);
        }
        $('body').css('cursor', 'default');
    }

    error = function(data){
        $.notify("Unable to post trade to Coinbend.", "error");
        $('body').css('cursor', 'default');
    }


    url = "/api/trades/" + encodeURIComponent(pair[0]) + "_" + encodeURIComponent(pair[1]);
    $.ajax({
    type: "POST",
    url: url,
    data: data,
    success: success,
    error: error,
    dataType: "json"
    });
}

function new_trade(action, amount, ppc, pair){
    //Connect to UNL if needed.
    $('body').css('cursor', 'progress');
    unl_pointer = $("#unl_pointer").val();
    dest_ip = "";
    simple_lock = 0;
    if(unl_pointer != ""){
        if(unl_pointer == our_unl_pointer){
            $("#unl_pointer").val("Try entering the Node ID of another trader - you entered yourself!")
            footer_format("Status:", "direct connection to yourself makes no sense!");
        } else {
            connection_countdown(60);
            setTimeout(function() {
                url = "/api/network/direct";
                data = {
                    "unl_pointer": unl_pointer,
                    "access": csrf_token
                }

                $.ajax({
                    type: "POST",
                    data: data,
                    dataType: "json",
                    url: url,
                    success: function( data ) {
                        simple_lock = 1;
                        if(typeof data["error"] === 'undefined') {
                            dest_ip = data["dest_ip"];
                            bootbox.hideAll();
                        } else {
                            dest_ip = "-1";
                            status = "unable to make a connection with that node";
                            footer_format("Status:", status);
                            $('body').css('cursor', 'default');
                        }
                    },
                    error: function(data) {
                        simple_lock = 1;
                        $.notify("Unable to connect to Coinbend.", "error");
                        $('body').css('cursor', 'default');
                    },
                    complete: function(xhdr, status) {
                        post_trade(action, amount, pair, ppc, csrf_token, dest_ip);
                    }
                });

            }, 500);
        }
    } else {
        post_trade(action, amount, pair, ppc, csrf_token, dest_ip);
    }
}

function delete_trade(trade_id){
    url = "/api/trades/" + encodeURIComponent(trade_id);
    data = {
        "access": csrf_token
    }
    success = function(data){
        list_open_trades();
    }

    $.ajax({
    type: "DELETE",
    url: url,
    data: data,
    success: success,
    dataType: "json"
    });
}

function find_currency(needle){
    index = "";
    $.each(currencies, function(key, val) {
        needle = needle.toLowerCase();
        if(needle == key){
            index = key;
        }

        if(needle == currencies[key]["code"]){
            index = key;
        }
    });

    return index;
}

function validate_trade_form(){
    if(active_tab == "new_trade"){
        type = $(".type_input").val();
        amount = $("#amount_input").val();
        ppc = $("#ppc_input").val();
        total = $("#total_input").val();
        base_currency = $("#amount_addon").find("select").val();
        quote_currency = $("#ppc_addon").find("select").val();

        if(base_currency == quote_currency){
            $("#trade_status_input").val("Invalid currency pair");
            return 0;
        }

        //save coin amount
        //After initial check..
        //convert currencies to codes to simulate select
        
        if(isNumeric(amount) && isNumeric(ppc) && isNumeric(total)){
            //Sanity checking.
            if(amount == "0"){
                $("#trade_status_input").val("Invalid input for amount");
                return 0;
            }

            if(ppc == "0"){
                $("#trade_status_input").val("Invalid input for ppc");
                return 0;
            }

            if(total == "0"){
                $("#trade_status_input").val("Invalid input for total");
                return 0;
            }

            //Check fee outputs satisfies dust threshold.
            //Buyer expected fee amount.
            fee_currency = find_currency(quote_currency);
            min_fee_output = math.bignumber(currencies[fee_currency]["dust_threshold"]) / math.bignumber(trade_fee);
            expected_fee_output = math.bignumber(trade_fee) * math.bignumber(total);
            if(min_fee_output < expected_fee_output || (math.bignumber(total) != min_fee_output && demo == "1")){
                currency_code = currencies[fee_currency]["code"];
                display_currency = format_currency(fee_currency, currency_code);
                if(demo == "1"){
                    leading = "Required";
                } else {
                    leading = "Minimum";
                }
                msg = leading + " total is " + pretty_float(min_fee_output, 8) + " " + htmlEncode(display_currency);
                $("#trade_status_input").val(msg);
                return 0;
            }

            //Seller expected fee amount.
            fee_currency = find_currency(base_currency);
            min_fee_output = math.bignumber(currencies[fee_currency]["dust_threshold"]) / math.bignumber(trade_fee);
            expected_fee_output = math.bignumber(trade_fee) * math.bignumber(amount);
            if(min_fee_output < expected_fee_output || (math.bignumber(amount) != min_fee_output && demo == "1")){
                currency_code = currencies[fee_currency]["code"];
                display_currency = format_currency(fee_currency, currency_code);
                if(demo == "1"){
                    leading = "Required";
                } else {
                    leading = "Minimum";
                }
                msg = leading + " amount is " + pretty_float(min_fee_output, 8) + " " + htmlEncode(display_currency);
                $("#trade_status_input").val(msg);
                return 0;
            }

            //Check the input size for amount isn't less than TX fee.
            tx_fee_currency = find_currency(base_currency);
            min_amount = math.bignumber(currencies[tx_fee_currency]["tx_fee"]) * math.bignumber(3);
            if(math.bignumber(amount) < min_amount){
                currency_code = currencies[tx_fee_currency]["code"];
                display_currency = format_currency(tx_fee_currency, currency_code);
                msg = "Minimum amount is " + pretty_float(min_amount, 8) + " " + htmlEncode(display_currency);
                $("#trade_status_input").val(msg);
                return 0;
            }

            //Check the input size for total isn't less than TX fee.
            tx_fee_currency = find_currency(quote_currency);
            min_amount = math.bignumber(currencies[tx_fee_currency]["tx_fee"]) * math.bignumber(3);
            if(math.bignumber(total) < min_amount){
                currency_code = currencies[tx_fee_currency]["code"];
                display_currency = format_currency(tx_fee_currency, currency_code);
                msg = "Minimum total is " + pretty_float(min_amount, 8) + " " + htmlEncode(display_currency);
                $("#trade_status_input").val(msg);
                return 0;
            }
        } else {
            $("#trade_status_input").val("Invalid number entered.");
            return 0;
        }
    } else {
        return 0;
    }

    return 1;
}

function trade_page_submit(){
    if(active_tab == "new_trade"){
        if(!validate_trade_form()){
            return;
        }

        type = $(".type_input").val();
        amount = $("#amount_input").val();
        ppc = $("#ppc_input").val();
        total = $("#total_input").val();
        base_currency = $("#amount_addon").find("select").val();
        quote_currency = $("#ppc_addon").find("select").val();

        $("body").css("overflow-y", "hidden");
        var box = bootbox.dialog({
          message: '&nbsp;',
          title: "New " + htmlEncode(type) + " order",
          buttons: {
            submit: {
              label: "Accept",
              className: "btn-white",
              callback: function() {
                new_trade(type, amount, ppc, [base_currency, quote_currency]);
                return false;
              }
            },
           cancel: {
              label: "Decline",
              className: "btn-white",
              callback: function() {
                bootbox.hideAll();
              }
            },
          }
        });
        $(".modal-dialog").css("width", "600px");
        $(".modal-body").css("padding-bottom", "5px");
        $(".bootbox-close-button").on("remove", function () {
            $("body").css("overflow-y", "scroll");
        });
        $( ".bootbox-body" ).html("Loading ...");
        $('body').css('cursor', 'progress');

        setTimeout(function(){
            prefered_quote_pair = convert_currencies(quote_currency, prefered_currency, 1);
            total_prefered_currency = total * prefered_quote_pair;
            total_prefered_currency_precision = 2;
            if(pretty_float(total_prefered_currency, 2) == "0.00"){
                total_prefered_currency_precision = 16;
            }
            //Fee is taken from amount that you send.
            if(type == "buy"){
                total_fee = math.bignumber(total) * math.bignumber(trade_fee);
                total_fee_prefered_currency = total_fee * prefered_quote_pair;
                fee_currency = quote_currency;
            }
            else {
                prefered_base_pair = convert_currencies(base_currency, prefered_currency, 1);
                total_fee = math.bignumber(amount) * math.bignumber(trade_fee);
                total_fee_prefered_currency = total_fee * prefered_base_pair;
                fee_currency = base_currency;
            }

            data = "Are you sure you want to place a new " + htmlEncode(type);
            data += " order for " + htmlEncode(amount) + " " + htmlEncode(base_currency);
            
            if(total_prefered_currency != math.bignumber(0)){
                data += " (worth around " + pretty_float(total_prefered_currency, 16) + " ";
            } else {
                data += " (worth an unknown amount in ";
            }

            data += htmlEncode(prefered_currency) + ")";
            data += " at " + htmlEncode(ppc) + " " + htmlEncode(quote_currency) + " per coin?<p>";
            data += "<br clear='all'>The total order value is ";
            data += htmlEncode(total) + " " + htmlEncode(quote_currency) + " and the ";
            data += "trade fees are " + htmlEncode((trade_fee * 100)) + "%";
            data += " (approxmimately " + pretty_float(total_fee, 16);
            data += " " + htmlEncode(fee_currency);

            if(total_fee_prefered_currency != math.bignumber(0)){
                data += ", or ";
                data += pretty_float(total_fee_prefered_currency, 16);
                data += " in " + htmlEncode(prefered_currency)
            }

            data += ".)";
            data += '<input type="text" placeholder="';
            data += 'Enter a Node ID for direct trading';
            data += ' or leave blank for everyone to see it."';
            data += ' style="margin-top: 20px; width: 100%;';
            data += ' height: 40px; padding-left: 10px;" ';
            data += 'id="unl_pointer">';
            $( ".bootbox-body" ).html( data );

            data  = '<div style="float: left; position: absolute;';
            data += ' bottom: 20px; font-size: 13px !important;';
            data += 'color: #888 !important;" id="trade_footer">';
            data += '<b>Node ID:</b>';
            data += '&nbsp;&nbsp;<a style="color: #888 !important;"';
            data += ' href="#" onclick="copy_node_id();">';
            data += 'click here to generate a copy of ';
            data += 'your Node ID.</a></div>';
            data += $(".modal-footer").html();
            $(".modal-footer").html(data);
            $('body').css('cursor', 'default');
        }, 100);
    } else {
        trade_id = $('input[name=trade_id_radio]:checked', '#delete_trade').val();
        if(typeof(trade_id) != "undefined"){
            delete_trade(trade_id);
        }
    }
}

function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function truncate_insignificant(dec_s) {
    l = dec_s.length;
    for(var i = dec_s.length - 1; i >= 0; i--){
        if(dec_s[i] != "0"){
            break
        }
        l = i;
    }
    return dec_s.substring(0, l);
}


function expand_float_precision(n){
    max_precision = 16;
    n = math.format(n, {"notation": "fixed", precision: 20});
    var parts = n.split(".");
    var ret = parts[0];

    //Expand float precision as needed.
    if(parts.length == 2){
        dec = parts[1];
        if(dec.length > float_precision){
            float_precision = dec.length;
        }
        if(float_precision > max_precision){
            float_precision = max_precision;
        }
    }
}

function pretty_float(n, float_precision){
    max_precision = 16;
    n = math.format(n, {notation: "fixed", precision: 20, scientific: "off"});
    var parts = n.split(".");
    var ret = parts[0];
    if(parts.length == 2){
        var dec = truncate_insignificant(parts[1]);
        dec = dec.substring(0, float_precision);
        if(dec.length){
            ret += "." + dec;

            if(dec.length == 1){
                1;
                //ret += "0";
            }
        }
    } else {
        1;
        //ret += ".00";
    }
    return htmlEncode(ret);
}

function adjust_ppc(){
    amount = $("#amount_input").val();
    total = $("#total_input").val();
    if(isNumeric(amount) && isNumeric(total)){
        amount = math.bignumber(amount);
        total = math.bignumber(total);
        ppc = (total / amount);
        ppp = pretty_float(ppc, 16);
        $("#ppc_input").val(ppc);
        adjust_desc();
    }
}

function adjust_total(){
    amount = $("#amount_input").val();
    ppc = $("#ppc_input").val();
    if(isNumeric(amount) && isNumeric(ppc)){
        amount = math.bignumber(amount);
        ppc = math.bignumber(ppc);
        total = (amount * ppc);
        total = pretty_float(total, 16);
        $("#total_input").val(total);
        adjust_desc();
    }
}

function capitaliseFirstLetter(s){
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function adjust_desc(){
    total = $("#total_input").val();
    amount = $("#amount_input").val();
    ppc = $("#ppc_input").val();
    base_currency = $("#amount_addon").find("select").val();
    quote_currency = $("#ppc_addon").find("select").val();
    action = capitaliseFirstLetter($(".type_input").val());
    if(isNumeric(amount) && isNumeric(ppc) && isNumeric(total)){
        amount = math.bignumber(amount);
        ppc = math.bignumber(ppc);
        total = math.bignumber(total);
        if(action == "Buy"){
            total_fee_quote_currency = total * math.bignumber(trade_fee);
            total_fee_quote_currency = pretty_float(total_fee_quote_currency, 8);
            trade_fee_line = total_fee_quote_currency + " " + quote_currency + " (";
        }
        else {
            total_fee_quote_currency = amount * math.bignumber(trade_fee);
            total_fee_quote_currency = pretty_float(total_fee_quote_currency, 8);
            trade_fee_line = total_fee_quote_currency + " " + base_currency + " (";
        }
        trade_fee_line += (trade_fee * 100) + "% fee)";
        status_line = action + " " + pretty_float(amount, 16) + " " + base_currency;
        if(action == "Buy"){
            status_line += " with ";
        }
        else {
            status_line += " for ";
        }
        status_line += quote_currency;
        $("#trade_fee_input").val(trade_fee_line);
        $("#trade_status_input").val(status_line);
    }
}

function adjust_total_currency(){
    $("#total_addon").find("select").val($("#ppc_addon").find("select").val());
    set_initial_ppc_value();
}

function adjust_ppc_currency(){
    $("#ppc_addon").find("select").val($("#total_addon").find("select").val());
    set_initial_ppc_value();
}

