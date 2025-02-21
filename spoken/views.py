from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.conf import settings
from forms import *
import os
from django.http import Http404
from django.core.exceptions import PermissionDenied
from urllib import urlopen, quote, unquote_plus
import json
import datetime
from dateutil.relativedelta import relativedelta
from creation.subtitles import *
from creation.views import get_video_info, is_administrator
from creation.models import TutorialCommonContent, TutorialDetail, TutorialResource, Language
from cms.models import SiteFeedback, Event, NewsType, News
from events.views import get_page
from mdldjango.models import MdlUser

def is_resource_person(user):
    """Check if the user is having resource person  rights"""
    if user.groups.filter(name='Resource Person').count() == 1:
        return True

@csrf_exempt
def site_feedback(request):
    data = request.POST
    if data:
        try:
            SiteFeedback.objects.create(name=data['name'], email = data['email'], message = data['message'])
            data = True
        except Exception, e:
            print e
            data = False
            
    return HttpResponse(json.dumps(data), mimetype='application/json')

def home(request):
    tr_rec = ''
    
    foss = list(TutorialResource.objects.filter(Q(status = 1) | Q(status = 2)).order_by('?').values_list('tutorial_detail__foss_id').distinct()[:9])
    random_tutorials = []
    eng_lang = Language.objects.get(name='English')
    for f in foss:
        tcount = TutorialResource.objects.filter(Q(status=1) | Q(status=2), tutorial_detail__foss_id = f, language__name='English').order_by('tutorial_detail__order').count()
        tutorial = TutorialResource.objects.filter(Q(status=1) | Q(status=2), tutorial_detail__foss_id = f, language__name='English').order_by('tutorial_detail__order')[:1].first()
        random_tutorials.append((tcount, tutorial))
    try:
        tr_rec = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2)).order_by('?')[:1].first()
    except Exception, e:
        messages.error(request, str(e))
    context = {
        'tr_rec': tr_rec,
        'media_url': settings.MEDIA_URL,
        'random_tutorials' : random_tutorials,
    }
    
    testimonials = Testimonials.objects.all().order_by('?')[:2]
    context['testimonials'] = testimonials
    
    events = Event.objects.filter(event_date__gte=datetime.datetime.today()).order_by('event_date')[:2]
    context['events'] = events
    return render(request, 'spoken/templates/home.html', context)

def get_or_query(terms, search_fields):
    #terms = ['linux', ' operating system', ' computers', ' hardware platforms', ' oscad']
    #search_fields = ['keyword']
    query = None
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query | or_query
    print query
    return query

def keyword_search(request):
    context = {}
    keyword = ''
    collection = None
    conjunction_words = ['a', 'i']
    form = TutorialSearchForm()
    if request.method == 'GET' and 'q' in request.GET and request.GET['q'] != '':
        form = KeywordSearchForm(request.GET)
        if form.is_valid():
            keyword = request.GET['q']
            keywords = keyword.split(' ')
            search_fields = ['keyword']
            remove_words = set(keywords).intersection(set(conjunction_words))
            for key in remove_words:
                keywords.remove(key)
            query = get_or_query(keywords, search_fields)
            if query:
                collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__status = 1, common_content = TutorialCommonContent.objects.filter(query), language__name = 'English').order_by('tutorial_detail__foss__foss', 'tutorial_detail__level', 'tutorial_detail__order', 'language__name')
    
    if collection:
        page = request.GET.get('page')
        collection = get_page(collection, page)
    
    context = {}
    context['form'] = KeywordSearchForm()
    context['collection'] = collection
    context['keywords'] = keyword
    context.update(csrf(request))
    return render(request, 'spoken/templates/keyword_search.html', context)

