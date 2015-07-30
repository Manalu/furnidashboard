from datetime import datetime, timedelta
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from orders.models import Order, OrderItem
import re

def calc_commissions_for_order(order):
  # returns the list containing key-value commissions data
  # per associate
  
  coms = []

  associates_cnt = order.commission_set.count()
  comm_queryset = order.commission_set.select_related().all() 
  for com in comm_queryset:
    sales_amount = order.subtotal_after_discount / float(associates_cnt)
    comm_amount = sales_amount * settings.COMMISSION_PERCENT

    if com.paid:
      amount_paid = comm_amount
      amount_pending = 0.0
      amount_due = 0.0
    else :
      amount_paid = 0.0
      #commission is pending if order status is not Dummy, Delivered, or Closed
      amount_pending = comm_amount if order.status not in ('D', 'X', 'C') else 0.0 
      #otherwise, if order is Delivered, or Closed, commission is due
      amount_due= comm_amount if order.status in ('D', 'C') else 0.0

    temp_subtotal = {
        'associate': com.associate.first_name,
        'sale': sales_amount, 
        'commissions_pending': amount_pending, 
        'commissions_due': amount_due, 
        'commissions_paid': amount_paid
    }

    coms.append(temp_subtotal)
  
  return coms


def _calc_sales_assoc_by_orders(order_list, **kwargs):
  # returns a list of commissions data stored as key-val pair

  res = {}
  expand_res = {}
  
  for o in order_list:

    #get order subtotal and commissions
    order_coms = calc_commissions_for_order(o)

    for com in order_coms:

      #save order info into expanded result list
      if not expand_res.has_key(com['associate']):
        expand_res[com['associate']] = []

      item = o.orderitem_set.all()[:1].get().description
      if len(item) > 30:
        item = item[:30] + "..." 
      sales_data = {
        'order_number':o.number, 
        'order_date': datetime.strftime(o.order_date, '%m-%d-%Y'), 
        'item':item, 
        'amount':com['sale'], 
        'commissions_pending':com['commissions_pending'], 
        'commissions_due':com['commissions_due'], 
        'commissions_paid':com['commissions_paid'],
        'order_pk':o.pk, 
      }
      expand_res[com['associate']].append(sales_data)        

      #count up subtotals
      if res.has_key(com['associate']):
        res[com['associate']]['sale'] += com['sale'] 
        res[com['associate']]['commissions_pending'] += com['commissions_pending'] 
        res[com['associate']]['commissions_due'] += com['commissions_due'] 
        res[com['associate']]['commissions_paid'] += com['commissions_paid'] 
      else:
        res[com['associate']] =  com

  sales_list = []
  for associate, temp_subtotal in res.items():
    
    if 'old_bonus' in kwargs.keys() and kwargs.get('old_bonus') :
      bonus = _calc_bonus_amount__old(temp_subtotal['sale'])
    else:
      bonus = _calc_bonus_amount(temp_subtotal['sale'])

    sales_list.append({
      'associate':          associate, 
      'sales':              temp_subtotal['sale'], 
      'commissions_due':    temp_subtotal['commissions_due'], 
      'commissions_paid':   temp_subtotal['commissions_paid'],
      'commissions_pending':temp_subtotal['commissions_pending'],
      'bonus':              bonus
    })

  return sales_list, expand_res

def _calc_bonus_amount(sales_amount):
  bonus = 0.0
  
  if 20000.0 <= sales_amount < 25000.0:
    bonus = 50.0
  elif 25000.0 <= sales_amount < 30000.0:
    bonus = 100.0
  elif 30000.0 <= sales_amount < 35000.0:
    bonus = 175.0
  elif 35000.0 <= sales_amount < 40000.0:
    bonus = 250.0
  elif 40000.0 <= sales_amount < 45000.0:
    bonus = 350.0
  elif 45000.0 <= sales_amount < 50000.0:
    bonus = 450.0
  elif 50000.0 <= sales_amount < 55000.0:
    bonus = 575.0
  elif 55000.0 <= sales_amount < 60000.0:
    bonus = 700.0
  elif 60000.0 <= sales_amount < 65000.0:
    bonus = 825.0
  elif 65000.0 <= sales_amount < 70000.0:
    bonus = 975.0
  elif 70000.0 <= sales_amount < 75000.0:
    bonus = 1125.0
  elif 75000.0 <= sales_amount < 80000.0:
    bonus = 1300.0
  elif 80000.0 <= sales_amount < 85000.0:
    bonus = 1475.0
  elif 85000.0 <= sales_amount < 90000.0:
    bonus = 1675.0
  elif 90000.0 <= sales_amount < 95000.0:
    bonus = 1900.0
  elif 95000.0 <= sales_amount < 100000.0:
    bonus = 2150.0
  elif sales_amount >= 100000.0:
    bonus = 2500.0

  return bonus

