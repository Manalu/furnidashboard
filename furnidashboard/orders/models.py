from django.db import models
from django.core.urlresolvers import reverse
from audit_log.models import AuthStampedModel
from django_extensions.db.models import TimeStampedModel
from customers.models import Customer
from stores.models import Store
from orders.managers import OrderManager
  
class Order(TimeStampedModel, AuthStampedModel):
  """
  A model class representing Order data
  """
  ORDER_STATUSES = (
    ('N', 'New'),
    ('Q', 'Pending'),
    ('H', 'On Hold'),
    ('E', 'Cancelled'),
    ('P', 'In Production'),
    ('T', 'In Transit'),
    ('S', 'Scheduled for Delivery'),
    ('D', 'Delivered'),
    ('X', 'Dummy'),
    ('I', 'Historical (Excel Import)'),
    ('C', 'Closed'),
  )

  REFERRAL_SOURCES = (
    ('NO', 'Not Referred'),
    ('RVL', 'Roseville Store'),
    ('CST', 'Referred by existing Furnitalia customer'), 
    ('REF', 'Referred by friends/relatives/acquaintances'),
    ('WEB', 'Website'),
    ('EBL', 'E-mail (or Eblast)'),
    ('MAG', 'Magazine'),
    ('SOC', 'Social networks'),
    ('NWP', 'Newspaper'),
    ('TV', 'TV'),
  )

  number = models.CharField(max_length=50)
  order_date = models.DateTimeField(null=True)
  customer = models.ForeignKey(Customer, default=0, blank=True, null=True)
  status = models.CharField(max_length=5, choices=ORDER_STATUSES)
  deposit_balance = models.FloatField(blank=True, default=0.0)
  subtotal_after_discount = models.FloatField(blank=True, default=0.0)
  tax = models.FloatField(blank=True, default=0.0)
  shipping = models.FloatField(blank=True, default=0.0)
  comments = models.TextField(blank=True)
  store = models.ForeignKey(Store)
  referral = models.CharField(blank=True, null=True, max_length=50, choices=REFERRAL_SOURCES)
  protection_plan = models.BooleanField(default=False, blank=True)
  financing_option = models.BooleanField(default=False, blank=True)
  
  #objects = models.Manager()      #default
  objects = OrderManager() #customer manager

  @property
  def not_placed(self):
           # no status        'new'                 'any item, which is not in stock, and does not have po#
    #return not self.status or self.status == 'N' or any([item for item in self.orderitem_set if not item.in_stock and not item.po_num])
    return any([item for item in self.orderitem_set.all() if item.status not in ("S", "I") and item.po_num == ''])

  @property
  def balance_due(self):
    """ Balance due after the deposits """
    return self.grand_total - self.deposit_balance

  @property
  def grand_total(self):
    """ Grand Total (Subtotal + tax + shipping) """
    return self.subtotal_after_discount + self.tax + self.shipping

  class Meta:
    ordering = ["-order_date"]
    db_table = "order_info"
    permissions = (
        ("view_orders", "Can View Orders"),
        ("view_sales", "Can View Sales Reports"),
        ("update_status", "Can Update Order Status"),
    )
  
  def __unicode__(self):
    return "#{0}".format(self.number)

  def get_absolute_url(self):
    return reverse("order_detail", kwargs={"pk":self.pk})


class OrderItem(TimeStampedModel, AuthStampedModel):
  """
  A model class representing Items Ordered (stock items, special order items, etc).
  """
  ITEM_STATUSES = (
    ('P', 'Pending'),
    ('O', 'Ordered'),
    ('R', 'Received'),
    ('D', 'Delivered'),
    ('S', 'In Stock'),
    ('I', 'Historical (Excel Import)'),
  )

  order = models.ForeignKey(Order)
  status = models.CharField(max_length=15, choices=ITEM_STATUSES, blank=True, null=True)
  in_stock = models.BooleanField(default=True, blank=True)
  description = models.CharField(max_length=255)
  po_num = models.CharField(max_length=125, blank=True)
  po_date = models.DateField(blank=True, null=True)
  ack_num = models.CharField(max_length=125, blank=True)
  ack_date = models.DateField(blank=True, null=True)
  eta = models.DateField(blank=True, null=True)

  class Meta:
    db_table = "order_items"
    verbose_name_plural = "ordered items"
  
class OrderDelivery(TimeStampedModel, AuthStampedModel):
  """
  A model class representing deliveries tracking for Orders 
  """

  DELIVERY_TYPES = (
      ('SELF', 'Self Pickup'),
      ('RFD', 'Roberts Furniture Delivery'),
      ('MGL', 'Miguel'),
      ('CUSTOM', 'Other'),
  )

  order = models.ForeignKey(Order)
  delivery_type =  models.CharField(max_length=25, choices=DELIVERY_TYPES, blank=True, null=True)
  scheduled_delivery_date = models.DateField(null=True, blank=True)
  delivered_date = models.DateField(null=True, blank=True)
  pickup_from = models.ForeignKey(Store, blank=True, null=True)
  delivery_slip = models.FileField(upload_to='deliveries/%Y/%m', blank=True, null=True)
  comments = models.TextField(blank=True, null=True)
  delivery_person_notes = models.TextField(blank=True, null=True)
  delivery_cost = models.FloatField(blank=True, default=0.0)
  paid = models.BooleanField(default=False, blank=True)

  def get_absolute_url(self):
    return reverse("delivery_detail", kwargs={"pk":self.pk})

  @property
  def delivery_slip_filename(self):
    if self.delivery_slip:
      import os
      return os.path.basename(self.delivery_slip.name)
    else :
      return ""

  class Meta:
    db_table = "deliveries"
    verbose_name_plural = "deliveries"
    permissions = (
      ("modify_delivery_fee", "Modify Delivery Fee"),
    )

class Attachment(models.Model):
  file = models.FileField(upload_to='attachments/%Y/%m')
  description = models.CharField(max_length=255, blank=True, null=True)

  class Meta:
    abstract = True

  @property
  def filename(self):
    import os
    return os.path.basename(self.file.name)

  def __unicode__(self):
    return self.description[:30]

class OrderAttachment(Attachment):
  """
  A class representing file attachments for an order
  """
  order = models.ForeignKey(Order)
  class Meta:
    db_table = "order_attachments"

class OrderIssue(TimeStampedModel, AuthStampedModel):
  """
  A class representing order issues
  """
  ISSUE_STATUSES =  (
    ('N', 'New'),
    ('C', 'Claim submitted'),
    ('T', 'Technician sent'),
    ('E', 'Eligible for Credit'),
    ('R', 'Resolved'),
  )

  order = models.ForeignKey(Order)
  status = models.CharField(max_length=5, choices=ISSUE_STATUSES)
  comments = models.TextField(blank=True, null=True)

  class Meta:
    db_table = "order_issues"
    ordering = ['-created']
    permissions = (
      ("update_order_issues", "Can Update Order Issues (Claims)Information"),
    )

class OrderFinancing(models.Model):
  """ 
  Stores financing details for sold orders 
  """

  order = models.ForeignKey(Order)
  approval_no = models.CharField(max_length=50, blank=False, null=False)
  details = models.TextField(blank=True, null=True)

class OrderItemProtectionPlan(models.Model):
  """ 
  Stores protection plan details for sold items 
  """

  order = models.ForeignKey(Order)
  approval_no = models.CharField(max_length=50, blank=False, null=False)
  details = models.TextField(blank=True, null=True)