@csrf_exempt
def tutorial_search(request):
    context = {}
    collection = None
    form = TutorialSearchForm()
    foss_get = ''
    if request.method == 'GET' and request.GET:
        form = TutorialSearchForm(request.GET)
        if form.is_valid():
            foss_get = request.GET.get('search_foss', '')
            language_get = request.GET.get('search_language', '')
            if foss_get and language_get:
                collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__foss = foss_get, language__name = language_get).order_by('tutorial_detail__level', 'tutorial_detail__order')
            elif foss_get:
                collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__foss = foss_get).order_by('tutorial_detail__level', 'tutorial_detail__order', 'language__name')
            elif language_get:
                collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), language__name = language_get).order_by('tutorial_detail__foss__foss', 'tutorial_detail__level', 'tutorial_detail__order')
            else:
                collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__id__in = FossCategory.objects.values('id'), language__id__in = Language.objects.values('id')).order_by('tutorial_detail__foss__foss', 'language__name', 'tutorial_detail__level', 'tutorial_detail__order')
    else:
        foss = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), language__name = 'English').values('tutorial_detail__foss__foss').annotate(Count('id')).values_list('tutorial_detail__foss__foss').distinct().order_by('?')[:1].first()
        collection = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__foss = foss[0], language__name = 'English')
        foss_get = foss[0]
    
    page = request.GET.get('page')
    collection = get_page(collection, page)
    context['form'] = form
    context['collection'] = collection
    context['SCRIPT_URL'] = settings.SCRIPT_URL
    context['current_foss'] = foss_get
    return render(request, 'spoken/templates/tutorial_search.html', context)

def watch_tutorial(request, foss, tutorial, lang):
    try:
        foss = unquote_plus(foss)
        tutorial = unquote_plus(tutorial)
        td_rec = TutorialDetail.objects.get(foss__foss = foss, tutorial = tutorial)
        tr_rec = TutorialResource.objects.select_related().get(tutorial_detail = td_rec, language = Language.objects.get(name = lang))
        tr_recs = TutorialResource.objects.select_related('tutorial_detail').filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss = tr_rec.tutorial_detail.foss, language = tr_rec.language).order_by('tutorial_detail__foss__foss', 'tutorial_detail__level', 'tutorial_detail__order', 'language__name')
    except Exception, e:
        messages.error(request, str(e))
        return HttpResponseRedirect('/')
    video_path = settings.MEDIA_ROOT + "videos/" + str(tr_rec.tutorial_detail.foss_id) + "/" + str(tr_rec.tutorial_detail_id) + "/" + tr_rec.video
    video_info = get_video_info(video_path)
    context = {
        'tr_rec': tr_rec,
        'tr_recs': tr_recs,
        'video_info': video_info,
        'media_url': settings.MEDIA_URL,
        'media_path': settings.MEDIA_ROOT,
        'tutorial_path': str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail_id) + '/',
        'script_base': settings.SCRIPT_URL
    }
    return render(request, 'spoken/templates/watch_tutorial.html', context)

