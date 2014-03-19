from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from orders.models import Order
from customers.models import Customer
from orders.views import OrderListView, OrderUpdateView, OrderDetailView, OrderCreateView, OrderDeleteView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='base.html')),
    url(
        regex= r'^orders/$', 
        view=OrderListView.as_view(),
        name="order_list",
    ),
    url(
        regex = r'^orders/(?P<pk>\d+)/$', 
        view=OrderDetailView.as_view(),
        name="order_detail",
    ),
    url(
        regex = r'^orders/(?P<pk>\d+)/edit/$', 
        view=login_required(OrderUpdateView.as_view()),
        name="order_edit",
    ),
    url(
        regex = r'^orders/(?P<pk>\d+)/delete/$', 
        view=login_required(OrderDeleteView.as_view()),
        name="order_delete",
    ),
    url(r'orders/add/$', login_required(OrderCreateView.as_view()), name="order_add"),
    url(r'orders/(?P<pk>\d+)/delete/$', login_required(OrderDeleteView.as_view()), name="order_delete"),
    url(r'customers/$', login_required(ListView.as_view(model=Customer, template_name="customers/customer_list.html")), name="customer_list"),

    # authentication-related URLs
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    url(r'^accounts/', include('django.contrib.auth.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # administration URLs 
    url(r'^admin/', include(admin.site.urls)),
)
