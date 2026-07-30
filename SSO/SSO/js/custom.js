$.fn.select2.amd.define('select2/data/customAdapter', ['select2/data/array', 'select2/utils'],
    function (ArrayAdapter, Utils) {
        function CustomDataAdapter($element, options) {
            CustomDataAdapter.__super__.constructor.call(this, $element, options);
        }
        Utils.Extend(CustomDataAdapter, ArrayAdapter);
        CustomDataAdapter.prototype.updateOptions = function (data) {
            this.$element.find('option').remove();
            this.addOptions(this.convertToOptions(data));
            this.$element.val(null);
        }
        return CustomDataAdapter;
    }
);
$.fn.select2.amd.define("select2/customSelection", [
    "select2/utils",
    "select2/selection/multiple",
    "select2/selection/placeholder",
    "select2/selection/eventRelay",
    "select2/selection/single",
],
    function (Utils, MultipleSelection, Placeholder, EventRelay, SingleSelection) {
        let adapter = Utils.Decorate(MultipleSelection, Placeholder);
        adapter = Utils.Decorate(adapter, EventRelay);

        adapter.prototype.render = function () {
            let $selection = SingleSelection.prototype.render.call(this);
            return $selection;
        };
        adapter.prototype.update = function (data) {
            this.clear();
            let $rendered = this.$selection.find('.select2-selection__rendered');
            let noItemsSelected = data.length === 0;
            let formatted = "";

            if (noItemsSelected) {
                var placeholder = this.options.get("placeholder");
                if (placeholder.hasOwnProperty("text")) {
                    placeholder = placeholder.text;
                }
                formatted = placeholder || "";
            } else {
                var selected = [];
                if (data != null) {
                    selected = data.filter(x => x.id != "-1");
                }
                if (selected == null || selected.length == 0) {
                    var placeholder = this.options.get("placeholder");
                    if (placeholder.hasOwnProperty("text")) {
                        placeholder = placeholder.text;
                    }
                    formatted = placeholder || "";
                } else {
                    var all = []
                    this.$element.find("option").each(function (i, e) {
                        if ($(e).val() != "-1") all.push(e);
                    })

                    let itemsData = {
                        selected: selected,
                        all: all
                    };
                    formatted = this.display(itemsData, $rendered);
                }
            }
            $rendered.empty().append(formatted);
            $rendered.prop('title', formatted);
        };
        return adapter;
    });
