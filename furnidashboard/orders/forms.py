from stores.models import Store
from .models import Order, OrderItem, OrderDelivery, OrderAttachment, OrderIssue, OrderItemProtectionPlan, OrderFinancing
from commissions.models import Commission
from customers.models import Customer
from django import forms
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms.utils import ErrorList
from bootstrap3_datetime.widgets import DateTimePicker
from django.forms.widgets import Select
from django.contrib.auth import get_user_model
from django.utils.functional import curry
from django.conf import settings
from ajax_select.fields import AutoCompleteSelectField
from bootstrap_toolkit.widgets import BootstrapDateInput, BootstrapTextInput
from core.mixins import DisabledFieldsMixin
from django.db.models import Q
import core.utils as utils
import orders.utils as order_utils
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, Field, HTML
from crispy_forms.bootstrap import AppendedText, InlineField

DATEPICKER_OPTIONS = {"format":"YYYY-MM-DD", "pickTime": False}

class OrderItemForm(forms.ModelForm):

  def __init__(self, *args, **kwargs):
    super(OrderItemForm, self).__init__(*args, **kwargs)
    self.fields['in_stock'].widget.attrs['class'] = "order-item-in-stock"
    self.fields['description'].widget.attrs['class'] = "order-item-desc"
    self.fields['description'].required = True
    
    self.fields['status'].required = True
    self.fields['status'].widget.attrs['class'] = "order-item-status"
    #self.fields['status'].initial = 'S'  #'In Stock' is selected by default
    
    self.fields['po_num'].widget.attrs['class'] = "order-item-po"
    self.fields['po_num'].label = "PO #"
    self.fields['po_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['po_date'].label = "PO placed date"
    self.fields['po_date'].widget.attrs['class'] = "order-item-po-date"
    self.fields['ack_num'].widget.attrs['class'] = "order-item-ack-num"
    self.fields['ack_num'].label = "Acknowledgement #"
    self.fields['ack_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['ack_date'].label = "Acknowl. date"
    self.fields['ack_date'].widget.attrs['class'] = "order-item-ack-date"
    
    self.fields['eta'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['eta'].widget.attrs['class'] = "order-item-eta clear"
    self.fields['eta'].label = "ETA"
    self.fields['description'].widget.attrs['size']=80

  def clean(self):
    ''' 
    By default, 'In Stock' status is auto selected for order item.
    If 'In stock' checkbox is selected, status is reset to 'In Stock'
    and special order related values are cleared and hidden. Otherwise, 
    if 'Pending' is selected, in stock indicator is cleared and special 
    order values are shown. 'Ordered', 'Received', or 'Delivered' arenot 
    availabe if PO number is not entered. 'Pending' is no available if
    PO number is entered.
    '''
    cleaned_data = super(OrderItemForm, self).clean()
    status = cleaned_data.get("status")
    if status in ('O', 'R', 'D'): #ordered, received, or delivered
      #check that all ordered items have PO num and date
      po_num = cleaned_data.get('po_num')
      po_date = cleaned_data.get('po_date')
      if po_num == None or po_date == None:
        msg = "Specify PO# and PO Date before changing item status"
        # self.add_error('status', msg)
        self._errors['status'] = ErrorList([u'Cannot change item status.'])
        raise forms.ValidationError(msg)

    return cleaned_data

  class Meta:
    model = OrderItem
    #fields = ['description', 'in_stock', 'status', 'po_num', 'po_date', 'ack_num', 'ack_date', 'eta']
    fields = "__all__" 

class OrderItemFormHelper(FormHelper):
  def __init__(self, *args, **kwargs):
    super(OrderItemFormHelper, self).__init__(*args, **kwargs)
    self.form_tag = False
    self.disable_csrf = True
    self.layout = Layout(
      Div(
        'status', 
        'in_stock',
        'description',
        css_class='item-general-fields',
      ),
      Div(
        Field('po_num', wrapper_class='field-wrapper inline'),
        AppendedText('po_date', '<i class="icon-calendar"></i>', css_classes='field-wrapper inline'),
        Field('ack_num', wrapper_class='field-wrapper inline clear'), 
        AppendedText('ack_date', '<i class="icon-calendar"></i>'),
        HTML('<br/>'),
        AppendedText('eta', '<i class="icon-calendar"></i>'), 
        css_class='item-special-fields',
      ),
      Div(
        Field('DELETE', css_class='input-small'),
      ),
    )


class OrderForm(forms.ModelForm):
  customer = AutoCompleteSelectField('customer', required=False)
  
  def __init__(self, *args, **kwargs):
    super(OrderForm, self).__init__(*args, **kwargs)
    
    self.fields['number'].label = "Order/Receipt #"
    self.fields['number'].required = True
    
    self.fields['status'].initial='N'
    self.fields['status'].required = True
    
    #self.fields['order_date'].widget = BootstrapDateInput()
    self.fields['order_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['order_date'].label = "Ordered Date"
    self.fields['order_date'].widget.attrs['class'] += " order-date"
    
    self.fields['subtotal_after_discount'].required = True

  def clean_number(self):
    ''' 
    SO number validation: make sure that order 
    numbers are valid according to specific format
    '''
    number = self.cleaned_data.get('number')
    if not order_utils.is_valid_order_number(number):
      raise forms.ValidationError("Order number should be in the following format: %s" % settings.ORDER_FORMAT_DESC)
    elif order_utils.is_duplicate_order_exists(number, self.instance):
      raise forms.ValidationError("Order with the same number already exists")
    return number
    
  class Meta:
    model = Order
    fields = "__all__" 

class CommissionForm(forms.ModelForm):

  def __init__(self, *args, **kwargs):
    self.request = kwargs.pop('request', None)
    super(CommissionForm, self).__init__(*args, **kwargs)
    #self.fields['paid_date'].widget = BootstrapDateInput()
    self.fields['paid_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['paid_date'].widget.attrs['layout'] = 'inline';
    self.fields['associate'].required = True
    user_model = get_user_model() 
    self.fields['associate'].queryset = user_model.objects.filter(Q(groups__name__icontains="associates") | Q(groups__name__icontains="managers" ))
    
    if self.request and not self.request.user.has_perm('commissions.update_commissions_payment'):
      # person can modify only certain delivery info data
      self.fields['paid_date'].widget.attrs['disabled'] = 'disabled'
      self.fields['paid'].widget.attrs['disabled'] = 'disabled'

  class Meta:
     model = Commission
     fields = "__all__" 

class OrderDeliveryForm(forms.ModelForm):

  def __init__(self, *args, **kwargs):
    self.request = kwargs.pop('request', None)
    super(OrderDeliveryForm, self).__init__(*args, **kwargs)

    self.fields['scheduled_delivery_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['delivered_date'].widget = DateTimePicker(options=DATEPICKER_OPTIONS)
    self.fields['pickup_from'].required = False
    #self.fields['delivery_cost'].widget = BootstrapTextInput(prepend='$')
    self.fields['delivery_cost'].initial = 0.0
    self.fields['paid'].widget = Select(choices = ((0,"No"), (1, "Yes")));
    self.fields['paid'].initial = False
    #self.fields['delivery_cost'].initial = 0.00
    
    disabled_fields = ['order']
    self.fields_to_disable = []
    self.fields_to_remove = []
    
    if self.request:
      if utils.is_user_delivery_group(self.request):
        # person can modify only certain delivery info data
        visible_fields = ('scheduled_delivery_date', 'delivered_date', 'comments', 'delivery_person_notes', 'delivery_cost', 'paid')
        disabled_fields += ['comments', 'paid']
        self.fields_to_remove = [f for f in self.fields if f not in visible_fields]
        
        for field in self.fields_to_remove: 
          del self.fields[field]
      elif self.request.user.groups.filter(Q(name="managers") | Q(name="associates")).exists() :
        disabled_fields.append('delivery_person_notes')
        disabled_fields.append('delivery_cost')
        
        if not self.request.user.has_perm('orders.modify_delivery_fee'):
          disabled_fields.append('paid')
      
      self.fields_to_disable = [f for f in self.fields if f in disabled_fields]
      
      for field in self.fields_to_disable: 
          self.fields[field].widget.attrs['disabled'] = 'disabled'
  
  def clean(self):
    cleaned_data = super(OrderDeliveryForm, self).clean()
    for field in self.fields_to_disable:
      val = getattr(self.instance, field)
      cleaned_data[field] = val or self.fields[field].initial
    
    #validation
    try:
      if cleaned_data['pickup_from'] == None and cleaned_data['delivery_type']:
        self._errors['pickup_from'] = ErrorList([u'Please specify pickup from location'])
      elif cleaned_data['delivery_type'] == None and cleaned_data['pickup_from']:
        self._errors['delivery_type'] = ErrorList([u'Please specify delivery type'])

      if cleaned_data['delivery_cost'] is None:
        cleaned_data['delivery_cost'] = 0.0

      if cleaned_data['delivery_type'] == 'SELF' and cleaned_data['delivery_cost'] > 0:
        self._errors['delivery_cost'] = ErrorList([u"Cannot assign delivery cost to 'Self Pickup' orders"])

    except KeyError as e:
      pass
    
    return cleaned_data
    
  class Meta:
    model = OrderDelivery
    fields = "__all__" 

class CustomerForm(forms.ModelForm):
  def __init__(self, *args, **kwargs):
    super(CustomerForm, self).__init__(*args, **kwargs)

  class Meta:
    model = Customer
    fields = "__all__" 

class CustomerDetailReadOnlyForm(DisabledFieldsMixin, CustomerForm):
  def __init__(self, *args, **kwargs):
    super(CustomerDetailReadOnlyForm, self).__init__(*args, **kwargs)

class OrderIssueForm(forms.ModelForm):
  pass
  
class DateRangeForm(forms.Form):
  REPORT_FILTER_CHOICES = (
    #("", "<Default>"),
    ("week", "This Week"),
    ("last-week", "Last Week"),
    ("month", "This month"),
    ("last-month", "Last month"),
    ("year", "Year-to-date"),
    ("custom", "Select date range"),
  )
  date_range = forms.ChoiceField(label="Filter by Date Range", required=False, choices=REPORT_FILTER_CHOICES) #choices=REPORT_FILTER_CHOICES, initial="custom")
  range_from = forms.DateField(label="From", required=False, widget=BootstrapDateInput())
  range_to = forms.DateField(label="To", required=False, widget=BootstrapDateInput())
  
  def __init__(self, *args, **kwargs):
    super(DateRangeForm, self).__init__(*args, **kwargs)
    #self.initial['date_range'] = 'custom'  #default selection

    self.helper = FormHelper()
    self.form_tag = False
    self.disable_csrf = True
    self.helper.form_class = 'form-inline'
    self.helper.field_template = 'bootstrap3/layout/inline_field.html'
    self.helper.layout = Layout(
        Div(
          HTML (
            '<h3>Select date range</h3>'
          ),
          'date_range',
          'range_from',
          'range_to',
          Submit('submit', 'Filter', css_class='btn-default'),
          css_class = 'well'
        )
    )

    
def get_ordered_items_formset(extra=1, max_num=1000):
  return inlineformset_factory(Order, OrderItem, form=OrderItemForm, fields='__all__', extra=extra, max_num=max_num)

def get_deliveries_formset(extra=1, max_num=1000, request=None):
  formset = inlineformset_factory(Order, OrderDelivery, fields='__all__', extra=extra, max_num=max_num, can_delete=False)
  formset.form = staticmethod(curry(OrderDeliveryForm, request=request))
  return formset

def get_commissions_formset(extra=1, max_num=1000, request=None):
  formset = inlineformset_factory(Order, Commission, fields='__all__', extra=extra, max_num=max_num, can_delete=True)
  formset.form = staticmethod(curry(CommissionForm, request=request))
  return formset

def get_order_issues_formset(extra=1, max_num=1000, request=None):
  return inlineformset_factory(Order, OrderIssue, form=OrderIssueForm, fields='__all__', extra=extra, max_num=max_num, can_delete=True)

#inline formsets
ItemFormSet = inlineformset_factory(Order, OrderItem, form=OrderItemForm, fields='__all__', extra=1, max_num=100)
DeliveryFormSet = inlineformset_factory(Order, OrderDelivery, form=OrderDeliveryForm, fields='__all__', extra=1, max_num=100)
CommissionFormSet = inlineformset_factory(Order, Commission, form=CommissionForm, fields='__all__', extra=1, max_num=100, can_delete=False)
CustomerFormSet = modelformset_factory(Customer, form=CustomerForm, fields='__all__', extra=1, max_num=1)
OrderAttachmentFormSet = inlineformset_factory(Order, OrderAttachment, fields='__all__', extra=1, max_num=5)
CryptonProtectionFormSet = inlineformset_factory(Order, OrderItemProtectionPlan, fields='__all__', extra=1, max_num=1)
OrderFinancingFormSet = inlineformset_factory(Order, OrderFinancing, fields='__all__', extra=1, max_num=1)