@csrf_exempt
def get_language(request):
    output = ''
    if request.method == "POST":
        foss = request.POST.get('foss')
        lang = request.POST.get('lang')
        if not lang and foss:
            lang_list = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), tutorial_detail__foss__foss = foss).values('language__name').annotate(Count('id')).order_by('language__name').values_list('language__name', 'id__count').distinct()
            tmp = '<option value = ""> -- All Languages -- </option>'
            for lang_row in lang_list:
                tmp += '<option value="' + str(lang_row[0]) +'">' + str(lang_row[0]) + ' (' + str(lang_row[1]) + ')</option>'
            output = ['foss', tmp]
        elif lang and not foss:
            foss_list = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), language__name = lang).values('tutorial_detail__foss__foss').annotate(Count('id')).order_by('tutorial_detail__foss__foss').values_list('tutorial_detail__foss__foss', 'id__count').distinct()
            tmp = '<option value = ""> -- All Courses -- </option>'
            for foss_row in foss_list:
                tmp += '<option value="' + str(foss_row[0]) +'">' + str(foss_row[0]) + ' (' + str(foss_row[1]) + ')</option>'
            output = ['lang', tmp]
        elif foss and lang:
            pass
        else:
            lang_list = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2)).values('language__name').annotate(Count('id')).order_by('language__name').values_list('language__name', 'id__count').distinct()
            tmp1 = '<option value = ""> -- All Languages -- </option>'
            for lang_row in lang_list:
                tmp1 += '<option value="' + str(lang_row[0]) +'">' + str(lang_row[0]) + ' (' + str(lang_row[1]) + ')</option>'
            foss_list = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2), language__name = 'English').values('tutorial_detail__foss__foss').annotate(Count('id')).order_by('tutorial_detail__foss__foss').values_list('tutorial_detail__foss__foss', 'id__count').distinct()
            tmp2 = '<option value = ""> -- All Courses -- </option>'
            for foss_row in foss_list:
                tmp2 += '<option value="' + str(foss_row[0]) +'">' + str(foss_row[0]) + ' (' + str(foss_row[1]) + ')</option>'
            output = ['reset', tmp1, tmp2]
    return HttpResponse(json.dumps(output), mimetype='application/json')

def testimonials(request):
    testimonials = Testimonials.objects.all()
    context = { 'testimonials' : testimonials}
    context.update(csrf(request))
    return render(request, 'spoken/templates/testimonial/testimonials.html', context)

def testimonials_new(request):
    ''' new testimonials '''
    user = request.user
    context = {}
    form = TestimonialsForm()
    if (not user.is_authenticated()) or ((not user.has_perm('events.add_testimonials'))):
        raise PermissionDenied()
    
    if request.method == 'POST':
        form = TestimonialsForm(request.POST, request.FILES)
        if form.is_valid():
            form_data = form.save(commit=False)
            form_data.user_id = user.id
            form_data.save()
            rid = form_data.id
            file_type = ['application/pdf']
            if 'scan_copy' in request.FILES:
                if request.FILES['scan_copy'].content_type in file_type:
                    file_path = settings.MEDIA_ROOT + 'testimonial/'
                    try:
                        os.mkdir(file_path)
                    except Exception, e:
                        print e
                    file_path = settings.MEDIA_ROOT + 'testimonial/'+ str(rid) +'/'
                    try:
                        os.mkdir(file_path)
                    except Exception, e:
                        print e
                    full_path = file_path + str(rid) +".pdf"
                    fout = open(full_path, 'wb+')
                    f = request.FILES['scan_copy']
                    # Iterate through the chunks.
                    for chunk in f.chunks():
                        fout.write(chunk)
                    fout.close()
                        
                        
            messages.success(request, 'Testimonial has posted successfully!')
            return HttpResponseRedirect('/')
    context['form'] = form
    context.update(csrf(request))
    return render(request, 'spoken/templates/testimonial/form.html', context)
    
def admin_testimonials_edit(request, rid):
    user = request.user
    context = {}
    form = TestimonialsForm()
    instance = ''
    if (not user.is_authenticated()) or ((not user.has_perm('events.change_testimonials'))):
        raise PermissionDenied()
    try:
        instance = Testimonials.objects.get(pk= rid)
    except Exception, e:
        raise Http404('Page not found')
        print e
        
    if request.method == 'POST':
        form = TestimonialsForm(request.POST, request.FILES, instance = instance)
        if form.is_valid():
            form.save()
    
    form = TestimonialsForm(instance = instance)
    context['form'] = form
    context['instance'] = instance
    context.update(csrf(request))
    return render(request, 'spoken/templates/testimonial/form.html', context)

