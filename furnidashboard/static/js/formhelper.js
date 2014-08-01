var FurnFormHelper = (function() {

  var init = function(form_container) {

    form_container.find("div.items-form:not(.processed)").each(function(index, f) {
        
      var $form = $(f);
      var $special_fields = $form.find(".item-special-fields");
      var $general_fields = $form.find(".item-general-fields");            
      var $in_stock = $general_fields.find('input.order-item-in-stock');
      var $status = $general_fields.find('select.order-item-status');
      var $po_num = $form.find("input.order-item-po");
      var $ack_num = $form.find("input.order-item-ack-num");
      var date = $.datepicker.formatDate('yy-mm-dd', new Date());

      $form.addClass('processed');

      if ($in_stock.length && $in_stock.prop('checked')) {
        $special_fields.find("input").val("");          // clear special order related values
        $status.val("S");                               // select "In Stock"
        $special_fields.hide();                         // hide special order related fields
        
      } else {  
        $status.val("P");                               // select "Pending"
        $special_fields.show();
      }

      $in_stock.change(function() {
        if (this.checked) {
          $special_fields.find("input").val("");        // clear special order related values
          $status.val("S");                             // select "In Stock"
          $special_fields.hide();                       // hide special order related fields
        } else {
          $status.val("P");                             // select "Pending"
          $special_fields.show();
        }
      });
      
      //processing of dependent fields once item status is changed
      $status.change(function() {
        if ($(this).val() == "S") {
          $special_fields.find("input").val("");        // clear special order related values
          $in_stock.prop("checked", "checked");
          $special_fields.hide();      // hide special order related fields
        } else {
          $in_stock.removeAttr("checked");
          $special_fields.show();
        }
      });
      
      //default PO date to current date if PO number is entered
      $po_num.change(function() {
        if ($(this).val().trim() != "") {
          $special_fields.find("input.order-item-po-date").val(date);
        } else { 
          $special_fields.find("input.order-item-po-date").val("");
        }
      });
      
      //default ack. date to current date if ack. number is entered
      $ack_num.change(function() {
        if ($(this).val().trim() != "") {
          $special_fields.find("input.order-item-ack-date").val(date);
        } else { 
          $special_fields.find("input.order-item-ack-date").val("");
        }
      });            
    });
  }

  return {
    applyItemFormRules: function(form_container) {
      init(form_container);
    },

    //calc order total and balance due
    recalcOrderTotals:  function() {
      var $total = $("#order-total");
      var $balance_due = $("#balance-due");

      var subtotal = $("#id_subtotal_after_discount").val();
      subtotal = parseFloat(subtotal.replace(',', ''));
      if (isNaN(subtotal)) {
        subtotal = 0.0;
      }

      var tax = $("#id_tax").val();
      tax = parseFloat(tax.replace(',', ''));
      if (isNaN(tax)) {
        tax = 0.0;
      }

      var shipping = $("#id_shipping").val();
      shipping = parseFloat(shipping.replace(',', ''));
      if (isNaN(shipping)) {
        shipping = 0.0;
      }

      var deposit_balance = $("#id_deposit_balance").val();
      deposit_balance = parseFloat(deposit_balance.replace(',', ''));
      if (isNaN(deposit_balance)) {
        deposit_balance = 0.0;
      }

      var total_amount = subtotal + tax + shipping;
      var due = total_amount - deposit_balance;
      
      $total.text("$" + total_amount.toFixed(2));
      $balance_due.text("$" + due.toFixed(2));
    }
  }
})()