def _calc_bonus_amount__old(sales_amount):
  bonus = 0.0

  if 25000.0 <= sales_amount < 35000.0:
    bonus = 50.0
  elif 35000.0 <= sales_amount < 45000.0:
    bonus = 100.0
  elif 45000.0 <= sales_amount < 50000.0:
    bonus = 150.0
  elif 50000.0 <= sales_amount < 60000.0:
    bonus = 200.0
  elif 60000.0 <= sales_amount < 75000.0:
    bonus = 250.0
  elif sales_amount >= 75000.0:
    bonus = 300.0

  return bonus

def is_valid_order_number(number):
  return re.match(settings.ORDER_FORMAT_REGEX, number) != None

def is_duplicate_order_exists(number, instance):
  try:
    o = Order.objects.get(number__iexact=number)

    if instance != None and instance.pk and o.pk == instance.pk:
      return False
    
    return True

  except Exception :
    return False
    
def get_date_range(range_str, request):
  
  to_date = datetime.now()
  if range_str == 'week':
    from_date = to_date - timedelta(days=to_date.weekday())
    from_date = from_date.replace(hour=0, minute=0, second=0)
  if range_str == 'last-week':
    to_date = to_date - timedelta(days=to_date.weekday())
    to_date = to_date.replace(hour=0, minute=0, second=0)
    from_date = to_date - timedelta(days=7)
  elif range_str == 'month':
    from_date = datetime(to_date.year, to_date.month, 1)
  elif range_str == 'last-month':
    to_date = datetime(to_date.year, to_date.month, 1)
    from_date = to_date - timedelta(days=1)
    from_date = datetime(from_date.year, from_date.month, 1)
  elif range_str == 'year':
    from_date = datetime(to_date.year, 1, 1)
  elif range_str == 'custom':
    try:
      from_date = datetime.strptime(request.GET['range_from'], "%Y-%m-%d")
      to_date = datetime.strptime(request.GET['range_to'], "%Y-%m-%d")
      to_date = to_date.replace(hour=23, minute=59, second=59)
    except (KeyError, ValueError) as e:
      #raise ValueError("Incorrect date format, should be YYYY-MM-DD")
      messages.add_message(request, messages.ERROR, "Incorrect date format, should be YYYY-MM-DD", extra_tags="alert alert-danger")
      from_date = to_date - timedelta(days=to_date.weekday())
      from_date = from_date.replace(hour=0, minute=0, second=0)
  else: #default
    from_date = to_date - timedelta(days=to_date.weekday())
    from_date = from_date.replace(hour=0, minute=0, second=0)
  
  return (from_date, to_date)

def get_order_associates(order): 
  assoc_list = []
  comm_queryset = order.commission_set.select_related().all() 
  for com in comm_queryset:
    assoc_list.append(com.associate.first_name)

  return ", ".join(assoc_list)

def list_unconfirmed_orders(by_associate=None):
  
  #items that have PO# but don't have Acknowledgement #
  unconfirmed_items = OrderItem.objects.exclude(po_num="").filter(ack_num="").select_related('order').exclude(order__status='I')

  import pdb; pdb.set_trace()
  if by_associate:
    #filter by specific associate
    unconfirmed_items.filter(order__commission__associate=by_associate)

  orders = (i.order for i in unconfirmed_items)

  return orders

def list_unplaced_orders(by_associate=None):
  
  #items that are not 'In Stock' and don't have PO#
  unplaced_items = OrderItem.objects.filter(in_stock=False, po_num="")#.select_related('order') 

  if associate:
    #filter by specific associate
    unplaced_items.filter(order__commission__associate=associate)

  orders = set([i.order for i in unplaced_items if i.order.status != 'I'])

  return tuple(orders)

