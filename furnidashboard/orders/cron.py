from django.utils import timezone
from django.conf import settings
from django_cron import CronJobBase, Schedule
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Order
from stores.models import Store
import order.utils as order_utils
from datetime import datetime
from django.core.mail.message import EmailMessage

class FurnCronJob(CronJobBase):
  MIN_NUM_FAILURES = 3

  def trace(self, txt, important=False):
    print txt

    if txt.strip() == "":
      txt = "<br/>"

    if important:
      txt = "<strong>" + txt + "</strong>"

    self.msg.append(txt)

  def send_emails(self, to=None, subject="", message="", from="admin@furnitalia.com"):
    if len(trim(message)) = 0 :
      return

    if to = None :
      to = settings.CRON_EMAIL_NOTIFICATION_LIST

    report_date = datetime.now().strftime('%m-%d-%Y')    
    if subject = "":
      subject = "FurniCloud Report (" + report_date + ")"
    else:
      subject = subject + " | " + report_date
    
    message = 'Report created on ' + report_date + '<br/><br/>' + message
    email_msg = EmailMessage(subject, message, from, to) 
    email_msg.content_subtype = "html"
    email_msg.send()

  # def send_emails(self):

  #   report_date = datetime.now().strftime('%m-%d-%Y')
  #   to = ['akhmirem@gmail.com', 'lana@furnitalia.com', 'd.aks@furnitalia.com', 'pearl@furnitalia.com', 'ruth@furnitalia.com', 'jenn@furnitalia.com', 'jamie@furnitalia.com']
  #   self.msg[:0] = ['Report created on ' + report_date, ""]
  #   email_msg = EmailMessage("FurniCloud Report (" + report_date + ")", "<br/>".join(self.msg), "admin@furnitalia.com", to) 
  #   email_msg.content_subtype = "html"
  #   email_msg.send()


class UnplacedOrderCronJob(FurnCronJob):
  code = 'orders.cron.UnplacedOrderCronJob'  
  msg = []
  report_is_blank = True

  #this job will run only at 6am
  RUN_AT_TIMES = ['6:00']   
  schedule = Schedule(run_at_times=RUN_AT_TIMES)  

  def do(self):
    self.trace("UNPLACED special orders (missing PO numbers): ", important=True)
    unplaced = Order.objects.unplaced_orders()
    self.trace("There are {0} unplaced orders".format(unplaced.count()), important=True)
    
    if unplaced.count() > 0 :
      self.report_is_blank = False

    for counter, o in enumerate(unplaced):
      self.trace("{0}) {1} unplaced. View order: http://cloud.furnitalia.com{2}".format(counter, o.number, o.get_absolute_url()))
    self.trace("-" * 40)
    self.trace("")

    self.trace("List of UNCONFIRMED special orders (missing acknowledgement# from vendor):", important=True)
    orders_no_ack_no = Order.objects.ordered_not_acknowledged()
    self.trace("There are {0} unconfirmed orders".format(orders_no_ack_no.count(), important = True))

    if orders_no_ack_no.count() > 0 :
      self.report_is_blank = False

    for counter, o in enumerate(orders_no_ack_no):
      self.trace("{0}) {1} View order: http://cloud.furnitalia.com{1}".format(counetr, o.number, o.get_absolute_url()))
    self.trace("-" * 40)

    # send email notifications
    if not self.report_is_blank:
      self.send_emails (
        to=['lana@furnitalia.com', 'dima.aks@furnitalia.com', 'admin@furnitalia.com'],
        message="<br/>".join(self.msg),
        subject ="Notification about Unplaced Orders at FurniCloud"
      )