def admin_testimonials_delete(request, rid):
    user = request.user
    context = {}
    instance = ''
    if (not user.is_authenticated()) or ((not user.has_perm('events.delete_testimonials'))):
        raise PermissionDenied()
    try:
        instance = Testimonials.objects.get(pk= rid)
    except Exception, e:
        raise Http404('Page not found')
        print e
    if request.method == 'POST':
        instance = Testimonials.objects.get(pk= rid)
        instance.delete()
        messages.success(request, 'Testimonial deleted successfully')
        return HttpResponseRedirect('/admin/testimonials')
    context['instance'] = instance
    context.update(csrf(request))
    return render(request, 'spoken/templates/testimonial/form.html', context)

def admin_testimonials(request):
    ''' admin testimonials '''
    user = request.user
    context = {}
    if (not user.is_authenticated()) or (not user.has_perm('events.add_testimonials') and (not user.has_perm('events.change_testimonials'))):
        raise PermissionDenied()
    collection = Testimonials.objects.all()
    context['collection'] = collection
    context.update(csrf(request))
    return render(request, 'spoken/templates/testimonial/index.html', context)

def news(request, cslug):
    try:
        newstype = NewsType.objects.get(slug = cslug)
        collection = None
        latest = None
        if request.GET and 'latest' in request.GET and int(request.GET.get('latest')):
            collection = newstype.news_set.order_by('-created')
            latest = True
        else:
            collection = newstype.news_set.order_by('weight', '-created')
            
        if collection:
            page = request.GET.get('page')
            collection = get_page(collection, page)
        context = {
            'collection' : collection,
            'category' : cslug,
            'newstype' : newstype,
            'latest' : latest,
        }
        context.update(csrf(request))
        return render(request, 'spoken/templates/news/index.html', context)
    
    except Exception, e:
        print e
        raise Http404('You are not allowed to view this page')

def news_view(request, cslug, slug):
    try:
        newstype = NewsType.objects.get(slug = cslug)
        news = News.objects.get(slug = slug)
        image_or_doc = None
        if news.picture:
            supported_formats = ['.gif', '.png', '.bmp', '.jpg', '.jpeg']
            file_name, file_extension = os.path.splitext(settings.MEDIA_ROOT + str(news.picture))
            image_or_doc = 1
            if not (file_extension.lower() in supported_formats):
                image_or_doc = 2
        context = {
            'news' : news,
            'image_or_doc' : image_or_doc,
        }
        context.update(csrf(request))
        return render(request, 'spoken/templates/news/view-news.html', context)
        
    except Exception, e:
        print e
        raise Http404('You are not allowed to view this page')

def create_subtitle_files(request, overwrite = True):
    rows = TutorialResource.objects.filter(Q(status = 1) | Q(status = 2))
    for row in rows:
        code = 0
        if row.language.name == 'English':
            if row.timed_script and row.timed_script != 'pending':
                script_path = settings.SCRIPT_URL.strip('/') + '?title=' + quote(row.timed_script) + '&printable=yes'
            elif row.script and row.script != 'pending':
                script_path = settings.SCRIPT_URL.strip('/') + '?title=' + quote(row.script + '-timed') + '&printable=yes'
            else:
                continue
        else:
            if row.script and row.script != 'pending':
                script_path = settings.SCRIPT_URL.strip('/') + '?title=' + quote(row.script) + '&printable=yes'
            else:
                continue
        srt_file_path = settings.MEDIA_ROOT + 'videos/' + str(row.tutorial_detail.foss_id) + '/' + str(row.tutorial_detail_id) + '/'
        srt_file_name = row.tutorial_detail.tutorial.replace(' ', '-') + '-' + row.language.name + '.srt'
        # print srt_file_name
        if not overwrite and os.path.isfile(srt_file_path + srt_file_name):
            continue
        try:
            code = urlopen(script_path).code
        except Exception, e:
            code = e.code
        result = ''
        if(int(code) == 200):
            if generate_subtitle(script_path, srt_file_path + srt_file_name):
                print 'Success: ', row.tutorial_detail.foss.foss + ',', srt_file_name
            else:
                print 'Failed: ', row.tutorial_detail.foss.foss + ',', srt_file_name
    return HttpResponse('Success!')
