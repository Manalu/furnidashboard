import django_tables2 as tables
from django.utils.safestring import mark_safe
from django_tables2.utils import A #accessor
from .models import Order, OrderDelivery
from core.tables import CustomTextLinkColumn
import core.utils as utils

class AssociateColumn(tables.Column):
  def render(self, value):
    commissions = value.all()
    associates = ", ".join([comm.associate.first_name for comm in commissions])
    return mark_safe(associates)

class OrderTable(tables.Table):
  order_date = tables.TemplateColumn('{{ record.order_date|date:\'m/d/Y\'}}') 
  modified = tables.TemplateColumn('{{ record.modified|date:\'m/d/Y\'}}', verbose_name="Last Modified") 
  # detail = tables.TemplateColumn('<a href="{% url \'order_detail\' record.pk %}">Detail</a>', verbose_name="Actions", orderable=False)
  pk = CustomTextLinkColumn('order_detail', args=[A('pk')], custom_text="Detail", orderable=False, verbose_name="Actions")
  associate = AssociateColumn(accessor="commission_set", verbose_name="Associate")
  grand_total = tables.Column(orderable=False)

  def render_grand_total(self, value):
    return utils.dollars(value)

  class Meta:
    model = Order
    attrs = {"class": "paleblue"}
    fields = ("number", "order_date", "status", "store", "customer", "grand_total", "modified", "associate")

class UnplacedOrdersTable(tables.Table):

  order_date = tables.TemplateColumn('{{ record.order_date|date:\'m/d/Y\'}}') 
  detail = tables.TemplateColumn('<a href="{% url \'order_detail\' record.pk %}">Detail</a>', verbose_name="Actions", orderable=False)
  associate = AssociateColumn(accessor="commission_set", verbose_name="Associate")
  grand_total = tables.Column(orderable=False)

  class Meta:
    model = Order
    attrs = {"class": "paleblue urgent"}
    fields = ("number", "order_date", "customer", "grand_total", "associate", "detail")

class SalesByAssociateTable(tables.Table):
  associate = tables.Column(orderable=False)
  sales = tables.Column()

  def render_sales(self, value):
    return utils.dollars(value)

  class Meta:
    order_by='-sales'
    attrs = {"class":"paleblue"}

class DeliveriesTable(tables.Table):
  order = tables.LinkColumn('order_detail', args=[A('order.pk')])
  pk = CustomTextLinkColumn('delivery_detail', args=[A('pk')], custom_text="Detail", orderable=False, verbose_name="Actions")
  customer = tables.Column(accessor="order.customer", verbose_name="Customer")

  class Meta:
    model = OrderDelivery
    attrs = {"class":"paleblue"}
    fields = ("order", "customer", "scheduled_delivery_date", "delivery_type", 'delivered_date') 

class SalesTotalsTable(tables.Table):
  item = tables.Column(verbose_name="-", orderable=False)
  hq = tables.Column(verbose_name="HQ/Sacramento", orderable=False)
  fnt = tables.Column(verbose_name="Roseville", orderable=False)
  total = tables.Column(verbose_name="Total", orderable=False)

  class Meta:
    attrs = {"class":"paleblue"}