class UnplacedOrderByAssocCronJob(UnplacedOrderCronJob):
  code = 'orders.cron.UnplacedOrderByAssocCronJob'  

  def do(self):

    user_model = get_user_model()
    associates = user_model.objects.filter(Q(is_active=True) & Q(groups__name__icontains="associates"))

    for associate in associates:
      self.report_is_blank = True
      self.msg = []
      if len(associate.email):
        unplaced = Order.objects.unplaced_orders().filter(commission__associate=associate)
        if unplaced.count():
          self.report_is_blank = False
          self.trace("There are {0} UNPLACED special orders (missing PO numbers): ".format(unplaced.count()), important=True)
          for counter, o in enumerate(unplaced):
            self.trace("{0}) {1} unplaced. View order: http://cloud.furnitalia.com{2}".format(counter, o.number, o.get_absolute_url()))
          self.trace("-" * 40)
          self.trace("Please bring to Lana's or Dmitriy's attention that your orders need to be placed with the vendor!")
          self.trace("")

        orders_no_ack_no = Order.objects.ordered_not_acknowledged().filter(commission__associate=associate)
        if orders_no_ack_no.count():
          self.report_is_blank = False
          self.trace("There are {0} UNCONFIRMED orders  (missing acknowledgement# from vendor)".format(orders_no_ack_no.count(), important = True))
          for counter, o in enumerate(orders_no_ack_no):
            self.trace("{0}) {1} View order: http://cloud.furnitalia.com{1}".format(counetr, o.number, o.get_absolute_url()))
          self.trace("-" * 40)
          self.trace("Please check with Lana regarding the status of this order.")

        # send email notifications
        if not self.report_is_blank:
          assoc_email = associate.email
          self.send_emails (
            to=[assoc_email 'admin@furnitalia.com'],
            message="<br/>".join(self.msg),
            subject ="Notification about your Order status in FurniCloud"
          )

  

class OrderCronJob(FurnCronJob):
  code = 'orders.cron.OrderCronJob'
  msg = []
  report_is_blank = True

  # cron job will run at 6:30am
  RUN_AT_TIMES = ['6:30']
  schedule = Schedule(run_at_times=RUN_AT_TIMES)  

  def do(self):

    orders_missing = self.determine_potentially_missed_orders()    
    if orders_missing:
      self.report_is_blank = False
      self.trace("There are {0} potentially missed orders.".format(len(orders_missing)), important=True)
      for o in orders_missing:
        self.trace(str(o))
      self.trace("")
      self.trace("*NOTE: please verify that your orders have been entered. If the POS order is a quote, select a status of 'Dummy' for order in FurniCloud.", important=True)
      self.trace("-" * 40)
      self.trace("")

    self.trace("10 most recent orders:", important=True)
    recent_orders = Order.objects.filter(status__exact='N').order_by('-order_date')[:10]
    for o in recent_orders:
       self.trace("Order {0}, created {1}, status: {2}, associate(s): {3}".format(o.number, 
          o.order_date.strftime("%m-%d-%Y"), o.get_status_display(), order_utils.get_order_associates(o)))
    self.trace("-" * 40)
    self.trace("")

    self.trace("*" * 40)
    self.trace("Please visits the 'Alerts' page on FurniCloud for full report".upper(), important=True)
    self.trace("*" * 40)
       
    # send email notifications
    if not self.report_is_blank:
      self.send_emails(message="<br/>".join(self.msg))

  def determine_potentially_missed_orders(self):
    res = []
    #launch_dt = datetime(2014, 6, 1)
    #if settings.USE_TZ:
    #  launch_dt = timezone.make_aware(launch_dt, timezone.get_current_timezone())

    #orders = Order.objects.filter(order_date__gte=launch_dt, number__istartswith="SO") 
    orders = Order.objects.get_qs().filter(number__istartswith="SO")
    
    sac_orders = orders.filter(store=Store.objects.get(name="Sacramento"))
    fnt_orders = orders.filter(store=Store.objects.get(name="Roseville"))

    sac_order_nums = sorted(map(lambda o: int(o.number[-4:]), sac_orders))
    fnt_order_nums = sorted(map(lambda o: int(o.number[-4:]), fnt_orders))
    
    lst = self.find_skipped_order_nums(sac_order_nums, "SO-1")
    if lst:
      res += lst

    lst = self.find_skipped_order_nums(fnt_order_nums, "SO-3")
    if lst:
      res += lst

    return res

  def find_skipped_order_nums(self, order_nums, prefix):

    res = []
    err_msg = "MISSING order #{0}{1:04d}"

    if order_nums:
      first = order_nums[0]
      expected = first + 1
      for num in order_nums[1:]:
        if num != expected:
          res.append(err_msg.format(prefix, expected))
          expected = expected + 1
          while expected < num:
            res.append(err_msg.format(prefix, expected))
            expected = expected + 1
          if expected <= num:
            expected = expected + 1
        else:
          expected = num + 1

    return res
