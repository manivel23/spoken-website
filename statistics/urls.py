from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    # Main pages dispatcher
    url(r'^$', 'statistics.views.maphome', name="maphome"),
    url(r'^india-map/$', 'statistics.views.maphome', name="maphome"),
    url(r'^get-state-info/(\w+)/$', 'statistics.views.get_state_info', name="get_state_info"),
    url(r'^training/$', 'statistics.views.training', name="statistics_training"),
    url(r'^training/(?P<slug>[\w-]+)/$', 'statistics.views.training', name="statistics_training"),
    url(r'^training/(?P<model>[\w-]+)/(?P<rid>\d+)/participant/$', 'statistics.views.training_participant', name="statistics_training_participant"),
    url(r'^academic-center/$', 'statistics.views.academic_center', name="acdemic_center"),
    url(r'^academic-center/(?P<academic_id>\d+)/$', 'statistics.views.academic_center_view', name="academic_center_view"),
    url(r'^academic-center/(?P<academic_id>\d+)/(?P<slug>[\w-]+)/$', 'statistics.views.academic_center_view', name="academic_center_view"),
)