$.fn.select2.amd.define('select2/selectAllAdapter', [
    'select2/utils',
    'select2/dropdown',
    'select2/dropdown/attachBody',
    'select2/dropdown/search',
], function (Utils, Dropdown, AttachBody, DropdownSearch) {
    function SelectAll() { }
    SelectAll.prototype.render = function (decorated) {
        var self = this,
            $rendered = decorated.call(this),
            $selectAll = $(
                '<button class="btn btn-default" type="button" style="padding: 0px 12px;display:inline-flex;align-items:center"><i class="fa fa-check-square" style="color:#f77750;font-size: 23px; margin-right:20px"></i> Chọn tất cả</button>'
            ),
            $unselectAll = $(
                '<button class="btn btn-default" type="button" style="padding: 0px 12px;display:inline-flex;align-items:center"><i class="fa fa-square-o" style="color:#f77750;font-size: 23px; margin-right:20px"></i> Bỏ chọn tất cả</button>'
            ),
            $btnContainer = $('<div style="margin-top:3px;">').append($selectAll).append($unselectAll);
        if (!this.$element.prop("multiple")) {
            // this isn't a multi-select -> don't add the buttons!
            return $rendered;
        }
        $rendered.find('.select2-dropdown').prepend($btnContainer);
        $selectAll.on('click', function (e) {
            var values = new Array();
            $(self.$element).find('option').each(function () {
                var opt = $(this);
                var opvalue = opt.attr('value');
                values.push(opvalue);
            });
            $(self.$element).data('select2').data.SelectAll = true;
            var selectid = '#' + $(self.$element)[0].dataset.select2Id.replace('-data-', '-') + '-results li'
            $(selectid).addClass('select2-results__option--selected')
            $(self.$element).val(values).trigger('change');
            // self.trigger('close');
        });
        $unselectAll.on('click', function (e) {
            var values = new Array();
            $(self.$element).data('select2').data.SelectAll = false;
            var selectid = '#' + $(self.$element)[0].dataset.select2Id.replace('-data-', '-') + '-results li'
            $(selectid).removeClass('select2-results__option--selected')
            $(self.$element).val(values).trigger('change');
            // self.trigger('close');
        });
        return $rendered;
    };
    var dropdownAdapter = Utils.Decorate(Utils.Decorate(Dropdown, DropdownSearch), AttachBody);
    return Utils.Decorate(
        Utils.Decorate(
            dropdownAdapter,
            AttachBody
        ),
        SelectAll
    )
});
$.fn.select2.amd.define('select2/selectAjaxAdapter', [
    'select2/utils',
    'select2/dropdown',
    'select2/dropdown/attachBody',
    'select2/dropdown/search',
], function (Utils, Dropdown, AttachBody, DropdownSearch) {
    function SelectAll() { }
    SelectAll.prototype.render = function (decorated) {
        var self = this,
            $rendered = decorated.call(this),
            $submit = $(
                '<button class="btn btn-xs btn-default pull-left ml-3" type="button" style="padding: 6px 0px;display:inline-flex;align-items:center">Select<i class="fa fa-check text-success ml-1" style="font-size: 23px;"></i></button>'
            ),
            $remove = $(
                '<button class="btn btn-xs btn-default pull-right mr-3" type="button" style="padding: 6px 0px;display:inline-flex;align-items:center">Delete<i class="fa fa-window-close text-danger ml-1" style="font-size: 23px;"></i></button>'
            ),
            $btnContainer = $('<div style="margin-top:3px;">').append($submit)
        if (self.options.options.allowClear || self.options.options.allowClear == null)
            $btnContainer.append($remove)
        if (!this.$element.prop("multiple")) {
            // this isn't a multi-select -> don't add the buttons!
            return $rendered;
        }
        $rendered.find('.select2-dropdown').prepend($btnContainer);
        $submit.on('click', function (e) {
            self.trigger('close');
        });
        $remove.on('click', function (e) {
            var values = new Array();
            $(self.$element).val(values).trigger('change');
            self.trigger('close');
        });
        return $rendered;
    };
    var dropdownAdapter = Utils.Decorate(Utils.Decorate(Dropdown, DropdownSearch), AttachBody);
    return Utils.Decorate(
        Utils.Decorate(
            dropdownAdapter,
            AttachBody
        ),
        SelectAll,
    )
});
var Select2_customSelection = $.fn.select2.amd.require('select2/customSelection');
var Select2_customSelectAll = $.fn.select2.amd.require('select2/selectAllAdapter');
var Select2_customSelectAjax = $.fn.select2.amd.require('select2/selectAjaxAdapter');
var Select2_customAdapter = $.fn.select2.amd.require('select2/data/customAdapter');
var Utils = $.fn.select2.amd.require('select2/utils');
var Select2_customSelectAjax_Close = Utils.Decorate($.fn.select2.amd.require('select2/selectAjaxAdapter'),
    $.fn.select2.amd.require("select2/dropdown/closeOnSelect"));
$.fn.select2.defaults.set("language", {
    loadingMore: function () {
        return "Tải thêm";
    },
    noResults: function () {
        return "Không tìm thấy";
    },
    searching: function () {
        return "Đang tải...";
    },
});
$.fn.select2.defaults.set("theme", "bootstrap");
$.fn.select2.defaults.set("width", "100%");
$.fn.select2.defaults.set("dropdownAutoWidth", true);

function showModal(element) {
    if ($("#" + element).length == 0) return;
    $("#" + element).modal("show");
}
function hideModal(element) {
    if ($("#" + element).length == 0) return;
    $("#" + element).modal("hide");
}

const reporter = {
    event: function (eventCode, message) {
        postData_common(constants.webAPIUrl + "/api/data/process/SaveLogFileClient", {
            screen: window.location.href,
            eventCode: eventCode,
            message: message
        })

    }
};

// Start reporter immediately

// Collect unhandled JavaScript errors and send them to the server
window.addEventListener('error', function (e) {
    // reporter.event('JAVASCRIPT_ERROR', e.message + ', ' + e.filename + ', ' + e.lineno + ':' + e.colno);
    // let stacktrace = e.stack;
    // if (!stacktrace && e.error) {
    //     stacktrace = e.error.stack;
    // }
    // if (stacktrace) {
    //     reporter.event('JAVASCRIPT_ERROR_STACKTRACE', stacktrace);
    // }
});